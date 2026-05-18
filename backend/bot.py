# backend/bot.py
import logging
import os
import json
import asyncio
from io import BytesIO
import aiohttp
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv
from sqlalchemy.future import select
from sqlalchemy import func

from backend.database import AsyncSessionLocal, TelegramUserCache, UserProfile, TaskCategory, Task

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# --- FSM States ---
class EditTaskState(StatesGroup):
    waiting_for_text = State()

class EditCategoryState(StatesGroup):
    waiting_for_text = State()

def get_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_task:{task_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_task:{task_id}")
        ]
    ])

def format_date_ru(date_obj: datetime) -> str:
    if not date_obj:
        return "Без даты"
    
    # Приводим к локальному часовому поясу
    tz = timezone(timedelta(hours=4))
    if date_obj.tzinfo:
        local_date = date_obj.astimezone(tz)
    else:
        local_date = date_obj.replace(tzinfo=timezone.utc).astimezone(tz)
        
    now = datetime.now(tz)
    date_day = local_date.date()
    now_day = now.date()
    diff_days = (date_day - now_day).days
    time_str = local_date.strftime("%H:%M")
    
    # Убираем отображение времени, если оно 00:00
    time_part = f" в {time_str}" if time_str != "00:00" else ""

    if diff_days == 0:
        return f"Сегодня{time_part}"
    elif diff_days == 1:
        return f"Завтра{time_part}"
    elif diff_days == -1:
        return f"Вчера{time_part}"
    elif 1 < diff_days <= 6:
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return f"{days[local_date.weekday()]}{time_part}"
    else:
        date_str = local_date.strftime("%d.%m.%Y")
        return f"{date_str}{time_part}"

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
        
    # При старте мы сохраняем пользователя в базу, чтобы потом по логину найти его chat_id
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TelegramUserCache).where(TelegramUserCache.telegram_id == message.from_user.id)
        )
        cache = result.scalar_one_or_none()
        
        username = message.from_user.username.lower() if message.from_user.username else None
        
        if cache:
            cache.username = username
            cache.first_name = message.from_user.first_name
            cache.last_name = message.from_user.last_name
        else:
            cache = TelegramUserCache(
                telegram_id=message.from_user.id,
                username=username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            session.add(cache)
        await session.commit()

    await message.answer(
        "Привет! Я бот-ассистент JetPlan.\n"
        "Если вы хотите привязать аккаунт, перейдите в настройки на сайте, "
        "введите ваш логин Telegram и нажмите 'Отправить код'."
    )

async def process_user_message(message: types.Message, text: str, processing_msg: types.Message = None, update_task_id: int = None, state: FSMContext = None, user_telegram_id: int = None):
    target_telegram_id = user_telegram_id or message.from_user.id
    
    async with AsyncSessionLocal() as session:
        # Находим пользователя
        result = await session.execute(
            select(UserProfile).where(UserProfile.telegram_id == target_telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            msg_text = "Сначала привяжите Telegram к вашему аккаунту JetPlan на сайте в разделе Настройки."
            if processing_msg:
                await processing_msg.edit_text(msg_text)
            else:
                await message.answer(msg_text)
            if state: await state.clear()
            return
            
        if user.ai_provider != 'groq' or not user.ai_api_key:
            msg_text = "Для умного добавления задач выберите провайдер Groq и укажите API ключ в настройках сайта."
            if processing_msg:
                await processing_msg.edit_text(msg_text)
            else:
                await message.answer(msg_text)
            if state: await state.clear()
            return

        if not processing_msg:
            processing_msg = await message.answer("🤖 <i>Анализирую текст...</i>", parse_mode="HTML")

        # Получаем категории пользователя
        cats_result = await session.execute(select(TaskCategory).where(TaskCategory.user_id == user.id))
        categories = cats_result.scalars().all()
        
        # Убеждаемся, что категория "Идея" существует (создаем, если нет)
        idea_cat = next((c for c in categories if c.name.lower() == "идея"), None)
        if not idea_cat:
            idea_cat = TaskCategory(user_id=user.id, name="Идея", category_type="custom")
            session.add(idea_cat)
            await session.commit()
            await session.refresh(idea_cat)
            categories.append(idea_cat)

        categories_str = "\n".join([f"- ID: {c.id}, Название: {c.name}" for c in categories])
        
        # Локальное время для точного вычисления относительных дат 
        tz = timezone(timedelta(hours=4))
        now = datetime.now(tz)
        current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # Загружаем существующую задачу, если мы в режиме редактирования
        existing_task = None
        if update_task_id:
            result_task = await session.execute(select(Task).where(Task.id == update_task_id, Task.user_id == user.id))
            existing_task = result_task.scalar_one_or_none()
            if not existing_task:
                await processing_msg.edit_text("Задача для обновления не найдена или была удалена.")
                if state: await state.clear()
                return
        
        # Базовый промпт
        system_prompt = f"""
Ты AI-ассистент, помогающий управлять задачами пользователя в системе JetPlan.
Информация о пользователе: {user.user_info or 'Не указана'}
Текущая дата и время сервера: {current_time_str}

Существующие категории пользователя:
{categories_str}

ОПРЕДЕЛЕНИЕ ДЕЙСТВИЯ (action_type):
- "category": Если пользователь явно просит создать или добавить новую категорию (например, "добавь категорию Покупки", "создай список Фильмы").
- "task": Если это явно задача (есть глагол действия, сроки, или это стандартная задача типа "купить молоко", "сделать отчет").
- "unknown": Если пользователь написал одно короткое слово или фразу без контекста (например, просто "Ремонт" или "Покупки") и непонятно, хочет он создать задачу с таким текстом или новую категорию.

Правила заполнения полей:
1. category_name: Если action_type="category", извлеки название категории (сделай его с заглавной буквы). В противном случае верни null.
2. category_id: Подбери ID категории, которая лучше всего подходит по смыслу для задачи. Для идей/мыслей обязательно используй ID ({idea_cat.id}). Если подходящей категории нет, верни null.
3. priority: Определи приоритет ("low", "medium", "high").
4. due_at: Если в тексте указан срок выполнения, дедлайн или дата, вычисли точную дату на основе текущей и верни в формате ISO 8601 ("YYYY-MM-DDTHH:MM:SS"). Если время дня явно не указано, используй 00:00:00. Если дата не подразумевается, верни null.
5. reminder_enabled: Если пользователь просит напомнить (например "напомни за 10 минут", "поставь напоминалку"), установи true. Если нет - false.
6. reminder_minutes: За сколько минут до `due_at` нужно прислать напоминание. По умолчанию 0. Если reminder_enabled=false, верни 0.

ВАЖНЫЕ ПРАВИЛА ДЛЯ ПОЛЯ DESCRIPTION (ТЕКСТ ЗАДАЧИ):
1. ОЧИСТКА: Строго удаляй из итогового текста любые упоминания времени, дат, приоритетов, названий категорий и вводные слова (например: "на завтра", "в категорию разработка", "создай задачу", "напомни").
2. ФОРМАТИРОВАНИЕ: Исправляй опечатки и всегда начинай с заглавной буквы.
"""

        # Дополняем промпт в зависимости от режима
        if existing_task:
            local_due_at_str = 'null'
            if existing_task.due_at:
                dt_utc = existing_task.due_at if existing_task.due_at.tzinfo else existing_task.due_at.replace(tzinfo=timezone.utc)
                local_due_at = dt_utc.astimezone(tz)
                local_due_at_str = f'"{local_due_at.strftime("%Y-%m-%dT%H:%M:%S")}"'
                
            system_prompt += f"""
РЕЖИМ РЕДАКТИРОВАНИЯ ЗАДАЧИ:
Пользователь хочет изменить существующую задачу.
Текущие данные задачи:
- Описание: "{existing_task.description}"
- ID категории: {existing_task.category_id if existing_task.category_id else 'null'}
- Приоритет: "{existing_task.priority}"
- Дата/Время: {local_due_at_str}
- Напоминание включено: {str(existing_task.reminder_enabled).lower()}
- Минуты напоминания: {existing_task.reminder_minutes}

Твоя задача: проанализировать запрос пользователя и применить изменения к текущим данным.
- Свойство action_type всегда верни "task".
- Для полей, которые пользователь НЕ просит менять, СКОПИРУЙ их текущие значения. 
- Для description: если пользователь просит дополнить/дописать текст, добавь это к текущему описанию. Если меняет только дату/приоритет - скопируй текущее описание.
"""

        system_prompt += """
Ответ должен быть СТРОГО в формате JSON:
{
  "action_type": "task", "category" или "unknown",
  "category_name": "Имя новой категории с заглавной буквы (только если action_type = category), иначе null",
  "description": "Только суть задачи (для action_type = task)",
  "category_id": число или null,
  "priority": "low" | "medium" | "high",
  "due_at": "YYYY-MM-DDTHH:MM:SS" или null,
  "reminder_enabled": true или false,
  "reminder_minutes": число
}
"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {user.ai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        logging.error(f"Groq API Error: {err_text}")
                        await processing_msg.edit_text("Произошла ошибка при обращении к Groq API. Проверьте логи сервера.")
                        if state: await state.clear()
                        return
                    res = await resp.json()
                    
            ai_content = res['choices'][0]['message']['content']
            task_data = json.loads(ai_content)
            
            action_type = task_data.get('action_type')
            
            # Фолбэк на случай старой модели, если она проигнорировала инструкцию
            if not action_type and 'create_task' in task_data:
                action_type = 'task' if task_data.get('create_task') else 'unknown'

            if action_type == 'category':
                cat_name = task_data.get('category_name') or text
                cat_name = cat_name.strip().capitalize()
                
                existing_cat = next((c for c in categories if c.name.lower() == cat_name.lower()), None)
                if existing_cat:
                    await processing_msg.edit_text(f"Категория <b>{existing_cat.name}</b> уже существует.", parse_mode="HTML")
                else:
                    new_cat = TaskCategory(user_id=user.id, name=cat_name, category_type="custom")
                    session.add(new_cat)
                    await session.commit()
                    await session.refresh(new_cat)
                    
                    kb = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_category:{new_cat.id}")
                    ]])
                    await processing_msg.edit_text(f"📁 Создана новая категория: <b>{new_cat.name}</b>", parse_mode="HTML", reply_markup=kb)
                
                if state: await state.clear()
                return

            elif action_type == 'unknown':
                await state.update_data(pending_text=text)
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="📝 Задачу", callback_data="clarify:task"),
                    InlineKeyboardButton(text="📁 Категорию", callback_data="clarify:category")
                ]])
                await processing_msg.edit_text(
                    f"Я не уверен, что именно вы хотите добавить.\n\nТекст: <i>{text}</i>\n\nВыберите действие:",
                    parse_mode="HTML",
                    reply_markup=kb
                )
                return

            elif action_type == 'task':
                # 1. Безопасный парсинг due_at
                raw_due_at = task_data.get('due_at')
                due_at_val = existing_task.due_at if existing_task else None
                
                if 'due_at' in task_data:
                    if raw_due_at:
                        try:
                            parsed_dt = datetime.fromisoformat(str(raw_due_at).replace("Z", ""))
                            due_at_val = parsed_dt.replace(tzinfo=tz).astimezone(timezone.utc)
                        except Exception:
                            pass
                    else:
                        due_at_val = None
                
                if not due_at_val and not existing_task:
                    # По умолчанию на сегодня 00:00 по локальному времени только для новых задач
                    local_now = datetime.now(tz)
                    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
                    due_at_val = local_midnight.astimezone(timezone.utc)
                
                # 2. Безопасный парсинг настроек напоминания
                raw_rem_enabled = task_data.get('reminder_enabled')
                rem_enabled = bool(raw_rem_enabled) if raw_rem_enabled is not None else (existing_task.reminder_enabled if existing_task else False)
                
                raw_rem_mins = task_data.get('reminder_minutes')
                if raw_rem_mins is not None:
                    try:
                        rem_mins = int(raw_rem_mins)
                    except (ValueError, TypeError):
                        rem_mins = 0
                else:
                    rem_mins = existing_task.reminder_minutes if existing_task else 0

                # 3. Безопасный парсинг описания, категории и приоритета
                raw_desc = task_data.get('description')
                desc_val = raw_desc if raw_desc else (existing_task.description if existing_task else text)
                
                cat_val = task_data.get('category_id') if 'category_id' in task_data else (existing_task.category_id if existing_task else None)
                
                raw_pri = task_data.get('priority')
                pri_val = raw_pri if raw_pri else (existing_task.priority if existing_task else 'medium')

                if existing_task:
                    existing_task.description = desc_val
                    existing_task.category_id = cat_val
                    existing_task.priority = pri_val
                    existing_task.due_at = due_at_val
                    existing_task.reminder_enabled = rem_enabled
                    existing_task.reminder_minutes = rem_mins
                    existing_task.reminder_sent = False
                    
                    new_task = existing_task
                    await session.commit()
                    await session.refresh(new_task)
                    prefix_action = "🔄 Задача обновлена"
                else:
                    idx_res = await session.execute(select(func.max(Task.order_index)).where(Task.user_id == user.id))
                    max_order = idx_res.scalar() or 0
                    
                    new_task = Task(
                        user_id=user.id,
                        description=desc_val,
                        category_id=cat_val,
                        priority=pri_val,
                        due_at=due_at_val,
                        status='pending',
                        order_index=max_order + 1,
                        reminder_enabled=rem_enabled,
                        reminder_minutes=rem_mins
                    )
                    session.add(new_task)
                    await session.commit()
                    await session.refresh(new_task)
                    prefix_action = "✅На"
                
                cat_name = "Без категории"
                if new_task.category_id:
                    cat_res = await session.execute(select(TaskCategory).where(TaskCategory.id == new_task.category_id))
                    cat = cat_res.scalar_one_or_none()
                    if cat: cat_name = cat.name
                
                due_str = format_date_ru(new_task.due_at)
                priority_emojis = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                emoji = priority_emojis.get(new_task.priority, '⚪')
                
                if new_task.reminder_enabled:
                    if new_task.reminder_minutes == 0:
                        rem_text = ", напоминание в то же время"
                    else:
                        rem_text = f", напомнить за {new_task.reminder_minutes} мин."
                else:
                    rem_text = ""
                    
                if existing_task:
                    reply_text = (
                        f"{prefix_action}:\n📅 {due_str}{rem_text} | 🗂 \"{cat_name}\" | ⚡ {emoji}\n\n"
                        f"{new_task.description}"
                    )
                else:
                    reply_text = (
                        f"{prefix_action} {due_str}{rem_text} в категорию \"{cat_name}\", приоритет: {emoji}\n\n"
                        f"{new_task.description}"
                    )
                
                keyboard = get_task_keyboard(new_task.id)
                await processing_msg.edit_text(reply_text, parse_mode="HTML", reply_markup=keyboard)
                
                if state:
                    await state.clear()
            else:
                msg = "Я не распознал команду. Напишите задачу или команду для создания категории."
                await processing_msg.edit_text(msg)
                if state:
                    await state.clear()

        except Exception as e:
            logging.error(f"Error processing AI task: {e}")
            await processing_msg.edit_text("Произошла ошибка при обработке вашего запроса.")
            if state:
                await state.clear()

@dp.callback_query(F.data.startswith("clarify:"))
async def process_clarification(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]
    data = await state.get_data()
    text = data.get("pending_text")
    
    if not text:
        await callback.answer("Данные устарели", show_alert=True)
        return
        
    await state.clear()
    
    if choice == 'category':
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.telegram_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            cat_name = text.strip().capitalize()
            
            cats_result = await session.execute(select(TaskCategory).where(TaskCategory.user_id == user.id))
            categories = cats_result.scalars().all()
            existing_cat = next((c for c in categories if c.name.lower() == cat_name.lower()), None)
            
            if existing_cat:
                await callback.message.edit_text(f"Категория <b>{existing_cat.name}</b> уже существует.", parse_mode="HTML")
            else:
                new_cat = TaskCategory(user_id=user.id, name=cat_name, category_type="custom")
                session.add(new_cat)
                await session.commit()
                await session.refresh(new_cat)
                
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_category:{new_cat.id}")
                ]])
                await callback.message.edit_text(f"📁 Создана новая категория: <b>{new_cat.name}</b>", parse_mode="HTML", reply_markup=kb)
    else:
        # Если пользователь выбрал задачу
        await callback.message.edit_text("🤖 <i>Создаю задачу...</i>", parse_mode="HTML")
        forced_text = f"Создай задачу: {text}"
        await process_user_message(
            message=callback.message, 
            text=forced_text, 
            processing_msg=callback.message, 
            state=state,
            user_telegram_id=callback.from_user.id
        )

# --- Обработчик редактирования текста категории ---
@dp.message(EditCategoryState.waiting_for_text)
async def handle_category_edit_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data.get("update_category_id")
    if not cat_id:
        await state.clear()
        return
        
    new_name = message.text.strip().capitalize()
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TaskCategory).where(TaskCategory.id == cat_id)
        )
        cat = result.scalar_one_or_none()
        if cat:
            cat.name = new_name
            await session.commit()
            
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_category:{cat.id}")
            ]])
            await message.answer(f"✅ Название категории обновлено: <b>{cat.name}</b>", parse_mode="HTML", reply_markup=kb)
        else:
            await message.answer("Категория не найдена.")
            
    await state.clear()

@dp.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    data = await state.get_data()
    update_task_id = data.get("update_task_id")
    await process_user_message(message, message.text, update_task_id=update_task_id, state=state)

@dp.message(F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user or user.ai_provider != 'groq' or not user.ai_api_key:
            await message.answer("Для голосового ввода привяжите Telegram и укажите API ключ Groq в настройках сайта.")
            if state: await state.clear()
            return
            
    processing_msg = await message.answer("🎙 <i>Распознаю голос...</i>", parse_mode="HTML")
    
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_bytes = BytesIO()
    await bot.download_file(file.file_path, file_bytes)
    file_bytes.seek(0)
            
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {user.ai_api_key}"}
    
    data = aiohttp.FormData()
    data.add_field('file', file_bytes.read(), filename='voice.ogg', content_type='audio/ogg')
    data.add_field('model', 'whisper-large-v3')
    
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    err_txt = await resp.text()
                    logging.error(f"Whisper Error: {err_txt}")
                    await processing_msg.edit_text("Ошибка при распознавании голоса Groq Whisper API.")
                    if state: await state.clear()
                    return
                res = await resp.json()
                text = res.get("text", "")
                
        if not text.strip():
            await processing_msg.edit_text("Не удалось распознать речь (пустой ответ).")
            if state: await state.clear()
            return
            
        await processing_msg.edit_text(f"🗣 <i>Распознано:</i> {text}\n🤖 <i>Анализирую...</i>", parse_mode="HTML")
        
        state_data = await state.get_data()
        update_task_id = state_data.get("update_task_id")
        
        await process_user_message(message, text, processing_msg=processing_msg, update_task_id=update_task_id, state=state)
        
    except Exception as e:
        logging.error(f"Voice processing error: {e}")
        await processing_msg.edit_text("Ошибка при обработке голосового сообщения.")
        if state: await state.clear()

# --- Callback Handlers для кнопок задач и категорий ---
@dp.callback_query(F.data.startswith("edit_category:"))
async def process_edit_category(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split(":")[1])
    await state.update_data(update_category_id=cat_id)
    await state.set_state(EditCategoryState.waiting_for_text)
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
    ])
    
    await callback.message.reply(
        "✏️ Введите новое название категории:",
        reply_markup=cancel_kb
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_task:"))
async def process_delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            await session.delete(task)
            await session.commit()
            await callback.message.edit_text(f"🗑️ Задача удалена:\n<s>{task.description}</s>", parse_mode="HTML")
        else:
            await callback.answer("Задача не найдена или уже удалена", show_alert=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_task:"))
async def process_edit_task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    await state.update_data(update_task_id=task_id)
    await state.set_state(EditTaskState.waiting_for_text)
    
    # Кнопка отмены редактирования
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить редактирование", callback_data="cancel_edit")]
    ])
    
    await callback.message.reply(
        "✏️ Что нужно изменить? (например: 'поставь на завтра на 15:00', 'сделай приоритет высоким' или 'допиши: купить хлеб'). "
        "Можно написать текстом или отправить голосовое сообщение.",
        reply_markup=cancel_kb
    )
    await callback.answer()

@dp.callback_query(F.data == "cancel_edit")
async def process_cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Редактирование отменено.")
    await callback.answer()

@dp.callback_query(F.data.startswith("complete:"))
async def process_complete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.status = 'completed'
            await session.commit()
            await callback.message.edit_text(f"✅ Задача выполнена:\n<s>{task.description}</s>", parse_mode="HTML")
        else:
            await callback.answer("Задача не найдена", show_alert=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("delay:"))
async def process_delay_task(callback: CallbackQuery):
    parts = callback.data.split(":")
    task_id = int(parts[1])
    minutes = int(parts[2])
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            if not task.due_at.tzinfo:
                task.due_at = task.due_at.replace(tzinfo=timezone.utc)
            
            task.due_at += timedelta(minutes=minutes)
            task.reminder_sent = False # Сбрасываем флаг, чтобы напоминание снова сработало
            await session.commit()
            
            new_time_str = format_date_ru(task.due_at)
            await callback.message.edit_text(
                f"⏳ Отложено на {minutes} мин (до {new_time_str})\n<i>{task.description}</i>",
                parse_mode="HTML"
            )
        else:
            await callback.answer("Задача не найдена", show_alert=True)
    await callback.answer()

# Экспортируемый воркер для проверки напоминаний
async def run_reminders():
    logging.info("Фоновый процесс проверки напоминаний запущен.")
    while True:
        try:
            async with AsyncSessionLocal() as session:
                now = datetime.now(timezone.utc)
                result = await session.execute(
                    select(Task, UserProfile)
                    .join(UserProfile, Task.user_id == UserProfile.id)
                    .where(
                        Task.status == 'pending',
                        Task.reminder_enabled == True,
                        Task.reminder_sent == False,
                        Task.due_at.isnot(None)
                    )
                )
                
                for task, user in result.all():
                    task_time = task.due_at
                    if not task_time.tzinfo:
                        task_time = task_time.replace(tzinfo=timezone.utc)
                        
                    remind_time = task_time - timedelta(minutes=task.reminder_minutes)
                    
                    if now >= remind_time:
                        if user.telegram_id:
                            try:
                                # Клавиатура с кнопками для выполнения и откладывания
                                kb = InlineKeyboardMarkup(inline_keyboard=[
                                    [
                                        InlineKeyboardButton(text="⏳ +15 мин", callback_data=f"delay:{task.id}:15"),
                                        InlineKeyboardButton(text="⏳ +30 мин", callback_data=f"delay:{task.id}:30"),
                                        InlineKeyboardButton(text="⏳ +1 час", callback_data=f"delay:{task.id}:60")
                                    ],
                                    [
                                        InlineKeyboardButton(text="✅ Выполнено", callback_data=f"complete:{task.id}")
                                    ]
                                ])
                                
                                await bot.send_message(
                                    user.telegram_id,
                                    f"🔔 <b>Напоминание</b>\n{task.description}",
                                    parse_mode="HTML",
                                    reply_markup=kb
                                )
                            except Exception as e:
                                logging.error(f"Failed to send reminder to {user.telegram_id}: {e}")
                        
                        task.reminder_sent = True
                        session.add(task)
                
                await session.commit()
        except Exception as e:
            logging.error(f"Cron reminder check error: {e}")
            
        await asyncio.sleep(60) # Проверяем раз в минуту

# Экспортируемая функция для запуска бота
async def start_bot():
    if not TELEGRAM_BOT_TOKEN:
        logging.error("Не задан TELEGRAM_BOT_TOKEN в файле .env. Бот не запущен.")
        return
        
    logging.info("Запуск Telegram бота в фоновом режиме...")
    await dp.start_polling(bot)
