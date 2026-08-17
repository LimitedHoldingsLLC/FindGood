from datetime import UTC, datetime, timedelta

import pytest
from app.core.exceptions import RateLimitedError, UnauthorizedError
from app.core.security import AdminAuth, LoginAttemptGuard, Principal


def _auth() -> AdminAuth:
    return AdminAuth(
        username="admin",
        password="correct-horse",
        signing_key="test-admin-key",
        session_ttl_seconds=3_600,
    )


def test_password_login_succeeds() -> None:
    principal = _auth().authenticate_password("admin", "correct-horse")
    assert principal.subject == "admin"
    assert principal.is_admin


def test_password_login_rejects_wrong_password() -> None:
    with pytest.raises(UnauthorizedError):
        _auth().authenticate_password("admin", "wrong")


def test_password_login_rejects_wrong_username() -> None:
    with pytest.raises(UnauthorizedError):
        _auth().authenticate_password("not-admin", "correct-horse")


def test_password_login_does_not_leak_which_field_failed() -> None:
    with pytest.raises(UnauthorizedError, match="Invalid admin credentials"):
        _auth().authenticate_password("nope", "nope")


def test_session_token_round_trip() -> None:
    auth = _auth()
    principal = Principal(subject="admin", roles=frozenset({"admin"}))
    token, expires_at = auth.issue_session(principal)
    restored = auth.authenticate_session(token)
    assert restored.subject == "admin"
    assert restored.is_admin
    assert expires_at > datetime.now(UTC)


def test_session_token_rejects_tampering() -> None:
    auth = _auth()
    token, _ = auth.issue_session(Principal(subject="admin", roles=frozenset({"admin"})))
    version, payload, signature = token.split(".")
    tampered = f"{version}.{payload[:-1]}x.{signature}"
    with pytest.raises(UnauthorizedError):
        auth.authenticate_session(tampered)


def test_expired_session_token_is_rejected() -> None:
    auth = _auth()
    past = datetime.now(UTC) - timedelta(hours=2)
    token, _ = auth.issue_session(Principal(subject="admin", roles=frozenset({"admin"})), now=past)
    with pytest.raises(UnauthorizedError):
        auth.authenticate_session(token)


def test_request_accepts_bearer_token() -> None:
    auth = _auth()
    token, _ = auth.issue_session(Principal(subject="admin", roles=frozenset({"admin"})))
    principal = auth.authenticate_request(bearer_token=token, api_key=None)
    assert principal.is_admin


def test_request_accepts_api_key_for_machine_access() -> None:
    principal = _auth().authenticate_request(bearer_token=None, api_key="test-admin-key")
    assert principal.is_admin


def test_request_rejects_missing_credentials() -> None:
    with pytest.raises(UnauthorizedError):
        _auth().authenticate_request(bearer_token=None, api_key=None)


def _guarded_auth() -> AdminAuth:
    return AdminAuth(
        username="admin",
        password="correct-horse",
        signing_key="test-admin-key",
        attempt_guard=LoginAttemptGuard(
            max_failures=3,
            window_seconds=900,
            lockout_seconds=900,
            global_max_failures=10,
        ),
    )


def test_login_lockout_after_repeated_failures() -> None:
    auth = _guarded_auth()
    for _ in range(3):
        with pytest.raises(UnauthorizedError):
            auth.login("admin", "wrong", client_key="1.1.1.1")
    with pytest.raises(RateLimitedError, match="Too many login attempts"):
        auth.login("admin", "wrong", client_key="1.1.1.1")
    with pytest.raises(RateLimitedError):
        auth.login("admin", "correct-horse", client_key="1.1.1.1")


def test_login_lockout_is_per_client() -> None:
    auth = _guarded_auth()
    for _ in range(3):
        with pytest.raises(UnauthorizedError):
            auth.login("admin", "wrong", client_key="1.1.1.1")
    principal = auth.login("admin", "correct-horse", client_key="2.2.2.2")
    assert principal.is_admin


def test_successful_login_clears_failures_for_that_client() -> None:
    auth = _guarded_auth()
    with pytest.raises(UnauthorizedError):
        auth.login("admin", "wrong", client_key="9.9.9.9")
    auth.login("admin", "correct-horse", client_key="9.9.9.9")
    with pytest.raises(UnauthorizedError):
        auth.login("admin", "wrong", client_key="9.9.9.9")


def test_global_lockout_stops_distributed_guessing() -> None:
    auth = AdminAuth(
        username="admin",
        password="correct-horse",
        signing_key="test-admin-key",
        attempt_guard=LoginAttemptGuard(
            max_failures=50,
            window_seconds=900,
            lockout_seconds=900,
            global_max_failures=4,
        ),
    )
    for index in range(4):
        with pytest.raises(UnauthorizedError):
            auth.login("admin", "wrong", client_key=f"10.0.0.{index}")
    with pytest.raises(RateLimitedError):
        auth.login("admin", "correct-horse", client_key="10.0.0.99")
