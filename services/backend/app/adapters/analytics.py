from typing import Any, Protocol

from app.core.logging import get_logger

logger = get_logger("analytics")


class AnalyticsAdapter(Protocol):
    def track(self, event: str, properties: dict[str, Any] | None = None) -> None: ...


class LoggingAnalyticsAdapter:
    def track(self, event: str, properties: dict[str, Any] | None = None) -> None:
        logger.info("analytics_event", analytics_name=event, properties=properties or {})
