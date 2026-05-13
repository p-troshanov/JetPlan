# frontend/Dockerfile
FROM node:20-alpine

WORKDIR /app

# Копируем конфигурационные файлы npm/yarn
COPY package*.json ./
RUN npm install

# Копируем исходный код фронтенда
COPY . .

# Запускаем Vite с прослушиванием всех сетевых интерфейсов
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]