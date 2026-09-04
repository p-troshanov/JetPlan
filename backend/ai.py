# backend/ai.py
# Предоставляет единый безопасный контур текстовых AI-провайдеров и распознавания речи.
import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import aiohttp


logger = logging.getLogger(__name__)

GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
GROQ_STT_MODEL = "whisper-large-v3"
SUPPORTED_AI_PROVIDERS = frozenset({"groq", "openrouter"})
SUPPORTED_STT_PROVIDERS = frozenset({"groq"})
OPENROUTER_MODEL_PATTERN = re.compile(
    r"^~?[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._:+-]*$"
)


@dataclass(frozen=True)
class AIProviderConfig:
    endpoint: str
    default_model: str | None = None
    extra_headers: Mapping[str, str] | None = None


AI_PROVIDER_CONFIGS = {
    "groq": AIProviderConfig(
        endpoint="https://api.groq.com/openai/v1/chat/completions",
        default_model=GROQ_DEFAULT_MODEL,
    ),
    "openrouter": AIProviderConfig(
        endpoint="https://openrouter.ai/api/v1/chat/completions",
        extra_headers={
            "HTTP-Referer": "https://jetplan.site",
            "X-OpenRouter-Title": "JetPlan",
        },
    ),
}


class AISettingsError(ValueError):
    """Ошибка локальной конфигурации AI без обращения к внешнему провайдеру."""


class AIProviderError(RuntimeError):
    """Нормализованная ошибка внешнего AI/STT-провайдера без секретных данных."""

    def __init__(
        self,
        *,
        provider: str,
        code: str,
        user_message: str,
        http_status: int,
        provider_status: int | None = None,
        request_id: str | None = None,
        provider_error_code: str | None = None,
    ) -> None:
        super().__init__(f"{provider}:{code}")
        self.provider = provider
        self.code = code
        self.user_message = user_message
        self.http_status = http_status
        self.provider_status = provider_status
        self.request_id = request_id
        self.provider_error_code = provider_error_code


def validate_ai_selection(provider: str | None, model: str | None) -> tuple[str, str | None]:
    normalized_provider = (provider or "").strip().lower()
    normalized_model = (model or "").strip() or None

    if normalized_provider not in SUPPORTED_AI_PROVIDERS:
        raise AISettingsError("Поддерживаются только Groq и OpenRouter.")

    if normalized_provider == "openrouter":
        if not normalized_model:
            raise AISettingsError("Для OpenRouter укажите ID модели.")
        if len(normalized_model) > 160 or not OPENROUTER_MODEL_PATTERN.fullmatch(normalized_model):
            raise AISettingsError("ID модели OpenRouter должен иметь формат provider/model.")
        return normalized_provider, normalized_model

    return normalized_provider, None


def validate_stt_selection(provider: str | None) -> str:
    normalized_provider = (provider or "").strip().lower()
    if normalized_provider not in SUPPORTED_STT_PROVIDERS:
        raise AISettingsError("Для распознавания речи сейчас поддерживается только Groq Whisper.")
    return normalized_provider


def resolve_ai_model(provider: str, model: str | None) -> str:
    normalized_provider, normalized_model = validate_ai_selection(provider, model)
    return normalized_model or AI_PROVIDER_CONFIGS[normalized_provider].default_model or ""


def log_provider_error(error: AIProviderError, operation: str, model: str | None = None) -> None:
    logger.warning(
        "AI provider request failed provider=%s operation=%s code=%s status=%s "
        "provider_error_code=%s request_id=%s model=%s",
        error.provider,
        operation,
        error.code,
        error.provider_status,
        error.provider_error_code,
        error.request_id,
        model,
    )


def _request_id(headers: Mapping[str, str]) -> str | None:
    return (
        headers.get("x-request-id")
        or headers.get("request-id")
        or headers.get("x-groq-request-id")
    )


def _provider_error_code(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    value = error.get("code") or error.get("type")
    return str(value)[:80] if value else None


def _provider_error_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or "")[:500]
    return ""


def _http_error(
    provider: str,
    status: int,
    payload: Any,
    headers: Mapping[str, str],
) -> AIProviderError:
    display_name = "OpenRouter" if provider == "openrouter" else "Groq"
    provider_message = _provider_error_message(payload).lower()
    common = {
        "provider": provider,
        "provider_status": status,
        "request_id": _request_id(headers),
        "provider_error_code": _provider_error_code(payload),
    }

    if status in (401, 403):
        return AIProviderError(
            **common,
            code="authentication",
            user_message=f"API-ключ {display_name} недействителен или не имеет доступа.",
            http_status=400,
        )
    if status == 429:
        return AIProviderError(
            **common,
            code="rate_limit",
            user_message=f"{display_name} временно отклонил запрос из-за лимита. Повторите позже.",
            http_status=429,
        )
    if status == 404 and "model" not in provider_message:
        return AIProviderError(
            **common,
            code="endpoint",
            user_message=f"Endpoint {display_name} недоступен. Сообщите администратору JetPlan.",
            http_status=502,
        )
    if status == 404 or (status == 400 and "model" in provider_message):
        return AIProviderError(
            **common,
            code="model",
            user_message=f"Выбранная модель {display_name} не найдена или недоступна для этого ключа.",
            http_status=400,
        )
    if status == 400:
        return AIProviderError(
            **common,
            code="request",
            user_message=f"{display_name} отклонил параметры запроса. Проверьте модель и настройки.",
            http_status=400,
        )
    if status >= 500:
        return AIProviderError(
            **common,
            code="provider_unavailable",
            user_message=f"{display_name} временно недоступен. Повторите позже.",
            http_status=502,
        )
    return AIProviderError(
        **common,
        code="provider_rejected",
        user_message=f"{display_name} отклонил запрос. Проверьте настройки AI.",
        http_status=502,
    )


