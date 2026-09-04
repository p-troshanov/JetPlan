-- backend/migrations/001_provider_neutral_ai.sql
-- Добавляет отдельные настройки LLM-модели и Groq Whisper без утечки сохранённых ключей.
ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_model VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS stt_provider VARCHAR DEFAULT 'groq';
ALTER TABLE users ADD COLUMN IF NOT EXISTS stt_api_key VARCHAR;

UPDATE users
SET stt_api_key = ai_api_key
WHERE stt_api_key IS NULL
  AND ai_provider = 'groq'
  AND ai_api_key IS NOT NULL;

UPDATE users
SET ai_provider = 'groq'
WHERE ai_provider IS NULL OR ai_provider NOT IN ('groq', 'openrouter');

UPDATE users
SET stt_provider = 'groq'
WHERE stt_provider IS NULL OR stt_provider <> 'groq';

ALTER TABLE users ALTER COLUMN ai_provider SET DEFAULT 'groq';
ALTER TABLE users ALTER COLUMN stt_provider SET DEFAULT 'groq';
