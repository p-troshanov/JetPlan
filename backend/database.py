# backend/database.py
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Text, ForeignKey, Float, DateTime, Integer, ARRAY, Boolean
from sqlalchemy.sql import func

from backend.config import settings

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

# Универсальный выбор типа для векторов
if settings.USE_PGVECTOR:
    from pgvector.sqlalchemy import Vector
    EmbeddingType = Vector(384)
else:
    # Фолбек на стандартный массив PostgreSQL, если pgvector не установлен
    EmbeddingType = ARRAY(Float)

class UserProfile(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=True)
    
    # Новые поля для настроек пользователя
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    ai_provider: Mapped[str] = mapped_column(String, default="gemini")
    ai_api_key: Mapped[str] = mapped_column(String, nullable=True)
    task_hotkey: Mapped[str] = mapped_column(String, default="ctrl+q")
    auto_postpone_overdue: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    
    bot_token: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    groq_token: Mapped[str] = mapped_column(String, nullable=True)
    bot_name: Mapped[str] = mapped_column(String, nullable=True)
    bot_persona: Mapped[str] = mapped_column(String, nullable=True)
    user_info: Mapped[str] = mapped_column(String, nullable=True)
    
    reply_mode_text: Mapped[str] = mapped_column(String, default="text")
    reply_mode_voice: Mapped[str] = mapped_column(String, default="both")
    voice_rate: Mapped[float] = mapped_column(Float, default=1.0)

class TelegramLinkCode(Base):
    __tablename__ = "telegram_link_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class TelegramAuthRequest(Base):
    __tablename__ = "telegram_auth_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class TelegramUserCache(Base):
    __tablename__ = "telegram_user_cache"
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, index=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)

class MemoryFact(Base):
    __tablename__ = "memory_facts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingType, nullable=False)

class MessageLog(Base):
    __tablename__ = "message_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    relationship: Mapped[str] = mapped_column(String, nullable=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    birthday: Mapped[str] = mapped_column(String, nullable=True)
    occupation: Mapped[str] = mapped_column(String, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

class TaskCategory(Base):
    __tablename__ = "task_categories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    subcategory: Mapped[str] = mapped_column(String, nullable=True)
    category_type: Mapped[str] = mapped_column(String, default="custom")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_categories.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(String, default="medium")
    status: Mapped[str] = mapped_column(String, default="pending")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Поля для регулярности и напоминаний
    recurrence_rule: Mapped[str] = mapped_column(String, nullable=True)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reminder_minutes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    
    category = relationship("TaskCategory")

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
