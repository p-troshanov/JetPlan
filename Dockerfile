FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё содержимое корня в контейнер
COPY . .

# Поскольку мы в корне, запускаем main.py из папки backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]