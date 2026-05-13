:: _start_all.bat
@echo off
chcp 65001 >nul

:: Принудительно переходим в папку со скриптом (корень проекта)
cd /d "%~dp0"

echo === Запуск проекта Jetplan (Backend + Frontend) ===

:: Проверка на наличие виртуального окружения
if not exist "venv\Scripts\python.exe" (
    echo ОШИБКА: Виртуальное окружение не найдено!
    echo Пожалуйста, сначала запустите 1_install_dependencies.bat
    pause
    exit /b
)

:: Запуск Backend в новом окне (теперь он сам подтянет настройки из .env)
echo Запускаем Backend (FastAPI)...
start "Jetplan Backend (FastAPI)" cmd /k "venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8008 --reload"

:: Пауза на 3 секунды, чтобы бэкенд успел подняться до запуска фронтенда
echo Ожидание запуска бэкенда...
timeout /t 3 /nobreak >nul

:: Запуск Frontend в новом окне
echo Запускаем Frontend (Vite)...
start "Jetplan Frontend (Vite)" cmd /k "cd frontend && npm run dev"

echo.
echo Оба сервера успешно запущены в новых окнах!
echo Это окно можно закрыть.
pause