class AppError(Exception):
    status_code = 400
    code = "app_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_failed"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"


class ProviderError(AppError):
    """A data provider (Google, Yelp, OpenTable, crawler) failed in a way the API can explain."""

    status_code = 502
    code = "provider_error"


class ProviderNotConfigured(ProviderError):
    status_code = 409
    code = "provider_not_configured"


class ProviderAuthenticationError(ProviderError):
    status_code = 502
    code = "provider_authentication_error"


class ProviderRateLimited(ProviderError):
    status_code = 429
    code = "provider_rate_limited"


class CrawlerFetchError(ProviderError):
    status_code = 502
    code = "crawler_fetch_error"


class CrawlerBlockedByRobots(ProviderError):
    status_code = 409
    code = "crawler_blocked_by_robots"


class NormalizationError(AppError):
    status_code = 422
    code = "normalization_error"


class EntityResolutionError(AppError):
    status_code = 409
    code = "entity_resolution_error"
