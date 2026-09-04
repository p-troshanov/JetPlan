# Backlog

## P0 — Критично

- [x] Исключить секреты и локальные артефакты из Docker build context
  - Контекст: до исправления корневой `Dockerfile` выполнял `COPY . .`, а `.dockerignore` отсутствовал, поэтому существующий `.env` попадал в образ вместе с локальными каталогами.
  - Где: `Dockerfile`, корневой Docker build context, `frontend/Dockerfile`.
  - Результат: backend копирует только `backend/`, оба build context защищены `.dockerignore`; server rebuild и условная ротация вынесены в отдельный операционный пункт ниже.

- [x] Закрыть cross-user доступ к категориям через задачи
  - Контекст: до исправления `create_task` и `update_task` принимали любой `category_id`, не проверяя принадлежность категории текущему пользователю.
  - Где: `backend/tasks.py`, контракты создания и обновления задач.
  - Результат: добавлен общий owner check до записи задачи и негативные unit-тесты; Telegram AI также ограничен allowlist категорий владельца.

- [x] Защитить привязку Telegram от перебора глобального 4-значного кода
  - Контекст: до исправления любой зарегистрированный пользователь мог перебирать глобальный четырёхзначный код в `/api/auth/telegram/verify-code`; challenge не был привязан к инициатору.
  - Где: `backend/auth.py`, `TelegramLinkCode`, auth rate limiting.
  - Результат: используется высокоэнтропийный HMAC challenge с user binding, ограничением длины и негативными security-тестами; общий rate limiting остаётся отдельной P2-задачей.

- [x] Пересобрать server images и оценить необходимость ротации секретов
  - Контекст: исправление исключает `.env` только из новых сборок; старые локальные/server image layers могли сохранить прежний файл. Публикация образов в registry из репозитория не подтверждена.
  - Где: server container storage, возможный registry, значения `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`.
  - Результат: server обновлён до `281b9e7`, backend и frontend пересобраны как `c6f5d749c2ec` и `546c4d06b650`; старые неиспользуемые образы `3e651cd9b198` и `41c0351292c7` удалены после проверки ссылок. В старом backend-образе подтверждено наличие `/app/.env`, в старом frontend-образе env-файлов не было. Публичные `/health`, `/api/health` и `/settings` вернули 200.
  - Ротация: в репозитории нет подтверждённого registry publish workflow, поэтому без свидетельств экспорта или публикации старого образа секреты не ротировались. Если образ когда-либо покидал доверенный сервер, нужно ротировать `SECRET_KEY`, `TELEGRAM_BOT_TOKEN` и `DATABASE_URL`.

## P1 — Высокий приоритет

- [x] Перевести frontend с Vite dev server на production static build
  - Контекст: production-контейнер запускает `npm run dev`, а nginx проксирует HMR/WebSocket. При рестартах и обновлениях клиент получает dev-runtime Vue/Vite и нестабильные ответы вместо неизменяемых статических assets.
  - Где: `frontend/Dockerfile`, `nginx/nginx.conf`, `docker-compose.yml`, `frontend/vite.config.ts`.
  - Результат: multi-stage image выполняет `npm ci` и обязательный `npm run build`, runtime nginx раздаёт только `dist`, поддерживает SPA fallback и проверяемый `/health`; внешний nginx больше не проксирует Vite/HMR.

- [x] Исправить падающий frontend typecheck и подтверждённый runtime-сбой Telegram-формы
  - Контекст: `vue-tsc --build` завершается с 10 ошибками; обработчик кнопки отмены компилируется в отсутствующий `component.clearInterval`, что вызывает runtime `TypeError`.
  - Где: `frontend/src/views/HomeView.vue`, `frontend/src/components/tasks/TaskModal.vue`, `frontend/src/views/SettingsView.vue`, `frontend/src/stores/user.ts`.
  - Результат: polling останавливает типизированная функция, native picker использует `currentTarget`, `UserProfile` синхронизирован с backend-полем `auto_postpone_overdue`; typecheck проходит и входит в production image build.

