# backend/security.py
# Создаёт и проверяет криптографические challenge-коды для чувствительных auth-сценариев.

import hashlib
import hmac
import secrets


TELEGRAM_LINK_NONCE_BYTES = 16
TELEGRAM_LINK_SIGNATURE_HEX_LENGTH = 32


def create_telegram_link_challenge(user_id: int, secret_key: str) -> str:
    """Создаёт непредсказуемый challenge, криптографически привязанный к web-пользователю."""
    nonce = secrets.token_urlsafe(TELEGRAM_LINK_NONCE_BYTES)
    signature = _telegram_link_signature(user_id, nonce, secret_key)
    return f"{nonce}.{signature}"


def telegram_link_challenge_belongs_to_user(
    challenge: str,
    user_id: int,
    secret_key: str,
) -> bool:
    """Проверяет формат и привязку challenge без раскрытия ожидаемой подписи."""
    try:
        nonce, provided_signature = challenge.rsplit(".", 1)
    except ValueError:
        return False

    if not nonce or len(provided_signature) != TELEGRAM_LINK_SIGNATURE_HEX_LENGTH:
        return False

    expected_signature = _telegram_link_signature(user_id, nonce, secret_key)
    return hmac.compare_digest(provided_signature, expected_signature)


def _telegram_link_signature(user_id: int, nonce: str, secret_key: str) -> str:
    payload = f"telegram-link:{user_id}:{nonce}".encode("utf-8")
    digest = hmac.new(secret_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return digest[:TELEGRAM_LINK_SIGNATURE_HEX_LENGTH]
