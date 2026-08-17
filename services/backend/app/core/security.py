"""Authentication boundary.

Today this only protects internal admin. Consumer and restaurant identity should
implement AuthN/AuthZ protocols here later rather than inventing a parallel system.

Admin operators sign in with username/password. The UI stores a signed session
token, not the password. Machine callers may still present ADMIN_API_KEY.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Protocol

from app.core.exceptions import RateLimitedError, UnauthorizedError

_TOKEN_VERSION = "v1"
_LOCKED_MESSAGE = "Too many login attempts. Try again later."


class Principal:
    def __init__(self, subject: str, roles: frozenset[str]) -> None:
        self.subject = subject
        self.roles = roles

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


class AuthN(Protocol):
    def authenticate_password(self, username: str | None, password: str | None) -> Principal: ...

    def authenticate_request(self, *, bearer_token: str | None, api_key: str | None) -> Principal: ...


class LoginAttemptGuard:
    """In-process lockout for password guessing. Same shape as the API rate limiter."""

    def __init__(
        self,
        *,
        max_failures: int = 5,
        window_seconds: int = 900,
        lockout_seconds: int = 900,
        global_max_failures: int = 25,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        self._max_failures = max_failures
        self._window = window_seconds
        self._lockout = lockout_seconds
        self._global_max = global_max_failures
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lockouts: dict[str, float] = {}
        self._global_failures: deque[float] = deque()
        self._global_lockout_until = 0.0
        self._lock = threading.Lock()

    def raise_if_locked(self, client_key: str, *, now: float | None = None) -> None:
        if not self._enabled:
            return
        ts = now if now is not None else time.time()
        with self._lock:
            if self._global_lockout_until > ts or self._lockouts.get(client_key, 0.0) > ts:
                raise RateLimitedError(_LOCKED_MESSAGE)

    def record_failure(self, client_key: str, *, now: float | None = None) -> None:
        if not self._enabled:
            return
        ts = now if now is not None else time.time()
        cutoff = ts - self._window
        with self._lock:
            bucket = self._failures[client_key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            bucket.append(ts)
            if len(bucket) >= self._max_failures:
                self._lockouts[client_key] = ts + self._lockout

            while self._global_failures and self._global_failures[0] < cutoff:
                self._global_failures.popleft()
            self._global_failures.append(ts)
            if len(self._global_failures) >= self._global_max:
                self._global_lockout_until = ts + self._lockout

    def record_success(self, client_key: str) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._failures.pop(client_key, None)
            self._lockouts.pop(client_key, None)


class AdminAuth:
    def __init__(
        self,
        *,
        username: str,
        password: str,
        signing_key: str,
        session_ttl_seconds: int = 43_200,
        attempt_guard: LoginAttemptGuard | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._api_key = signing_key
        self._signing_key = signing_key.encode("utf-8")
        self._ttl = session_ttl_seconds
        self._guard = attempt_guard

    def login(self, username: str | None, password: str | None, *, client_key: str) -> Principal:
        if self._guard:
            self._guard.raise_if_locked(client_key)
        try:
            principal = self.authenticate_password(username, password)
        except UnauthorizedError:
            if self._guard:
                self._guard.record_failure(client_key)
            raise
        if self._guard:
            self._guard.record_success(client_key)
        return principal

    def authenticate_password(self, username: str | None, password: str | None) -> Principal:
        user_ok = _compare(username or "", self._username)
        password_ok = _compare(password or "", self._password)
        if not (user_ok and password_ok):
            raise UnauthorizedError("Invalid admin credentials")
        return Principal(subject=self._username, roles=frozenset({"admin"}))

    def authenticate_api_key(self, presented_key: str | None) -> Principal:
        if not presented_key:
            raise UnauthorizedError("Admin authentication required")
        if not _compare(presented_key, self._api_key):
            raise UnauthorizedError("Invalid admin credentials")
        return Principal(subject=self._username, roles=frozenset({"admin"}))

    def issue_session(self, principal: Principal, *, now: datetime | None = None) -> tuple[str, datetime]:
        issued_at = now or datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=self._ttl)
        payload = json.dumps(
            {"sub": principal.subject, "exp": int(expires_at.timestamp())},
            separators=(",", ":"),
        ).encode("utf-8")
        payload_b64 = _b64encode(payload)
        token = f"{_TOKEN_VERSION}.{payload_b64}.{_b64encode(self._sign(payload_b64))}"
        return token, expires_at

    def authenticate_session(self, token: str | None) -> Principal:
        if not token:
            raise UnauthorizedError("Admin authentication required")
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != _TOKEN_VERSION:
            raise UnauthorizedError("Invalid admin credentials")
        payload_b64, signature_b64 = parts[1], parts[2]
        try:
            presented_sig = _b64decode(signature_b64)
        except (ValueError, OSError):
            raise UnauthorizedError("Invalid admin credentials") from None
        if not hmac.compare_digest(presented_sig, self._sign(payload_b64)):
            raise UnauthorizedError("Invalid admin credentials")
        try:
            payload = json.loads(_b64decode(payload_b64))
            subject = str(payload["sub"])
            exp = int(payload["exp"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            raise UnauthorizedError("Invalid admin credentials") from None
        if exp < int(time.time()):
            raise UnauthorizedError("Invalid admin credentials")
        return Principal(subject=subject, roles=frozenset({"admin"}))

    def authenticate_request(self, *, bearer_token: str | None, api_key: str | None) -> Principal:
        if bearer_token:
            return self.authenticate_session(bearer_token)
        return self.authenticate_api_key(api_key)

    def _sign(self, payload_b64: str) -> bytes:
        return hmac.new(self._signing_key, payload_b64.encode("ascii"), hashlib.sha256).digest()


def generate_admin_key() -> str:
    return secrets.token_urlsafe(32)


@lru_cache
def get_login_attempt_guard(
    max_failures: int,
    window_seconds: int,
    lockout_seconds: int,
    global_max_failures: int,
    enabled: bool,
) -> LoginAttemptGuard:
    return LoginAttemptGuard(
        max_failures=max_failures,
        window_seconds=window_seconds,
        lockout_seconds=lockout_seconds,
        global_max_failures=global_max_failures,
        enabled=enabled,
    )


def reset_login_attempt_guard() -> None:
    get_login_attempt_guard.cache_clear()


def _compare(presented: str, expected: str) -> bool:
    return hmac.compare_digest(_digest(presented), _digest(expected))


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
