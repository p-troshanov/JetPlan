# AI-провайдеры и распознавание речи

## Назначение

JetPlan использует один provider-neutral контур для структурированных текстовых ответов в web API и Telegram. Распознавание Telegram voice отделено от текстового провайдера: сначала STT возвращает текст, затем этот текст обрабатывает выбранный LLM.

## Матрица поддержки

| Сценарий | Провайдер | Модель | Credential |
|---|---|---|---|
| Текстовые команды | Groq | `llama-3.3-70b-versatile` | `ai_api_key` |
| Текстовые команды | OpenRouter | обязательный пользовательский `provider/model` | `ai_api_key` |
| Telegram voice STT | Groq | `whisper-large-v3` | отдельный `stt_api_key` |

Gemini не поддерживается и не показывается в настройках. Backend принимает только перечисленные комбинации. Для OpenRouter проверяется синтаксис model ID; фактическая доступность модели определяется самим OpenRouter при запросе.

## Контракты

`backend/ai.py` владеет следующими provider-specific деталями:

- endpoint, headers и модель по умолчанию;
- timeout;
- JSON mode и разбор `choices[0].message.content`;
- классификация authentication, model, endpoint, rate limit, timeout, network, upstream и payload errors;
- Groq Whisper multipart-запрос.

`backend/tasks.py` и `backend/bot.py` формируют только предметный prompt и обрабатывают уже разобранный JSON. Они не хранят provider URLs или собственные HTTP-разборщики.

Поля профиля:

- `ai_provider`: `groq` или `openrouter`;
- `ai_model`: обязательный model ID только для OpenRouter;
- `ai_api_key`: credential выбранного текстового провайдера;
- `stt_provider`: сейчас только `groq`;
- `stt_api_key`: credential Groq Whisper.

Ответ `/api/auth/me` никогда не содержит значения `ai_api_key` и `stt_api_key`. Вместо них frontend получает `ai_api_key_configured` и `stt_api_key_configured`. Пустое поле ключа при сохранении настроек сохраняет прежний credential.

## Миграция

`backend/migrations/001_provider_neutral_ai.sql` добавляет model/STT-поля, переводит неподдерживаемые legacy provider values на Groq и копирует существующий `ai_api_key` в `stt_api_key` только для прежних Groq-профилей. Это сохраняет голосовой ввод для существующих Groq-пользователей и позволяет независимо заменить любой из двух ключей позже.

SQL-файлы применяются по имени через `backend/migrations/runner.py`; выполненные версии фиксируются в `schema_migrations`. Ошибка новой файловой миграции блокирует startup.

## Безопасные ошибки и логи

Пользователь получает короткую инструкцию: заменить ключ, проверить модель, дождаться снятия лимита или повторить запрос. В server log записываются только provider, operation, нормализованный code, HTTP status, безопасный request ID и model ID. Тело ответа, prompt, аудио и API-ключи не логируются.

## Проверка

Mock contract-тесты покрывают успешные Groq/OpenRouter ответы, authentication, model, rate limit, timeout, некорректный payload и Groq Whisper. Telegram-тесты отдельно проверяют передачу распознанного текста в сценарии создания и редактирования задачи и отказ при отсутствующей STT-настройке.

Для runtime-проверки с реальным credential следует выполнить минимальный JSON-запрос отдельно от пользовательского сценария и фиксировать только HTTP status, provider error code и наличие completion. Значение ключа и provider response body выводить нельзя.

Актуальные внешние контракты: [Groq Chat API](https://console.groq.com/docs/api-reference), [Groq Speech to Text](https://console.groq.com/docs/speech-to-text), [OpenRouter Chat Completions](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request).
