"""Small geographic helpers used by matching and freshness — no HTTP, no FastAPI."""

import hashlib
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers. Used to decide if two pins are the same place."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    origin = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(origin))


def optional_haversine_km(
    lat1: Decimal | float | None,
    lon1: Decimal | float | None,
    lat2: Decimal | float | None,
    lon2: Decimal | float | None,
) -> float | None:
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    return haversine_km(float(lat1), float(lon1), float(lat2), float(lon2))


def address_hash(address_line1: str, city: str, region: str, postal_code: str) -> str:
    raw = "|".join(part.strip().casefold() for part in (address_line1, city, region, postal_code))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
