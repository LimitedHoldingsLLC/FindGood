import logging
import sys
import uuid
from contextvars import ContextVar

import structlog

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
crawl_run_id_ctx: ContextVar[str | None] = ContextVar("crawl_run_id", default=None)


def new_request_id() -> str:
    return str(uuid.uuid4())


def bind_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)


def add_contextvars(_logger: object, _method: str, event_dict: dict) -> dict:
    request_id = request_id_ctx.get()
    crawl_run_id = crawl_run_id_ctx.get()
    if request_id:
        event_dict["request_id"] = request_id
    if crawl_run_id:
        event_dict["crawl_run_id"] = crawl_run_id
    return event_dict


def configure_logging(log_format: str, log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        add_contextvars,  # type: ignore[list-item]
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