- [ ] Диагностировать и восстановить текстовые запросы к Groq
  - Контекст: Telegram сообщает только общую ошибку Groq; репозиторий жёстко использует `https://api.groq.com/openai/v1/chat/completions` и модель `llama-3.3-70b-versatile`, а актуальность пользовательского ключа и runtime-ответ провайдера из репозитория определить нельзя.
  - Где: `backend/bot.py`, `backend/tasks.py`, безопасные server logs и пользовательские AI-настройки без вывода значений ключей.
  - Критерии: контролируемый текстовый запрос отдельно проверен для Telegram и web API; ошибки ключа, модели, endpoint, rate limit, timeout и разбора JSON различимы в безопасных логах и понятны пользователю; секреты не попадают в ответы и логи.
  - Выполнено в коде: Groq переведён на общий адаптер; endpoint и модель сверены с официальной документацией; authentication/model/endpoint/rate limit/timeout/payload errors различаются без логирования ключа или response body; web и Telegram используют один проверенный контракт.
  - Проверено: mock contract-тесты проходят; в доступном хвосте server logs ошибок Groq нет.
  - Осталось: контролируемый runtime-запрос с сохранённым ключом не запускался без отдельного явного разрешения владельца на использование credential во внешнем запросе.

- [ ] Централизовать обработку API и исключить Vue unhandled handler errors
  - Контекст: async-обработчики категорий, смены статуса, удаления, сортировки и настроек не перехватывают сетевые ошибки; временный 502/рестарт backend превращается в Vue `Unhandled error during execution of native event handler`. Часть GET-запросов маскирует 5xx как пустые данные.
  - Где: `frontend/src/stores/tasks.ts`, `frontend/src/stores/user.ts`, `frontend/src/components/tasks/CategoryModal.vue`, `frontend/src/components/tasks/TaskModal.vue`, `frontend/src/components/tasks/TasksDashboard.vue`, `frontend/src/views/SettingsView.vue`.
  - Следующий шаг: добавить общий API-клиент с нормализацией ошибок, обработкой 401/5xx, пользовательскими error states и тестами отказов.

- [ ] Довести существующие экраны до полноценной мобильной адаптивности
  - Контекст: базовые media queries уже есть, но верхняя панель и AI/search-контролы собраны в одну строку, часть размеров задана inline, категории скрываются из карточек, а header, auth, settings и модальные формы не проверены как единый мобильный сценарий.
  - Где: `frontend/src/App.vue`, `frontend/src/views/HomeView.vue`, `frontend/src/views/SettingsView.vue`, `frontend/src/components/tasks/TasksDashboard.vue`, `frontend/src/components/tasks/TaskModal.vue`, `frontend/src/components/tasks/CategoryModal.vue`, `frontend/src/assets/tasks.css`.
  - Зависит от: исправления frontend typecheck; мобильная раскладка будущего канбана входит в задачи канбана, а не в этот пункт.
  - Критерии: на ширинах 360, 390, 768 и 1024 px нет горизонтального скролла и перекрытий; можно войти, просматривать и фильтровать задачи, создать/изменить задачу и категорию, открыть настройки и выйти; модалки прокручиваются внутри viewport, основные действия доступны с клавиатуры и имеют удобную touch-зону.
  - Следующий шаг: провести viewport-аудит основных состояний, затем исправлять layout mobile-first без изменения backend и API contracts.

- [ ] Сделать startup и healthcheck backend достоверными
  - Контекст: ошибки подключения к БД и runtime-DDL перехватываются, после чего приложение продолжает запуск и `/api/health` всегда отвечает `healthy`; Compose ждёт только старт контейнеров, а не готовность сервисов.
  - Где: `backend/main.py`, `docker-compose.yml`, deployment healthcheck.
  - Следующий шаг: завершать startup при критической ошибке БД, проверять DB readiness в health endpoint, добавить healthchecks и зависимости по состоянию здоровья.

