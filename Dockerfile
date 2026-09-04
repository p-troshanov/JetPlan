# Dockerfile
# Собирает минимальный runtime-образ FastAPI backend без локальных секретов и frontend-артефактов.
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости для компиляции некоторых пакетов (если нужно)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости в системную директорию
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем только runtime-исходники backend; секреты передаются контейнеру через environment.
COPY backend ./backend

# Запускаем через модуль python -m
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
