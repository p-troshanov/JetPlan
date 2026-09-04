# tests/test_ai_profile.py
# Проверяет сохранение AI-настроек и отсутствие credentials в ответе профиля.
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException


os.environ.setdefault(
    "TELEGRAM_BOT_TOKEN",
    "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
)

from backend.auth import update_me
from backend.schemas import UserProfileUpdate


def make_user():
    return SimpleNamespace(
        id=7,
        username="tester",
        first_name="Test",
        last_name=None,
        ai_provider="groq",
        ai_api_key="old-text-secret",
        ai_model=None,
        stt_provider="groq",
        stt_api_key="old-speech-secret",
        task_hotkey="ctrl+q",
        auto_postpone_overdue=False,
        telegram_id=42,
    )


def make_db():
    return SimpleNamespace(add=MagicMock(), commit=AsyncMock(), refresh=AsyncMock())


class AIProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_openrouter_model_and_key_are_saved_but_secret_is_not_returned(self) -> None:
        user = make_user()
        db = make_db()

        response = await update_me(
            UserProfileUpdate(
                ai_provider="openrouter",
                ai_model="anthropic/claude-sonnet-4.5",
                ai_api_key="new-openrouter-secret",
            ),
            db,
            user,
        )

        self.assertEqual(user.ai_provider, "openrouter")
        self.assertEqual(user.ai_model, "anthropic/claude-sonnet-4.5")
        self.assertEqual(user.ai_api_key, "new-openrouter-secret")
        self.assertTrue(response["ai_api_key_configured"])
        self.assertTrue(response["stt_api_key_configured"])
        self.assertNotIn("ai_api_key", response)
        self.assertNotIn("stt_api_key", response)

    async def test_partial_profile_update_preserves_model_and_keys(self) -> None:
        user = make_user()
        user.ai_provider = "openrouter"
        user.ai_model = "openai/gpt-oss-20b"
        db = make_db()

        await update_me(UserProfileUpdate(first_name="Новое имя"), db, user)

        self.assertEqual(user.ai_model, "openai/gpt-oss-20b")
        self.assertEqual(user.ai_api_key, "old-text-secret")
        self.assertEqual(user.stt_api_key, "old-speech-secret")

    async def test_openrouter_without_model_is_rejected(self) -> None:
        user = make_user()
        db = make_db()

        with self.assertRaises(HTTPException) as caught:
            await update_me(UserProfileUpdate(ai_provider="openrouter"), db, user)

        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("ID модели", caught.exception.detail)


if __name__ == "__main__":
    unittest.main()
