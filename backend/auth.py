# backend/auth.py
import hashlib
import hmac
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, func
from pydantic import BaseModel
import bcrypt

from backend.config import settings
from backend.database import get_db, UserProfile, TaskCategory, TelegramLinkCode, TelegramUserCache, TelegramAuthRequest
from backend.schemas import (
    UserProfileUpdate, UserProfileResponse, ChangePasswordRequest,
    TelegramBotCodeRequest, TelegramBotCodeResponse, TelegramLinkCodeRequest,
    TelegramRequestCodeRequest, TelegramVerifyCodeRequest, InteractiveAuthRequest
)
from backend.bot import bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Токен живет 7 дней
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
router = APIRouter()

# --- Схемы Pydantic ---
class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

class UserRegisterData(BaseModel):
    username: str
    password: str

# --- Утилиты ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_telegram_authorization(data: TelegramAuthData) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        return False
        
    data_dict = data.model_dump(exclude_none=True)
    received_hash = data_dict.pop('hash', None)
    if not received_hash:
        return False

    data_check_arr = []
    for key, value in sorted(data_dict.items()):
        data_check_arr.append(f"{key}={value}")
    data_check_string = "\n".join(data_check_arr)

    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    hash_check = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    return hash_check == received_hash

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Эндпоинты авторизации ---

