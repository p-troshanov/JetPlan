# tests/test_security.py
# Проверяет криптографическую стойкость и user binding Telegram link challenge.

import unittest

from pydantic import ValidationError

from backend.schemas import TelegramVerifyCodeRequest
from backend.security import (
    create_telegram_link_challenge,
    telegram_link_challenge_belongs_to_user,
)


class TelegramLinkChallengeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret_key = "unit-test-secret-key"

    def test_challenge_is_bound_to_requesting_user(self) -> None:
        challenge = create_telegram_link_challenge(17, self.secret_key)

        self.assertTrue(
            telegram_link_challenge_belongs_to_user(challenge, 17, self.secret_key)
        )
        self.assertFalse(
            telegram_link_challenge_belongs_to_user(challenge, 18, self.secret_key)
        )

    def test_tampered_challenge_is_rejected(self) -> None:
        challenge = create_telegram_link_challenge(17, self.secret_key)
        nonce, signature = challenge.rsplit(".", 1)
        replacement = "0" if signature[-1] != "0" else "1"
        tampered = f"{nonce}.{signature[:-1]}{replacement}"

        self.assertFalse(
            telegram_link_challenge_belongs_to_user(tampered, 17, self.secret_key)
        )

    def test_challenge_has_high_entropy_and_rejects_legacy_code(self) -> None:
        first = create_telegram_link_challenge(17, self.secret_key)
        second = create_telegram_link_challenge(17, self.secret_key)

        self.assertNotEqual(first, second)
        self.assertGreaterEqual(len(first), 50)
        self.assertFalse(
            telegram_link_challenge_belongs_to_user("1234", 17, self.secret_key)
        )

    def test_request_contract_rejects_legacy_four_digit_code(self) -> None:
        with self.assertRaises(ValidationError):
            TelegramVerifyCodeRequest(code="1234")


if __name__ == "__main__":
    unittest.main()
