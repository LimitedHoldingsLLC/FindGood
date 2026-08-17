"""Retry helpers for crawler fetches.

The HTTP client already retries transient failures. This module exists so jobs
can decide whether a given error is worth another attempt at the job layer.
"""

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def is_retryable_status(status: int) -> bool:
    return status in RETRYABLE_STATUS


def is_permanent_status(status: int) -> bool:
    return 400 <= status < 500 and status != 429
