"""Authentication boundary.

Today this only protects internal admin. Consumer and restaurant identity should
implement AuthN/AuthZ protocols here later rather than inventing a parallel system.
"""

from __future__ import annotations

import hmac
import secrets
from typing import Protocol

from app.core.exceptions import UnauthorizedError


class Principal:
    def __init__(self, subject: str, roles: frozenset[str]) -> None:
        self.subject = subject
        self.roles = roles

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


class AuthN(Protocol):
    def authenticate_admin(self, presented_key: str | None) -> Principal: ...


class AdminKeyAuth:
    def __init__(self, expected_key: str) -> None:
        self._expected = expected_key.encode("utf-8")

    def authenticate_admin(self, presented_key: str | None) -> Principal:
        if not presented_key:
            raise UnauthorizedError("Admin authentication required")
        presented = presented_key.encode("utf-8")
        if not hmac.compare_digest(presented, self._expected):
            raise UnauthorizedError("Invalid admin credentials")
        return Principal(subject="admin", roles=frozenset({"admin"}))


def generate_admin_key() -> str:
    return secrets.token_urlsafe(32)
