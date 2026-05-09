from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Text, ForeignKey, Float, DateTime, Integer
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "users"
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bot_token: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    groq_token: Mapped[str] = mapped_column(String, nullable=True)
    bot_name: Mapped[str] = mapped_column(String, nullable=True)
    bot_persona: Mapped[str] = mapped_column(String, nullable=True)
    user_info: Mapped[str] = mapped_column(String, nullable=True)
    
    # --- НАСТРОЙКИ ГОЛОСОВЫХ СООБЩЕНИЙ ---
    reply_mode_text: Mapped[str] = mapped_column(String, default="text")
    reply_mode_voice: Mapped[str] = mapped_column(String, default="both")
    voice_rate: Mapped[float] = mapped_column(Float, default=1.0)

class MemoryFact(Base):
    __tablename__ = "memory_facts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)

class MessageLog(Base):
    """Таблица для полного хранения всей переписки на сервере."""
    __tablename__ = "message_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String)  # 'user' или 'assistant'
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

class Contact(Base):
    """Таблица для хранения контактов и адресной книги пользователя."""
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    relationship: Mapped[str] = mapped_column(String, nullable=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    birthday: Mapped[str] = mapped_column(String, nullable=True)
    occupation: Mapped[str] = mapped_column(String, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

# --- НОВЫЕ МОДЕЛИ ДЛЯ ПЛАНИРОВЩИКА ---

class TaskCategory(Base):
    """Категории задач (Работа, Личное, Спорт и т.д.)."""
    __tablename__ = "task_categories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)

class Task(Base):
    """Задачи пользователя."""
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_categories.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="medium")  # low, medium, high
    status: Mapped[str] = mapped_column(String, default="pending")   # pending, completed, cancelled
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    
    category = relationship("TaskCategory")