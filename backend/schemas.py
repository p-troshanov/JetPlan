# backend/schemas.py
# Определяет проверяемые request/response-контракты пользователей, Telegram, категорий и задач.
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal, Optional, List
from datetime import datetime

# --- User Profile Schemas ---
class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    ai_provider: Optional[Literal["groq", "openrouter"]] = None
    ai_api_key: Optional[str] = Field(default=None, max_length=512)
    ai_model: Optional[str] = Field(default=None, max_length=160)
    stt_provider: Optional[Literal["groq"]] = None
    stt_api_key: Optional[str] = Field(default=None, max_length=512)
    task_hotkey: Optional[str] = None
    auto_postpone_overdue: Optional[bool] = None

    @field_validator("ai_api_key", "ai_model", "stt_api_key")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value and value.strip() else None

class UserProfileResponse(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_api_key_configured: bool = False
    stt_provider: Optional[str] = None
    stt_api_key_configured: bool = False
    task_hotkey: Optional[str] = None
    auto_postpone_overdue: bool = False
    telegram_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

# --- Telegram Link Schemas ---
class TelegramBotCodeRequest(BaseModel):
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

class TelegramBotCodeResponse(BaseModel):
    code: str
    expires_in_seconds: int

class TelegramLinkCodeRequest(BaseModel):
    code: str

class TelegramRequestCodeRequest(BaseModel):
    username: str

class TelegramVerifyCodeRequest(BaseModel):
    code: str = Field(min_length=50, max_length=128)
    
class InteractiveAuthRequest(BaseModel):
    username: str

# --- Task Category Schemas ---
class TaskCategoryBase(BaseModel):
    name: str
    subcategory: Optional[str] = None
    category_type: Optional[str] = "custom"

class TaskCategoryCreate(TaskCategoryBase):
    pass

class TaskCategoryUpdate(BaseModel):
    name: Optional[str] = None
    subcategory: Optional[str] = None
    category_type: Optional[str] = None

class TaskCategoryResponse(TaskCategoryBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

# --- Task Schemas ---
class TaskBase(BaseModel):
    description: str
    category_id: Optional[int] = None
    due_at: Optional[datetime] = None
    priority: str = "medium"
    status: str = "pending"
    recurrence_rule: Optional[str] = None
    reminder_enabled: bool = False
    reminder_minutes: int = 0

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    description: Optional[str] = None
    category_id: Optional[int] = None
    due_at: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    order_index: Optional[int] = None
    recurrence_rule: Optional[str] = None
    reminder_enabled: Optional[bool] = None
    reminder_minutes: Optional[int] = None
    reminder_sent: Optional[bool] = None

class TaskResponse(TaskBase):
    id: int
    user_id: int
    order_index: int
    created_at: datetime
    category: Optional[TaskCategoryResponse] = None
    reminder_sent: bool = False
    
    model_config = ConfigDict(from_attributes=True)

class TaskReorderRequest(BaseModel):
    task_ids: List[int]

# --- AI Integration Schemas ---
class AIQueryRequest(BaseModel):
    query: str
    local_time: str

class AIQueryResponse(BaseModel):
    action: str
    message: Optional[str] = None
    filters: Optional[dict] = None