- [ ] Исключить публичный 502 после пересоздания frontend при деплое
  - Контекст: deploy `00cbf5a` пересоздал `frontend`, но оставил `nginx` в состоянии `up-to-date`; reverse proxy сохранил старый upstream-адрес, поэтому `/health` и `/settings` отвечали 502 до ручного `podman compose restart nginx`, тогда как `/api/health` оставался доступен.
  - Где: `C:/PYTHON/deploy_jetplan.sh`, серверный `/home/pasha/deploy_jetplan.sh`, `docker-compose.yml`, nginx upstream resolution.
  - Следующий шаг: гарантированно перезапускать или пересоздавать nginx после backend/frontend и завершать deploy только после публичных smoke-проверок `/health`, `/api/health` и прямого SPA route.

- [ ] Заменить runtime-DDL полноценными файловыми миграциями
  - Контекст: `create_all` и набор `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` не контролируют версии схемы, constraints и rollback; серверная схема может отличаться от свежей установки.
  - Где: `backend/main.py`, `backend/database.py`, legacy runtime-DDL рядом с новым `backend/migrations/` runner.
  - Прогресс: AI schema change уже оформлен версионируемым SQL-файлом и обязательным runner; legacy `create_all`/`ALTER TABLE` ещё не перенесены в baseline.
  - Следующий шаг: зафиксировать baseline существующей схемы, перенести оставшиеся runtime-DDL и удалить конкурирующий путь изменения schema.

- [x] Добавить provider-neutral AI-контур и поддержку OpenRouter с выбором модели
  - Контекст: профиль хранит только `ai_provider` и один `ai_api_key`; settings предлагает Gemini и Groq, но backend принимает только Groq, использует его URL и модель напрямую. Для OpenRouter требуется сохраняемый `ai_model`, который показывается и валидируется только при выборе OpenRouter.
  - Где: `backend/database.py`, файловая миграция, `backend/schemas.py`, единый AI provider adapter, `backend/bot.py`, `backend/tasks.py` для сохраняемого web AI endpoint, `frontend/src/views/SettingsView.vue`, `frontend/src/stores/user.ts`.
  - Зависит от: диагностики Groq, централизованной обработки API и файлового migration workflow.
  - Критерии: пользователь выбирает OpenRouter, вводит API key и обязательный model ID, после повторного входа настройки сохраняются; Telegram-текст и каждый сохранённый web AI-сценарий используют выбранного провайдера; Groq не регрессирует; backend отклоняет неизвестные provider/model combinations, а UI не рекламирует неподдерживаемый Gemini.
  - Архитектура: provider-specific URL, headers, model defaults, timeout и разбор ошибок находятся за одним интерфейсом; ключи не логируются и не возвращаются целиком в profile response — UI получает только признак/маску сохранённого секрета.
  - Результат: добавлен единый адаптер Groq/OpenRouter, обязательный `ai_model` для OpenRouter, файловая миграция и безопасный profile response только с признаками сохранённых ключей; Telegram и web используют общий контур, Gemini удалён из UI.

- [x] Сделать голосовой ввод Telegram независимым от выбранного текстового AI-провайдера
  - Контекст: `handle_voice` сейчас требует `ai_provider == 'groq'`, использует тот же `ai_api_key` для Groq Whisper и после распознавания снова вызывает Groq-only текстовый путь. При выборе OpenRouter голосовое сообщение гарантированно отклоняется до распознавания.
  - Где: `backend/bot.py`, AI/STT provider contracts, профиль и настройки отдельных credentials только если выбранная STT-схема этого требует.
  - Зависит от: provider-neutral AI-контура с OpenRouter.
  - Критерии: голос Telegram распознаётся явно выбранным/поддерживаемым STT-контуром, а полученный текст обрабатывается выбранной OpenRouter или Groq моделью; отсутствие STT-настройки даёт точную инструкцию, не ломая текстовые сообщения; создание и редактирование задачи голосом покрыты тестами успешного и ошибочного путей.
  - Результат: Groq Whisper использует отдельные `stt_provider`/`stt_api_key`, после транскрибации текст поступает в выбранный Groq или OpenRouter; миграция сохраняет голос прежним Groq-пользователям, успешные create/edit и ошибочный STT-путь покрыты тестами.

- [ ] Проверять владельца во всех Telegram callback-операциях
  - Контекст: редактирование категории, удаление/завершение/откладывание задачи и approve/deny интерактивного входа выбирают запись только по ID без сверки с `callback.from_user.id`.
  - Где: `backend/bot.py`, callback handlers начиная с `process_auth_approve`.
  - Следующий шаг: разрешать действие только владельцу Telegram/profile и добавить тесты с callback другого пользователя.

