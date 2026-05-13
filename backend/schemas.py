# backend/schemas.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- User Profile Schemas ---
class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_api_key: Optional[str] = None
    task_hotkey: Optional[str] = None

class UserProfileResponse(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_api_key: Optional[str] = None
    task_hotkey: Optional[str] = None
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
    code: str

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

