# backend/access_control.py
# Проверяет принадлежность связанных сущностей текущему пользователю перед изменением данных.

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import TaskCategory


async def require_owned_task_category(
    db: AsyncSession,
    category_id: int | None,
    user_id: int,
) -> TaskCategory | None:
    """Возвращает категорию пользователя или отклоняет чужой/несуществующий идентификатор."""
    if category_id is None:
        return None

    result = await db.execute(
        select(TaskCategory).where(
            TaskCategory.id == category_id,
            TaskCategory.user_id == user_id,
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category does not belong to the current user",
        )
    return category
