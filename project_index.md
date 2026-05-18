# ИНСТРУКЦИЯ ДЛЯ ИИ (SYSTEM PROMPT)
Перед тобой актуальная структура проекта и индекс файлов.

**Твоя задача в этом чате:**
1. Изучи структуру, назначение файлов и их зависимости (импорты) ниже.
2. Когда я ставлю задачу по разработке, первым делом проанализируй, какие файлы затронет изменение, опираясь на их связи.
3. Ответь мне списком: какие конкретно файлы (пути) мне нужно прикрепить в чат.
**ВАЖНО:** Каждый запрашиваемый файл выводи строго в таком формате: `[LOAD: путь/к/файлу.ext]` (именно в квадратных скобках, без лишних символов).
4. **ВАЖНОЕ ПРАВИЛО:** При выдаче готового кода строго соблюдай инструкции: всегда возвращай полный код измененного файла от начала до конца. Никогда не удаляй и не сокращай код ради краткости (никаких комментариев вида "остальной код без изменений").

---

# Структура проекта

```text
📄 .gitignore
📄 Dockerfile
📄 requirements.txt
📄 _start_all.bat
📂 backend/
  📄 auth.py
  📄 bot.py
  📄 config.py
  📄 database.py
  📄 main.py
  📄 schemas.py
  📄 tasks.py
📂 frontend/
  📄 .gitignore
  📄 Dockerfile
  📄 env.d.ts
  📄 index.html
  📄 package-lock.json
  📄 package.json
  📄 README.md
  📄 tsconfig.app.json
  📄 tsconfig.json
  📄 tsconfig.node.json
  📄 vite.config.ts
  📂 public/
  📂 src/
    📄 App.vue
    📄 main.ts
    📂 assets/
      📄 base.css
      📄 logo.svg
      📄 main.css
      📄 tasks.css
    📂 components/
      📄 HelloWorld.vue
      📄 TelegramLogin.vue
      📄 TheWelcome.vue
      📄 WelcomeItem.vue
      📂 icons/
        📄 IconCommunity.vue
        📄 IconDocumentation.vue
        📄 IconEcosystem.vue
        📄 IconSupport.vue
        📄 IconTooling.vue
      📂 tasks/
        📄 CategoryModal.vue
        📄 TaskModal.vue
        📄 TasksDashboard.vue
    📂 router/
      📄 index.ts
    📂 stores/
      📄 counter.ts
      📄 tasks.ts
      📄 user.ts
    📂 types/
      📄 index.ts
    📂 views/
      📄 AboutView.vue
      📄 HomeView.vue
      📄 SettingsView.vue
📂 nginx/
  📄 nginx.conf
📂 src/
  📂 assets/
    📄 main.css
```

# Индекс файлов (Пути, Строки, Зависимости, Суть)