async def _response_payload(response: aiohttp.ClientResponse) -> Any:
    try:
        return await response.json(content_type=None)
    except (aiohttp.ContentTypeError, json.JSONDecodeError, ValueError):
        return None


def _completion_content(payload: Any) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("missing completion content") from exc

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        return "".join(text_parts)
    raise ValueError("unsupported completion content")


def _parse_json_content(content: str) -> dict[str, Any]:
    value = content.strip()
    if value.startswith("```") and value.endswith("```"):
        first_line_end = value.find("\n")
        value = value[first_line_end + 1:-3].strip() if first_line_end >= 0 else value[3:-3].strip()
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("completion JSON is not an object")
    return parsed


async def complete_json(
    *,
    provider: str,
    api_key: str | None,
    model: str | None,
    messages: Iterable[Mapping[str, str]],
    http_session: aiohttp.ClientSession | None = None,
) -> dict[str, Any]:
    normalized_provider, normalized_model = validate_ai_selection(provider, model)
    if not api_key or not api_key.strip():
        raise AISettingsError("Укажите API-ключ выбранного AI-провайдера в настройках.")

    config = AI_PROVIDER_CONFIGS[normalized_provider]
    resolved_model = normalized_model or config.default_model or ""
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        **(config.extra_headers or {}),
    }
    payload: dict[str, Any] = {
        "model": resolved_model,
        "messages": list(messages),
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }
    if normalized_provider == "openrouter":
        payload["provider"] = {"require_parameters": True}

    owns_session = http_session is None
    session = http_session or aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45))
    try:
        async with session.post(config.endpoint, headers=headers, json=payload) as response:
            response_payload = await _response_payload(response)
            if response.status != 200:
                raise _http_error(normalized_provider, response.status, response_payload, response.headers)
    except asyncio.TimeoutError as exc:
        raise AIProviderError(
            provider=normalized_provider,
            code="timeout",
            user_message="AI-провайдер не ответил вовремя. Повторите запрос.",
            http_status=504,
        ) from exc
    except aiohttp.ClientError as exc:
        raise AIProviderError(
            provider=normalized_provider,
            code="network",
            user_message="Не удалось подключиться к AI-провайдеру. Повторите позже.",
            http_status=502,
        ) from exc
    finally:
        if owns_session:
            await session.close()

    try:
        return _parse_json_content(_completion_content(response_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise AIProviderError(
            provider=normalized_provider,
            code="payload",
            user_message="AI-провайдер вернул ответ в неожиданном формате. Повторите запрос.",
            http_status=502,
        ) from exc


async def transcribe_audio(
    *,
    provider: str,
    api_key: str | None,
    audio_bytes: bytes,
    filename: str = "voice.ogg",
    content_type: str = "audio/ogg",
    http_session: aiohttp.ClientSession | None = None,
) -> str:
    normalized_provider = validate_stt_selection(provider)
    if not api_key or not api_key.strip():
        raise AISettingsError(
            "Для голосового ввода укажите отдельный API-ключ Groq Whisper в настройках."
        )

    endpoint = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    form = aiohttp.FormData()
    form.add_field("file", audio_bytes, filename=filename, content_type=content_type)
    form.add_field("model", GROQ_STT_MODEL)
    form.add_field("response_format", "json")

    owns_session = http_session is None
    session = http_session or aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
    try:
        async with session.post(endpoint, headers=headers, data=form) as response:
            response_payload = await _response_payload(response)
            if response.status != 200:
                raise _http_error(normalized_provider, response.status, response_payload, response.headers)
    except asyncio.TimeoutError as exc:
        raise AIProviderError(
            provider=normalized_provider,
            code="timeout",
            user_message="Распознавание речи не ответило вовремя. Повторите сообщение.",
            http_status=504,
        ) from exc
    except aiohttp.ClientError as exc:
        raise AIProviderError(
            provider=normalized_provider,
            code="network",
            user_message="Не удалось подключиться к сервису распознавания речи.",
            http_status=502,
        ) from exc
    finally:
        if owns_session:
            await session.close()

    text = response_payload.get("text") if isinstance(response_payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise AIProviderError(
            provider=normalized_provider,
            code="payload",
            user_message="Сервис распознавания речи вернул пустой или некорректный ответ.",
            http_status=502,
        )
    return text.strip()