- [ ] Не терять напоминания при ошибке отправки Telegram
  - Контекст: `run_reminders` выставляет `reminder_sent = True` даже после исключения `bot.send_message`, поэтому временный сбой Telegram навсегда подавляет повторную доставку.
  - Где: `backend/bot.py`, `run_reminders`.
  - Следующий шаг: отмечать доставку только после успеха, хранить число попыток/последнюю ошибку и применять ограниченный retry/backoff.

## P2 — Средний приоритет

- [x] Заменить AI-поле в списке задач обычным поиском с подсветкой совпадений
  - Контекст: поле между «Создать задачу» и «Фильтры» сейчас отправляет запрос в `/api/tasks/ai`; требуемый сценарий — мгновенно фильтровать уже загруженные задачи по тексту без обращения к нейросети.
  - Где: `frontend/src/components/tasks/TasksDashboard.vue`, `frontend/src/assets/tasks.css`; после подтверждения отсутствия других web-consumers — судьба `sendAiQuery` и `/api/tasks/ai`.
  - Критерии: поиск запускается при вводе, нечувствителен к регистру, сочетается с текущими status/date/category/priority filters, очищается одним действием, удобен на мобильной ширине и показывает корректный empty state; все вхождения запроса в описании слегка подсвечены без `v-html` и XSS-риска.
  - Не входит: семантический/серверный поиск и изменение Telegram AI-сценариев.
  - Следующий шаг: добавить локальный `searchQuery` в общую filter model и безопасный renderer совпавших фрагментов; удалить web AI-контрол только после проверки его оставшихся consumers.

- [x] Добавить поиск по категориям в создание и редактирование задачи
  - Контекст: `TaskModal` использует обычный `<select>`, поэтому в длинном списке категорию нельзя быстро найти по части названия.
  - Где: `frontend/src/components/tasks/TaskModal.vue`, при необходимости переиспользуемый category combobox и `frontend/src/assets/tasks.css`.
  - Критерии: ввод фильтрует категории без учёта регистра, доступны клавиатурная навигация и выбор, «Без категории» остаётся явным вариантом, а при редактировании текущая категория корректно отображается даже до ввода поиска; в payload по-прежнему уходит только owned `category_id` или `null`.
  - Не входит: создание/переименование категорий внутри TaskModal и изменение backend contract.
  - Результат: `CategoryCombobox` фильтрует название и подкатегорию без учёта регистра, поддерживает стрелки/Enter/Escape, явный вариант «Без категории» и корректно показывает текущий выбор при редактировании; payload contract не изменён.

- [x] Добавить страницу канбана и первый режим «Приоритет» с общими фильтрами
  - Контекст: отдельного route и канбан-представления нет; фильтры списка локальны в `TasksDashboard`, поэтому их defaults и поведение пока нельзя переиспользовать на другой странице. `vuedraggable` и `PUT /api/tasks/{id}` уже доступны.
  - Где: `frontend/src/router/index.ts`, header в `frontend/src/views/HomeView.vue`, новый Kanban view/components, общий filter state в frontend store/composable, `frontend/src/stores/tasks.ts`.
  - Зависит от: обычного поиска, исправления frontend typecheck и централизованной обработки API.
  - Критерии: рядом с «Настройки» есть ссылка на защищённую страницу канбана; выбранные/default filters совпадают со списком задач; режим «Приоритет» показывает три колонки high/medium/low; перенос между колонками сохраняет новый priority через существующий owned task API и откатывается/перезагружается при ошибке; desktop и mobile layouts пригодны для drag и альтернативного keyboard/tap перемещения.
  - Архитектура: список и канбан используют один filter contract и одну task collection, не дублируют правила фильтрации и enum приоритетов.
  - Результат: добавлены защищённый `/kanban`, общие search/filter state и три колонки приоритета; drag и доступный `select` сохраняют `priority` через owned task API, а store выполняет оптимистичное обновление с откатом и повторной загрузкой при ошибке.

