# backend/config.py
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
    SECRET_KEY = os.getenv("SECRET_KEY", "insecure_default_key_replace_in_env")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Флаг для включения/отключения векторного поиска (pgvector)
    # По умолчанию False, чтобы не ломать запуск на локальном Windows без Docker
    USE_PGVECTOR = os.getenv("USE_PGVECTOR", "False").lower() in ("true", "1", "t")

settings = Settings()
