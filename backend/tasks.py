# backend/tasks.py
import aiohttp
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, delete
from typing import List

from backend.database import get_db, Task, TaskCategory, UserProfile
from backend.auth import get_current_user
from backend.schemas import (
    TaskCategoryCreate, TaskCategoryUpdate, TaskCategoryResponse,
    TaskCreate, TaskUpdate, TaskResponse, TaskReorderRequest,
    AIQueryRequest, AIQueryResponse
)

router = APIRouter(tags=["tasks"])

# ==========================================
# CATEGORIES
# ==========================================

@router.post("/categories", response_model=TaskCategoryResponse)
async def create_category(
    data: TaskCategoryCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    new_cat = TaskCategory(**data.model_dump(), user_id=current_user.id)
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)
    return new_cat

@router.get("/categories", response_model=List[TaskCategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    result = await db.execute(
        select(TaskCategory).where(TaskCategory.user_id == current_user.id)
    )
    return result.scalars().all()

@router.put("/categories/{category_id}", response_model=TaskCategoryResponse)
async def update_category(
    category_id: int, 
    data: TaskCategoryUpdate, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    result = await db.execute(
        select(TaskCategory).where(TaskCategory.id == category_id, TaskCategory.user_id == current_user.id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cat, key, value)
        
    await db.commit()
    await db.refresh(cat)
    return cat

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    result = await db.execute(
        select(TaskCategory).where(TaskCategory.id == category_id, TaskCategory.user_id == current_user.id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
        
    await db.delete(cat)
    await db.commit()


# ==========================================
# TASKS
# ==========================================

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    data: TaskCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    # Находим максимальный order_index, чтобы новая задача упала в конец списка
    result = await db.execute(select(func.max(Task.order_index)).where(Task.user_id == current_user.id))
    max_order = result.scalar() or 0
    
    new_task = Task(**data.model_dump(), user_id=current_user.id, order_index=max_order + 1)
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    # Подгружаем категорию для красивого ответа фронту
    result_with_cat = await db.execute(
        select(Task).options(selectinload(Task.category)).where(Task.id == new_task.id)
    )
    return result_with_cat.scalar_one()

@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.category))
        .where(Task.user_id == current_user.id)
        .order_by(Task.order_index.asc())  # Сортируем по искусственному порядку
    )
    return result.scalars().all()

@router.put("/tasks/reorder", status_code=status.HTTP_200_OK)
async def reorder_tasks(
    data: TaskReorderRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Принимает массив ID задач в нужном порядке.
    Например: {"task_ids": [5, 2, 8, 1]}
    И обновляет у них order_index от 0 до N.
    """
    result = await db.execute(
        select(Task).where(Task.user_id == current_user.id, Task.id.in_(data.task_ids))
    )
    tasks_map = {task.id: task for task in result.scalars().all()}
    
    for index, task_id in enumerate(data.task_ids):
        if task_id in tasks_map:
            tasks_map[task_id].order_index = index
            
    await db.commit()
    return {"detail": "Tasks reordered successfully"}

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int, 
    data: TaskUpdate, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.category))
        .where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
        
    # Сбрасываем флаг отправки, если изменились дата или настройки напоминания
    if any(k in update_data for k in ("due_at", "reminder_enabled", "reminder_minutes")):
        task.reminder_sent = False
        
    await db.commit()
    await db.refresh(task)
    
    updated_result = await db.execute(
        select(Task).options(selectinload(Task.category)).where(Task.id == task_id)
    )
    return updated_result.scalar_one()

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    await db.delete(task)
    await db.commit()

# ==========================================
# AI INTEGRATION
# ==========================================

@router.post("/tasks/ai", response_model=AIQueryResponse)
async def process_ai_action(
    data: AIQueryRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    if current_user.ai_provider != 'groq' or not current_user.ai_api_key:
        raise HTTPException(status_code=400, detail="Для использования ИИ необходимо указать API ключ Groq в настройках.")

    cats = await db.execute(select(TaskCategory).where(TaskCategory.user_id == current_user.id))
    categories = cats.scalars().all()
    cats_info = ", ".join([f"'{c.name}' (ID: {c.id})" for c in categories])

    system_prompt = f"""
Ты AI-помощник для управления задачами.
Текущее время пользователя: {data.local_time}
Категории пользователя: {cats_info}

Твоя цель - проанализировать запрос и вернуть JSON-ответ.
Возможные намерения (intent): "filter", "delete_category", "reschedule_overdue".

1. Для фильтрации/поиска (например "просроченные", "важные", "из категории X"):
{{
  "intent": "filter",
  "filters": {{
    "status": "pending" | "completed" | "all",
    "priority": "high" | "medium" | "low" | "",
    "is_overdue": true | false,
    "category_id": число | ""
  }},
  "message": "Показываю ..."
}}
(Если просят показать активные или невыполненные - используй status: "pending". Если просроченные - is_overdue: true и status: "pending").

2. Для удаления задач категории (например "удали все задачи категории X"):
{{
  "intent": "delete_category",
  "category_id": число,
  "message": "Задачи категории удалены"
}}

3. Для переноса просроченных (например "перенеси просроченные на сегодня"):
{{
  "intent": "reschedule_overdue",
  "message": "Просроченные задачи перенесены на сегодня"
}}

Ответ должен быть СТРОГО в формате JSON. Не пиши ничего кроме JSON.
"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {current_user.ai_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": data.query}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                err_text = await resp.text()
                raise HTTPException(status_code=500, detail=f"Ошибка API Groq: {err_text}")
            res_json = await resp.json()

    ai_content = res_json['choices'][0]['message']['content']
    try:
        parsed = json.loads(ai_content)
    except Exception:
        raise HTTPException(status_code=500, detail="Неверный формат ответа от ИИ")

    intent = parsed.get("intent")
    message = parsed.get("message", "Выполнено")

    if intent == "delete_category":
        cat_id = parsed.get("category_id")
        if cat_id:
            await db.execute(delete(Task).where(Task.category_id == cat_id, Task.user_id == current_user.id))
            await db.commit()
            return AIQueryResponse(action="reload", message=message)

    elif intent == "reschedule_overdue":
        now_utc = datetime.now(timezone.utc)
        today_end = now_utc.replace(hour=23, minute=59, second=59)
        result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id, 
                Task.status == 'pending', 
                Task.due_at < now_utc
            )
        )
        overdue_tasks = result.scalars().all()
        for t in overdue_tasks:
            t.due_at = today_end
        await db.commit()
        return AIQueryResponse(action="reload", message=message)

    filters = parsed.get("filters", {})
    return AIQueryResponse(action="filter", message=message, filters=filters)

