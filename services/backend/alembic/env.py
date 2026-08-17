from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def _require_psycopg() -> None:
    """Fail with a venv hint instead of a raw ModuleNotFoundError.

    `alembic` on PATH is often a global install that does not have project deps.
    """
    try:
        import psycopg  # noqa: F401
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "psycopg is not installed in this Python, so Alembic cannot talk to Postgres.\n"
            "Use the project virtualenv (do not run the global alembic.exe):\n"
            "  cd services\\backend\n"
            "  .venv\\Scripts\\activate\n"
            "  pip install -e \".[dev]\"\n"
            "  python -m alembic upgrade head\n"
        ) from exc


def run_migrations_offline() -> None:
    _require_psycopg()
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    _require_psycopg()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