@router.post("/register")
async def register_user(user_data: UserRegisterData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.username == user_data.username))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    hashed_password = get_password_hash(user_data.password)
    
    new_user = UserProfile(
        username=user_data.username,
        hashed_password=hashed_password,
        user_info=f"User: {user_data.username}"
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    default_cat = TaskCategory(user_id=new_user.id, name="Личное", category_type="default")
    db.add(default_cat)
    await db.commit()
    
    return {"message": "User registered successfully"}

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/telegram")
async def telegram_auth(data: TelegramAuthData, db: AsyncSession = Depends(get_db)):
    if not verify_telegram_authorization(data):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram authentication")

    if datetime.now(timezone.utc).timestamp() - data.auth_date > 86400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth data is outdated")

    result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == data.id))
    user = result.scalar_one_or_none()

    if not user:
        user = UserProfile(
            telegram_id=data.id,
            first_name=data.first_name,
            last_name=data.last_name,
            user_info=f"{data.first_name} {data.last_name or ''} (@{data.username or ''})".strip()
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        default_cat = TaskCategory(user_id=user.id, name="Личное", category_type="default")
        db.add(default_cat)
        await db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# --- Интерактивный Telegram Вход через бота ---
@router.post("/telegram-interactive/request")
async def interactive_auth_request(data: InteractiveAuthRequest, db: AsyncSession = Depends(get_db)):
    username = data.username.replace("@", "").lower().strip()
    if not username:
        raise HTTPException(status_code=400, detail="Укажите корректный логин")
        
    result = await db.execute(select(TelegramUserCache).where(func.lower(TelegramUserCache.username) == username))
    cache = result.scalar_one_or_none()
    
    if not cache:
        raise HTTPException(status_code=400, detail="Бот вас не знает. Напишите /start в бота @jetplan_bot, а затем повторите попытку.")

    req_id = str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    auth_req = TelegramAuthRequest(
        request_id=req_id, 
        telegram_id=cache.telegram_id, 
        expires_at=expires
    )
    db.add(auth_req)
    await db.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Разрешить вход", callback_data=f"auth_approve:{req_id}")],
        [InlineKeyboardButton(text="❌ Запретить", callback_data=f"auth_deny:{req_id}")]
    ])
    
    try:
        await bot.send_message(
            chat_id=cache.telegram_id,
            text="🚨 <b>Попытка входа/регистрации</b>\nКто-то пытается зайти в ваш аккаунт JetPlan на сайте. Разрешить?",
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка отправки сообщения ботом. Убедитесь, что вы не заблокировали бота.")
        
    return {"request_id": req_id}

@router.get("/telegram-interactive/status")
async def interactive_auth_status(request_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TelegramAuthRequest).where(TelegramAuthRequest.request_id == request_id))
    auth_req = result.scalar_one_or_none()
    
    if not auth_req:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    
    if auth_req.expires_at < datetime.now(timezone.utc):
        return {"status": "expired"}

    if auth_req.status == "approved":
        res_user = await db.execute(select(UserProfile).where(UserProfile.telegram_id == auth_req.telegram_id))
        user = res_user.scalar_one_or_none()
        
        if not user:
            c_res = await db.execute(select(TelegramUserCache).where(TelegramUserCache.telegram_id == auth_req.telegram_id))
            cache = c_res.scalar_one_or_none()
            
            user = UserProfile(
                telegram_id=auth_req.telegram_id,
                username=cache.username if cache else None,
                first_name=cache.first_name if cache else None,
                last_name=cache.last_name if cache else None,
                user_info=f"Вход через Telegram (@{cache.username if cache else 'unknown'})"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            default_cat = TaskCategory(user_id=user.id, name="Личное", category_type="default")
            db.add(default_cat)
            await db.commit()
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        await db.delete(auth_req)
        await db.commit()
        
        return {"status": "approved", "access_token": access_token}

    return {"status": auth_req.status}


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
        
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# --- Эндпоинты профиля пользователя ---

@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: UserProfile = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserProfileResponse)
async def update_me(
    data: UserProfileUpdate, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.put("/password")
async def change_password(
    data: ChangePasswordRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="У пользователя не установлен пароль (вход только через Telegram)")
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный старый пароль")
    
    current_user.hashed_password = get_password_hash(data.new_password)
    db.add(current_user)
    await db.commit()
    return {"message": "Пароль успешно обновлен"}

# --- Привязка Telegram (С вводом логина на сайте) ---

@router.post("/telegram/request-code")
async def request_telegram_code(
    data: TelegramRequestCodeRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    """ Эндпоинт для запроса кода, который бот пришлет в ЛС """
    username = data.username.replace("@", "").lower().strip()
    if not username:
        raise HTTPException(status_code=400, detail="Укажите корректный логин")
        
    # Ищем пользователя в кэше бота
    result = await db.execute(select(TelegramUserCache).where(func.lower(TelegramUserCache.username) == username))
    cache = result.scalar_one_or_none()
    
    if not cache:
        raise HTTPException(status_code=400, detail="Бот вас не знает. Пожалуйста, напишите /start в бота @jetplan_bot, а затем повторите попытку.")

    await db.execute(delete(TelegramLinkCode).where(TelegramLinkCode.telegram_id == cache.telegram_id))
    
    while True:
        code = ''.join(random.choices(string.digits, k=4))
        res = await db.execute(select(TelegramLinkCode).where(TelegramLinkCode.code == code))
        if not res.scalar_one_or_none():
            break

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    new_code = TelegramLinkCode(
        code=code,
        telegram_id=cache.telegram_id,
        first_name=cache.first_name,
        last_name=cache.last_name,
        username=cache.username,
        expires_at=expires_at
    )
    db.add(new_code)
    await db.commit()
    
    # Отправляем сообщение напрямую из FastAPI
    try:
        await bot.send_message(
            chat_id=cache.telegram_id,
            text=f"Ваш код для привязки аккаунта JetPlan: <b>{code}</b>\nНикому его не сообщайте.",
            parse_mode="HTML"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки сообщения ботом. Убедитесь, что вы не заблокировали бота.")
        
    return {"message": "Код отправлен вам в Telegram"}

@router.post("/telegram/verify-code")
async def verify_telegram_code(
    data: TelegramVerifyCodeRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserProfile = Depends(get_current_user)
):
    """ Эндпоинт для проверки отправленного кода """
    result = await db.execute(select(TelegramLinkCode).where(TelegramLinkCode.code == data.code))
    link_record = result.scalar_one_or_none()
    
    if not link_record:
        raise HTTPException(status_code=400, detail="Неверный или несуществующий код")
        
    if link_record.expires_at < datetime.now(timezone.utc):
        await db.delete(link_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="Срок действия кода истек")
        
    current_user.telegram_id = link_record.telegram_id
    if not current_user.first_name and link_record.first_name:
        current_user.first_name = link_record.first_name
    if not current_user.last_name and link_record.last_name:
        current_user.last_name = link_record.last_name
        
    db.add(current_user)
    await db.delete(link_record) # Удаляем использованный код
    await db.commit()

    # Отправка уведомления об успешной привязке
    try:
        await bot.send_message(
            chat_id=current_user.telegram_id,
            text="✅ <b>Telegram успешно привязан!</b>\nТеперь вы можете управлять своими задачами и получать уведомления прямо здесь.",
            parse_mode="HTML"
        )
    except Exception as e:
        # Логируем ошибку, но не прерываем ответ фронтенду, так как в БД всё уже сохранилось
        print(f"Ошибка при отправке уведомления об успехе: {e}")
    
    return {"message": "Telegram linked successfully"}
