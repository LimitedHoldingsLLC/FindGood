import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("QUEUE_BACKEND", "memory")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://findgood:findgood@localhost:5432/findgood_test",
)

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings, reset_settings_cache


def postgres_available() -> bool:
    reset_settings_cache()
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 2},
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except (OperationalError, OSError, TimeoutError):
        return False
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def db_ready() -> bool:
    return postgres_available()


@pytest.fixture
def client(db_ready: bool) -> Generator[TestClient, None, None]:
    if not db_ready:
        pytest.skip("PostgreSQL is not available")
    from alembic import command
    from alembic.config import Config

    reset_settings_cache()
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
