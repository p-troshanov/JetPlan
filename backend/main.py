# backend/main.py
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text

from backend.config import settings
from backend.auth import router as auth_router
from backend.tasks import router as tasks_router, run_daily_cron
from backend.database import engine, Base

# Импортируем функцию запуска бота и крон напоминаний
from backend.bot import start_bot, run_reminders

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Установка расширения pgvector только если оно включено в конфиге
    if settings.USE_PGVECTOR:
        async with engine.begin() as conn:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                print("pgvector extension ensured.")
            except Exception as e:
                print(f"Warning: Failed to create vector extension. {e}")
        
    # 2. Создание таблиц БД
    print("Создание таблиц базы данных...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                columns_to_add = [
                    "first_name VARCHAR",
                    "last_name VARCHAR",
                    "ai_provider VARCHAR DEFAULT 'gemini'",
                    "ai_api_key VARCHAR",
                    "task_hotkey VARCHAR DEFAULT 'ctrl+q'",
                    "auto_postpone_overdue BOOLEAN DEFAULT FALSE",
                    "bot_token VARCHAR",
                    "groq_token VARCHAR",
                    "bot_name VARCHAR",
                    "bot_persona VARCHAR",
                    "user_info VARCHAR",
                    "reply_mode_text VARCHAR DEFAULT 'text'",
                    "reply_mode_voice VARCHAR DEFAULT 'both'",
                    "voice_rate FLOAT DEFAULT 1.0"
                ]
                for col in columns_to_add:
                    await conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col};"))
                print("Миграция колонок для users успешно проверена.")
                
                # Миграция для новых полей задач
                task_cols = [
                    "recurrence_rule VARCHAR",
                    "reminder_enabled BOOLEAN DEFAULT FALSE",
                    "reminder_minutes INTEGER DEFAULT 0",
                    "reminder_sent BOOLEAN DEFAULT FALSE"
                ]
                for col in task_cols:
                    await conn.execute(text(f"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS {col};"))
                print("Миграция колонок для tasks успешно проверена.")
            except Exception as e:
                print(f"Warning: Failed to alter tables: {e}")

        print("Таблицы успешно проверены/созданы.")
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
        
    # 3. ЗАПУСК БОТА И КРОНОВ В ФОНЕ
    bot_task = asyncio.create_task(start_bot())
    reminder_task = asyncio.create_task(run_reminders())
    cron_task = asyncio.create_task(run_daily_cron())
        
    yield
    
    # 4. Грациозное завершение фоновых задач при остановке сервера
    bot_task.cancel()
    reminder_task.cancel()
    cron_task.cancel()

app = FastAPI(title="Jetplan API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://jetplan.site",
        "https://jetplan.site",
        "http://jetplan.site:28202",
        "https://jetplan.site:28202"
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(tasks_router, prefix="/api", tags=["tasks"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "Jetplan API is running"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}