- [x] Добавить в канбан режим «Категория»
  - Контекст: режим должен строить колонки из категорий текущего пользователя и менять `category_id` при переносе задачи; backend owner check уже является source of truth.
  - Где: Kanban view/components, `frontend/src/stores/tasks.ts`, существующий `PUT /api/tasks/{id}`.
  - Зависит от: готового режима «Приоритет» и общего filter contract.
  - Критерии: переключение режима не сбрасывает фильтры; есть колонка «Без категории» и колонки доступных категорий; перенос сохраняет `category_id`/`null`, сразу обновляет badge и откатывается при 4xx/5xx; удалённая или чужая категория не приводит к потере задачи или cross-user изменению.
  - Результат: колонки строятся из owned категорий и «Без категории», общий move-механизм обновляет `category_id`/`null`, недоступная категория не становится целью и не скрывает задачу; backend owner check и его негативный тест остаются source of truth.

- [x] Добавить в канбан недельный режим «Дата»
  - Контекст: нужны семь последовательных колонок от сегодня до дня `+6`; перенос должен менять дату задачи, не повреждая время, recurrence и reminder semantics. Текущий default `hideFutureTasks=true` противоречит показу будущих дней и требует явного правила приоритета.
  - Где: Kanban date mode, общая filter model, date/time helpers, `frontend/src/stores/tasks.ts`, существующий task update contract.
  - Зависит от: готового режима «Приоритет» и общего filter contract.
  - Критерии: первая колонка всегда соответствует локальному «сегодня», остальные — следующим шести датам; перенос сохраняет time-of-day и связанные поля, меняя только календарную дату; week horizon в этом режиме не подавляется `hideFutureTasks`, остальные общие фильтры работают одинаково; поведение задач без даты и вне недели явно выбрано и не скрывает их без доступного пути.
  - Результат: добавлены семь локальных дней, «Без даты» и read-only источник «Вне недели»; `hideFutureTasks` не подавляет недельный горизонт, перенос сохраняет локальное время и связанные recurrence/reminder fields, а timezone/DST contract и граничные тесты зафиксированы в `docs/features/kanban.md`.

- [ ] Зафиксировать версии Python-зависимостей и проверять воспроизводимость образа
  - Контекст: все записи в `requirements.txt` не имеют версий, поэтому одинаковый commit может получить разные FastAPI, SQLAlchemy, Pydantic и aiogram при новой сборке.
  - Где: `requirements.txt`, backend image build.
  - Следующий шаг: сформировать проверенный lock/constraints-файл и добавить smoke-test импорта и запуска API в CI.

- [ ] Разобрать npm audit уязвимости frontend build toolchain
  - Контекст: чистый `npm ci` при production image build сообщает о 6 уязвимостях (1 low, 4 high, 1 critical) и peer-конфликте `vite-plugin-vue-devtools` с Vite 8; runtime image содержит только статические файлы и nginx, но build/CI-контур требует отдельной проверки.
  - Где: `frontend/package.json`, `frontend/package-lock.json`, frontend build/CI.
  - Следующий шаг: получить полный `npm audit` в окружении со стабильным доступом к registry, определить direct/transitive зависимости и обновить lockfile минимально, подтвердив typecheck и production build без `--force`.

- [ ] Согласовать опциональный `USE_PGVECTOR` с runtime-зависимостями
  - Контекст: конфигурация поддерживает `USE_PGVECTOR`, но пакет `pgvector` отсутствует в `requirements.txt`; чистый backend image упадёт на импорте при включении флага. Compose также не передаёт этот флаг явно.
  - Где: `backend/config.py`, `backend/database.py`, `requirements.txt`, `docker-compose.yml`.
  - Следующий шаг: либо удалить неиспользуемый режим, либо добавить зафиксированную зависимость и явную env-конфигурацию с отдельным startup test.

- [ ] Валидировать обязательные Compose env-переменные до запуска
  - Контекст: локальный `docker compose config` предупреждает, что `APP_PORT` не задан, а существующий `.env` не содержит такого ключа; публикация порта становится неоднозначной.
  - Где: `docker-compose.yml`, будущий `.env.example`, deployment preflight.
  - Следующий шаг: использовать required interpolation (`${APP_PORT:?...}`), добавить безопасный `.env.example` и проверку значений без вывода секретов.

