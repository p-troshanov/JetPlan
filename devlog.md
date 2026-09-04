# Devlog

Последние 25 завершённых задач, в которых изменялся код проекта.
Новые записи располагаются сверху.

## 2026-09-04 — Устранение утечки visibilitychange listener

**Работали над:** lifecycle фонового обновления списка задач во frontend.

**Изменения:**
- обработчик `visibilitychange` вынесен в стабильную именованную функцию;
- при размонтировании компонента удаляется та же ссылка, которая была зарегистрирована, поэтому повторные mount не накапливают фоновые запросы.

**Файлы:**
- `frontend/src/components/tasks/TasksDashboard.vue`
- `backlog.md`
- `devlog.md`

**Проверки:**
- `node node_modules/vue-tsc/bin/vue-tsc.js --build` — успешно;
- `node node_modules/vite/bin/vite.js build` — успешно.

## 2026-09-04 — Серверная пересборка и очистка Jetplan images

**Работали над:** поставкой исправлений Docker build context, пересборкой server images и оценкой необходимости ротации секретов.

**Изменения:**
- commits `8ebe290` и `281b9e7` отправлены в `origin/main` и получены сервером через fast-forward;
- frontend image build использует `npm ci --no-audit --no-fund`, чтобы обязательная lockfile-установка не зависела от нестабильных audit/fund-запросов;
- штатная команда `deploy_jetplan` и обязательный синтаксис `podman compose` зафиксированы в корневом README;
- server-контейнеры переключены на backend image `c6f5d749c2ec` и frontend image `546c4d06b650`;
- старые неиспользуемые Jetplan images `3e651cd9b198` и `41c0351292c7` удалены; в старом backend image подтверждено наличие `/app/.env` без чтения значений.

**Файлы:**
- `frontend/Dockerfile`
- `README.md`
- `backlog.md`
- `devlog.md`

**Проверки:**
- backend unit/security tests — 10 из 10 успешно;
- Python compileall и `pip check` — успешно;
- frontend typecheck и production build локально и внутри server image — успешно;
- Dockerfile build check — успешно;
- server `podman compose ps` — backend, database, frontend и nginx запущены; frontend — `healthy`;
- публичные `/health`, `/api/health` и `/settings` — HTTP 200;
- удаление двух прежних image ID подтверждено, новые image ID сохранились.

**Ограничения:**
- registry publication старого образа не подтверждена; секреты не ротировались. Если старый backend image экспортировался или публиковался за пределами доверенного сервера, требуется ротация `SECRET_KEY`, `TELEGRAM_BOT_TOKEN` и `DATABASE_URL`.

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
