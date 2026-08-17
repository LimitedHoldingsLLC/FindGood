"""Vertical and category taxonomy. No FastAPI or persistence imports."""

from app.domain.taxonomy.verticals import (
    CONSUMER_DEFAULT_VERTICAL,
    Vertical,
    resolve_consumer_vertical,
)

__all__ = ["CONSUMER_DEFAULT_VERTICAL", "Vertical", "resolve_consumer_vertical"]
