# tests/test_bot_voice.py
# Проверяет, что Telegram-голос использует отдельный STT и передаёт текст в создание/редактирование.
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


os.environ.setdefault(
    "TELEGRAM_BOT_TOKEN",
    "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
)

from backend.ai import AISettingsError
from backend import bot as bot_module


class ScalarResult:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, user) -> None:
        self.execute = AsyncMock(return_value=ScalarResult(user))


class FakeSessionContext:
    def __init__(self, user) -> None:
        self.session = FakeSession(user)

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class TelegramVoiceTests(unittest.IsolatedAsyncioTestCase):
    def make_message(self):
        processing_message = SimpleNamespace(edit_text=AsyncMock())
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=42),
            voice=SimpleNamespace(file_id="voice-id"),
            answer=AsyncMock(return_value=processing_message),
        )
        return message, processing_message

    async def test_voice_creation_and_editing_use_transcribed_text(self) -> None:
        user = SimpleNamespace(stt_provider="groq", stt_api_key="speech-secret")

        for state_data, expected_task_id in (({}, None), ({"update_task_id": 77}, 77)):
            with self.subTest(update_task_id=expected_task_id):
                message, processing_message = self.make_message()
                state = SimpleNamespace(
                    get_data=AsyncMock(return_value=state_data),
                    clear=AsyncMock(),
                )

                async def download_file(_path, destination):
                    destination.write(b"voice-bytes")

                with (
                    patch.object(bot_module, "AsyncSessionLocal", return_value=FakeSessionContext(user)),
                    patch.object(bot_module.bot, "get_file", AsyncMock(return_value=SimpleNamespace(file_path="voice.ogg"))),
                    patch.object(bot_module.bot, "download_file", AsyncMock(side_effect=download_file)),
                    patch.object(bot_module, "transcribe_audio", AsyncMock(return_value="Создай задачу")) as transcribe,
                    patch.object(bot_module, "process_user_message", AsyncMock()) as process_message,
                ):
                    await bot_module.handle_voice(message, state)

                transcribe.assert_awaited_once_with(
                    provider="groq",
                    api_key="speech-secret",
                    audio_bytes=b"voice-bytes",
                )
                process_message.assert_awaited_once_with(
                    message,
                    "Создай задачу",
                    processing_msg=processing_message,
                    update_task_id=expected_task_id,
                    state=state,
                )

    async def test_missing_stt_settings_do_not_call_text_provider(self) -> None:
        user = SimpleNamespace(stt_provider="groq", stt_api_key=None)
        message, processing_message = self.make_message()
        state = SimpleNamespace(get_data=AsyncMock(return_value={}), clear=AsyncMock())

        async def download_file(_path, destination):
            destination.write(b"voice-bytes")

        with (
            patch.object(bot_module, "AsyncSessionLocal", return_value=FakeSessionContext(user)),
            patch.object(bot_module.bot, "get_file", AsyncMock(return_value=SimpleNamespace(file_path="voice.ogg"))),
            patch.object(bot_module.bot, "download_file", AsyncMock(side_effect=download_file)),
            patch.object(
                bot_module,
                "transcribe_audio",
                AsyncMock(side_effect=AISettingsError("Настройте Groq Whisper")),
            ),
            patch.object(bot_module, "process_user_message", AsyncMock()) as process_message,
        ):
            await bot_module.handle_voice(message, state)

        processing_message.edit_text.assert_awaited_with("Настройте Groq Whisper")
        process_message.assert_not_awaited()
        state.clear.assert_awaited()


if __name__ == "__main__":
    unittest.main()
