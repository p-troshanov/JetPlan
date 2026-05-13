# Dockerfile
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

# Копируем всё содержимое проекта
COPY . .

# Запускаем через модуль python -m
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]