- **.gitignore** - *(25 строк)* `node_modules/ | dist/`
- **Dockerfile** - *(22 строк)* `FROM python:3.11-slim | WORKDIR /app`
- **requirements.txt** - *(13 строк)* `fastapi | uvicorn`
- **_start_all.bat** - *(33 строк)* `@echo off | chcp 65001 >nul`
- **backend/auth.py** - *(321 строк)* 🔗 Зависимости: [hashlib, hmac, random, string, datetime, typing] `class TelegramAuthData(BaseModel): | class UserRegisterData(BaseModel): | def verify_password(plain_password: str, hashed_password:...`
- **backend/bot.py** - *(729 строк)* 🔗 Зависимости: [logging, os, json, asyncio, io, aiohttp] `class EditTaskState(StatesGroup): | class EditCategoryState(StatesGroup): | def get_task_keyboard(task_id: int) -> InlineKeyboardMarkup:`
- **backend/config.py** - *(17 строк)* 🔗 Зависимости: [os, dotenv] `class Settings:`
- **backend/database.py** - *(124 строк)* 🔗 Зависимости: [datetime, asyncio, orm, sqlalchemy, sql, config] `class UserProfile(Base): | class TelegramLinkCode(Base):`
- **backend/main.py** - *(108 строк)* 🔗 Зависимости: [asyncio, fastapi, cors, contextlib, sqlalchemy, config] `async def lifespan(app: FastAPI):`
- **backend/schemas.py** - *(119 строк)* 🔗 Зависимости: [pydantic, typing, datetime] `class UserProfileUpdate(BaseModel): | class UserProfileResponse(BaseModel): | class ChangePasswordRequest(BaseModel):`
- **backend/tasks.py** - *(369 строк)* 🔗 Зависимости: [aiohttp, json, asyncio, datetime, rrule, fastapi] `async def create_category( | async def get_categories(`
- **frontend/.gitignore** - *(39 строк)* `logs | *.log`
- **frontend/Dockerfile** - *(14 строк)* `FROM node:20-alpine | WORKDIR /app`
- **frontend/env.d.ts** - *(2 строк)* `[Конфиг / Без сигнатур]`
- **frontend/index.html** - *(14 строк)* `<!DOCTYPE html> | <html lang="">`
- **frontend/package-lock.json** - *(3092 строк)* `"name": "jetplan-web", | "version": "0.0.0",`
- **frontend/package.json** - *(33 строк)* `"name": "jetplan-web", | "version": "0.0.0",`
- **frontend/README.md** - *(43 строк)* `This template should help get you started developing with Vu | [VS Code](https://code.visualstudio.com/) + [Vue (Official)]`
- **frontend/tsconfig.app.json** - *(18 строк)* `"extends": "@vue/tsconfig/tsconfig.dom.json", | "include": ["env.d.ts", "src/**/*", "src/**/*.vue"],`
- **frontend/tsconfig.json** - *(11 строк)* `"files": [], | "references": [`
- **frontend/tsconfig.node.json** - *(27 строк)* `{ | "extends": "@tsconfig/node24/tsconfig.json",`
- **frontend/vite.config.ts** - *(25 строк)* 🔗 Зависимости: [node:url, vite, plugin-vue] `export default defineConfig(`
- **frontend/src/App.vue** - *(24 строк)* `</script> | <template>`
- **frontend/src/main.ts** - *(15 строк)* 🔗 Зависимости: [App, router] `const app = createApp(App)`
- **frontend/src/assets/base.css** - *(87 строк)* `:root { | --vt-c-white: #ffffff;`
- **frontend/src/assets/logo.svg** - *(1 строк)* `[Конфиг / Без сигнатур]`
- **frontend/src/assets/main.css** - *(30 строк)* `@import './base.css'; | max-width: 1280px;`
- **frontend/src/assets/tasks.css** - *(434 строк)* `.tasks-dashboard { | display: flex;`
- **frontend/src/components/HelloWorld.vue** - *(42 строк)* `defineProps<{ | msg: string`
- **frontend/src/components/TelegramLogin.vue** - *(70 строк)* `interface Window`
- **frontend/src/components/TheWelcome.vue** - *(96 строк)* 🔗 Зависимости: [WelcomeItem, IconDocumentation, IconTooling, IconEcosystem, IconCommunity, IconSupport] `const openReadmeInEditor = () => fetch('/__open-in-editor?fi`
- **frontend/src/components/WelcomeItem.vue** - *(88 строк)* `<template> | <div class="item">`
- **frontend/src/components/icons/IconCommunity.vue** - *(8 строк)* `<template> | <svg xmlns="http://www.w3.org/2000/svg" width="20" height="2`
- **frontend/src/components/icons/IconDocumentation.vue** - *(8 строк)* `<template> | <svg xmlns="http://www.w3.org/2000/svg" width="20" height="1`
- **frontend/src/components/icons/IconEcosystem.vue** - *(8 строк)* `<template> | <svg xmlns="http://www.w3.org/2000/svg" width="18" height="2`
- **frontend/src/components/icons/IconSupport.vue** - *(8 строк)* `<template> | <svg xmlns="http://www.w3.org/2000/svg" width="20" height="2`
- **frontend/src/components/icons/IconTooling.vue** - *(20 строк)* `<!-- This icon is from <https://github.com/Templarian/Materi | <template>`
- **frontend/src/components/tasks/CategoryModal.vue** - *(98 строк)* 🔗 Зависимости: [tasks] `const emit = defineEmits(['close']) | const store = useTasksStore()`
- **frontend/src/components/tasks/TaskModal.vue** - *(180 строк)* 🔗 Зависимости: [tasks, types] `const props = defineProps<{ | taskToEdit?: Task | null`
- **frontend/src/components/tasks/TasksDashboard.vue** - *(382 строк)* 🔗 Зависимости: [tasks, user, vuedraggable, types, TaskModal, CategoryModal] `[Конфиг / Без сигнатур]`
- **frontend/src/router/index.ts** - *(29 строк)* 🔗 Зависимости: [HomeView] `export default router`
- **frontend/src/stores/counter.ts** - *(13 строк)* `export const useCounterStore = defineStore('counter', () =>`
- **frontend/src/stores/tasks.ts** - *(211 строк)* 🔗 Зависимости: [types] `export const useTasksStore = defineStore('tasks', () =>`
- **frontend/src/stores/user.ts** - *(59 строк)* `export interface UserProfile | export const useUserStore = defineStore('user', () =>`
- **frontend/src/types/index.ts** - *(24 строк)* `export interface Category | export interface Task`
- **frontend/src/views/AboutView.vue** - *(16 строк)* `<template> | <div class="about">`
- **frontend/src/views/HomeView.vue** - *(294 строк)* 🔗 Зависимости: [TasksDashboard, TelegramLogin] `const router = useRouter() | const isAuthenticated = ref(false)`
- **frontend/src/views/SettingsView.vue** - *(404 строк)* 🔗 Зависимости: [user] `const router = useRouter() | const userStore = useUserStore()`
- **nginx/nginx.conf** - *(27 строк)* `server { | listen 80;`
- **src/assets/main.css** - *(35 строк)* `@import './base.css'; | max-width: 100%; /* Убрали жесткое ограничение в 1280px */`


# Карта API-эндпоинтов

- `POST /register` *(в backend/auth.py)*
- `POST /token` *(в backend/auth.py)*
- `POST /telegram` *(в backend/auth.py)*
- `GET /me` *(в backend/auth.py)*
- `PUT /me` *(в backend/auth.py)*
- `PUT /password` *(в backend/auth.py)*
- `POST /telegram/request-code` *(в backend/auth.py)*
- `POST /telegram/verify-code` *(в backend/auth.py)*
- `GET /` *(в backend/main.py)*
- `GET /api/health` *(в backend/main.py)*
- `POST /categories` *(в backend/tasks.py)*
- `GET /categories` *(в backend/tasks.py)*
- `PUT /categories/{category_id}` *(в backend/tasks.py)*
- `DELETE /categories/{category_id}` *(в backend/tasks.py)*
- `POST /tasks` *(в backend/tasks.py)*
- `GET /tasks` *(в backend/tasks.py)*
- `PUT /tasks/reorder` *(в backend/tasks.py)*
- `PUT /tasks/{task_id}` *(в backend/tasks.py)*
- `DELETE /tasks/{task_id}` *(в backend/tasks.py)*
- `POST /tasks/ai` *(в backend/tasks.py)*
