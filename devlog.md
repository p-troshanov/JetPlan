# Devlog

Последние 25 завершённых задач, в которых изменялся код проекта.
Новые записи располагаются сверху.

## 2026-09-04 — Production static build frontend и исправление typecheck

**Работали над:** переводом frontend runtime с Vite dev server на статическую nginx-раздачу и устранением блокирующих ошибок TypeScript.

**Изменения:**
- frontend переведён на multi-stage Docker build с воспроизводимой установкой через `npm ci --no-audit --no-fund`, обязательным typecheck/build и минимальным nginx runtime; audit остаётся отдельной явной проверкой и не блокирует server build при зависании registry;
- добавлены SPA fallback, `/health`, cache headers для хешированных assets и ожидание готовности frontend внешним nginx;
- удалено production-проксирование HMR/WebSocket и обновлён порт frontend upstream;
- polling Telegram-входа теперь останавливается общей типизированной функцией, поэтому кнопка отмены не обращается к отсутствующему методу компонента;
- native date/time picker типизирован через `currentTarget`, а frontend `UserProfile` синхронизирован с backend-полем `auto_postpone_overdue`.

**Файлы:**
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `nginx/nginx.conf`
- `docker-compose.yml`
- `frontend/src/components/tasks/TaskModal.vue`
- `frontend/src/views/HomeView.vue`
- `frontend/src/stores/user.ts`
- `backlog.md`
- `devlog.md`

**Проверки:**
- `vue-tsc --build` — успешно;
- `vite build` — успешно;
- `docker buildx build --check ./frontend` — успешно, предупреждений Dockerfile нет;
- `docker buildx build --load --tag jetplan-frontend:codex-test ./frontend` — успешно, внутри образа прошли `npm ci` и `npm run build`;
- smoke-test временного frontend-контейнера — `/health` и прямой SPA route `/settings` вернули 200, Docker healthcheck перешёл в `healthy`;
- `docker compose config --quiet` с тестовым `APP_PORT` — успешно, остаётся предупреждение об устаревшем поле `version`;
- `nginx -t` для внешнего reverse proxy — успешно.

**Ограничения:**
- `npm audit` не завершился из-за зависшего обращения к registry; `npm ci` сообщил о 6 уязвимостях build dependency tree, отдельная P2-задача добавлена в backlog;
- server deploy в этой задаче не выполнялся.

## 2026-09-04 — Закрытие критических security gaps

**Работали над:** защитой Docker build context, ownership категорий задач и привязкой Telegram.

**Изменения:**
- backend image больше не копирует весь репозиторий, а `.dockerignore` исключает `.env`, локальные зависимости и артефакты из обоих build context;
- API создания и изменения задач проверяет принадлежность `category_id` текущему пользователю, Telegram AI ограничен категориями владельца;
- четырёхзначный Telegram-код заменён высокоэнтропийным HMAC challenge, привязанным к web-пользователю;
- frontend принимает полный одноразовый код, а backend отклоняет legacy-коды, подмену challenge и Telegram, уже привязанный к другому аккаунту;
- добавлены 10 unit/security-тестов и документация security controls.

**Файлы:**
- `.dockerignore`
- `Dockerfile`
- `frontend/.dockerignore`
- `backend/access_control.py`
- `backend/security.py`
- `backend/auth.py`
- `backend/bot.py`
- `backend/tasks.py`
- `backend/schemas.py`
- `frontend/src/views/SettingsView.vue`
- `tests/test_access_control.py`
- `tests/test_docker_context.py`
- `tests/test_security.py`
- `docs/security/critical-controls.md`
- `backlog.md`
- `devlog.md`

**Проверки:**
- `venv\Scripts\python.exe -m unittest discover -s tests -v` — успешно, 10 тестов;
- `venv\Scripts\python.exe -m compileall -q backend tests` — успешно;
- `venv\Scripts\python.exe -m pip check` — успешно;
- импорт `backend.main` — успешно;
- `vite build` — успешно;
- `docker buildx build --check` для backend и frontend — успешно, предупреждений нет;
- `docker compose config --quiet` — синтаксически успешно, остаётся предупреждение об отсутствующем `APP_PORT`;
- `vue-tsc --build` — остаются прежние 10 ошибок из отдельной P1-задачи; новых ошибок текущая работа не добавила.

**Ограничения:**
- фактический server deploy и очистка старых image layers не выполнялись;
- при публикации старого образа за пределы доверенного сервера требуется ротация секретов.

## 2026-09-03 — Обновление deployment-скрипта Jetplan

**Работали над:** безопасным обновлением и перезапуском Jetplan на сервере через Podman Compose.

**Изменения:**
- серверный путь проекта исправлен на `/home/pasha/jetplan`;
- принудительный сброс Git заменён на безопасное fast-forward обновление с остановкой при локальных изменениях tracked-файлов;
- удалена команда очистки Redis, которого нет в `docker-compose.yml` Jetplan;
- добавлены проверки окружения, Compose-конфигурации и готовности backend через `/api/health`;
- итоговый вывод ограничен состоянием контейнеров и последними строками логов backend.

**Файлы:**
- `../deploy_jetplan.sh`

**Проверки:**
- `bash -n C:/PYTHON/deploy_jetplan.sh` — успешно;
- состав Compose-сервисов и endpoint `/api/health` сверены с текущим кодом проекта;
- фактический деплой на сервер не запускался.