- [ ] Добавить автоматические проверки frontend/backend и deployment smoke tests
  - Контекст: в репозитории нет тестов, frontend lint/test scripts и проверки browser-сценариев; ошибки сейчас обнаруживаются уже при ручном открытии сервера.
  - Где: `frontend/package.json`, отсутствующие `tests/` и CI-конфигурация.
  - Следующий шаг: добавить минимум contract/API tests, component tests критичных обработчиков, production-build smoke test и проверку прямого открытия SPA routes.

- [x] Исправить утечку listener `visibilitychange`
  - Контекст: listener добавляется анонимной функцией, а удаляется ссылкой на `syncOnFocus`, поэтому после повторных mount остаются лишние фоновые запросы.
  - Где: `frontend/src/components/tasks/TasksDashboard.vue`.
  - Следующий шаг: хранить одну именованную функцию-обработчик и удалять ту же ссылку при unmount.

- [ ] Валидировать и экранировать пользовательский текст в Telegram HTML-сообщениях
  - Контекст: описания задач, категории и распознанный текст вставляются в сообщения с `parse_mode="HTML"` без escaping; символы `<`, `>` и `&` могут ломать отправку или менять формат сообщения.
  - Где: `backend/bot.py`.
  - Следующий шаг: централизованно экранировать динамические значения и покрыть тестами HTML-подобный пользовательский ввод.

- [ ] Усилить auth validation и rate limiting
  - Контекст: login/register и чувствительные Telegram endpoints не имеют ограничения попыток; регистрация и смена пароля не задают минимальные требования к логину/паролю.
  - Где: `backend/auth.py`, reverse proxy/API middleware.
  - Следующий шаг: определить лимиты, единый контракт валидации и тесты brute-force/abuse сценариев.

- [ ] Добавить frontend error reporting и полезные серверные логи
  - Контекст: централизованного `app.config.errorHandler`, correlation id и сбора browser runtime errors нет; историческую Vue-ошибку нельзя восстановить без снимка консоли пользователя.
  - Где: `frontend/src/main.ts`, nginx/backend logging и operations-документация.
  - Следующий шаг: определить безопасный канал client error reporting, структурировать backend/nginx логи и документировать диагностику 4xx/5xx.

- [ ] Ввести единый auth state и защиту frontend routes
  - Контекст: наличие строки в `localStorage` сразу считается успешной авторизацией, `/settings` открывается без route guard, а валидность токена проверяется позднее и неодинаково в разных stores.
  - Где: `frontend/src/views/HomeView.vue`, `frontend/src/router/index.ts`, `frontend/src/stores/user.ts`, `frontend/src/stores/tasks.ts`.
  - Следующий шаг: загружать сессию через `/api/auth/me`, централизованно обрабатывать истёкший токен и перенаправлять гостя со страниц, требующих авторизации.

- [ ] Создать актуальный корневой README и runbook запуска
  - Контекст: корневой `README.md` отсутствует, а `frontend/README.md` остаётся текстом шаблона Vue и не описывает реальный production build, env requirements и проверки.
  - Где: корень проекта, `frontend/README.md`, будущий `docs/operations/`.
  - Следующий шаг: документировать локальный запуск, сборку, обязательные env-переменные без значений, healthcheck и порядок диагностики.

## P3 — Низкий приоритет / идеи

- [ ] Удалить или оформить оставшиеся Vue template-файлы и служебные заголовки исходников
  - Контекст: в рабочем дереве остаются неиспользуемые template-компоненты/`AboutView`, а hand-written frontend/backend файлы не имеют обязательной второй строки с назначением.
  - Где: `frontend/src/components/HelloWorld.vue`, `frontend/src/components/TheWelcome.vue`, `frontend/src/components/WelcomeItem.vue`, `frontend/src/components/icons/`, `frontend/src/views/AboutView.vue`, исходники frontend/backend.
  - Следующий шаг: отдельно подтвердить неиспользуемые файлы, удалить только мёртвый scaffold и добавить безопасные описания назначения.
