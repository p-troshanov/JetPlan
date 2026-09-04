# tests/test_ai.py
# Проверяет provider-neutral AI/STT-контур, безопасные ошибки и profile contract ключей.
import asyncio
import unittest

from backend.ai import (
    AIProviderError,
    AISettingsError,
    GROQ_DEFAULT_MODEL,
    complete_json,
    transcribe_audio,
    validate_ai_selection,
)
from backend.schemas import UserProfileResponse


class FakeResponse:
    def __init__(self, status: int, payload: object, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.payload = payload
        self.headers = headers or {}

    async def json(self, content_type=None):
        return self.payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSession:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.calls: list[tuple[str, dict]] = []

    def post(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class AISettingsTests(unittest.TestCase):
    def test_groq_uses_fixed_model_and_openrouter_requires_model(self) -> None:
        self.assertEqual(validate_ai_selection("groq", None), ("groq", None))
        self.assertEqual(
            validate_ai_selection("openrouter", "anthropic/claude-sonnet-4.5"),
            ("openrouter", "anthropic/claude-sonnet-4.5"),
        )
        with self.assertRaises(AISettingsError):
            validate_ai_selection("openrouter", None)
        with self.assertRaises(AISettingsError):
            validate_ai_selection("gemini", None)

    def test_profile_response_never_contains_secret_fields(self) -> None:
        self.assertNotIn("ai_api_key", UserProfileResponse.model_fields)
        self.assertNotIn("stt_api_key", UserProfileResponse.model_fields)
        self.assertIn("ai_api_key_configured", UserProfileResponse.model_fields)
        self.assertIn("stt_api_key_configured", UserProfileResponse.model_fields)


class AIProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_groq_success_uses_default_model(self) -> None:
        session = FakeSession(FakeResponse(200, {
            "choices": [{"message": {"content": '{"intent":"filter"}'}}],
        }))

        result = await complete_json(
            provider="groq",
            api_key="secret-key",
            model=None,
            messages=[{"role": "user", "content": "test"}],
            http_session=session,
        )

        self.assertEqual(result, {"intent": "filter"})
        url, request = session.calls[0]
        self.assertEqual(url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(request["json"]["model"], GROQ_DEFAULT_MODEL)
        self.assertNotIn("secret-key", str(request["json"]))

    async def test_openrouter_uses_selected_model_and_attribution(self) -> None:
        session = FakeSession(FakeResponse(200, {
            "choices": [{"message": {"content": "```json\n{\"ok\":true}\n```"}}],
        }))

        result = await complete_json(
            provider="openrouter",
            api_key="openrouter-key",
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": "test"}],
            http_session=session,
        )

        self.assertEqual(result, {"ok": True})
        url, request = session.calls[0]
        self.assertEqual(url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(request["json"]["model"], "openai/gpt-oss-20b")
        self.assertTrue(request["json"]["provider"]["require_parameters"])
        self.assertEqual(request["headers"]["X-OpenRouter-Title"], "JetPlan")

    async def test_auth_rate_model_timeout_and_payload_errors_are_distinct(self) -> None:
        cases = [
            (FakeResponse(401, {"error": {"message": "invalid key"}}), "authentication", 400),
            (FakeResponse(429, {"error": {"message": "rate limit"}}), "rate_limit", 429),
            (FakeResponse(404, {"error": {"message": "model not found"}}), "model", 400),
            (FakeResponse(404, {"error": {"message": "route not found"}}), "endpoint", 502),
            (FakeResponse(503, {"error": {"message": "unavailable"}}), "provider_unavailable", 502),
            (asyncio.TimeoutError(), "timeout", 504),
            (FakeResponse(200, {"choices": []}), "payload", 502),
        ]

        for response, expected_code, expected_status in cases:
            with self.subTest(expected_code):
                with self.assertRaises(AIProviderError) as caught:
                    await complete_json(
                        provider="groq",
                        api_key="must-not-leak",
                        model=None,
                        messages=[{"role": "user", "content": "test"}],
                        http_session=FakeSession(response),
                    )
                self.assertEqual(caught.exception.code, expected_code)
                self.assertEqual(caught.exception.http_status, expected_status)
                self.assertNotIn("must-not-leak", caught.exception.user_message)

    async def test_stt_success_is_independent_from_text_provider(self) -> None:
        session = FakeSession(FakeResponse(200, {"text": "Создай задачу"}))

        text = await transcribe_audio(
            provider="groq",
            api_key="speech-key",
            audio_bytes=b"ogg-data",
            http_session=session,
        )

        self.assertEqual(text, "Создай задачу")
        self.assertEqual(session.calls[0][0], "https://api.groq.com/openai/v1/audio/transcriptions")


if __name__ == "__main__":
    unittest.main()
