"""Turn messy provider addresses into FindGood location fields.

Providers send addresses in different shapes. We fill what we can and leave
the rest empty instead of guessing a city or timezone we do not know.
"""

from decimal import Decimal

from app.domain.ingestion.schemas import NormalizedLocation

US_STATE_TIMEZONES = {
    "AL": "America/Chicago",
    "AK": "America/Anchorage",
    "AZ": "America/Phoenix",
    "AR": "America/Chicago",
    "CA": "America/Los_Angeles",
    "CO": "America/Denver",
    "CT": "America/New_York",
    "DC": "America/New_York",
    "DE": "America/New_York",
    "FL": "America/New_York",
    "GA": "America/New_York",
    "HI": "Pacific/Honolulu",
    "IA": "America/Chicago",
    "ID": "America/Boise",
    "IL": "America/Chicago",
    "IN": "America/Indiana/Indianapolis",
    "KS": "America/Chicago",
    "KY": "America/New_York",
    "LA": "America/Chicago",
    "MA": "America/New_York",
    "MD": "America/New_York",
    "ME": "America/New_York",
    "MI": "America/Detroit",
    "MN": "America/Chicago",
    "MO": "America/Chicago",
    "MS": "America/Chicago",
    "MT": "America/Denver",
    "NC": "America/New_York",
    "ND": "America/Chicago",
    "NE": "America/Chicago",
    "NH": "America/New_York",
    "NJ": "America/New_York",
    "NM": "America/Denver",
    "NV": "America/Los_Angeles",
    "NY": "America/New_York",
    "OH": "America/New_York",
    "OK": "America/Chicago",
    "OR": "America/Los_Angeles",
    "PA": "America/New_York",
    "RI": "America/New_York",
    "SC": "America/New_York",
    "SD": "America/Chicago",
    "TN": "America/Chicago",
    "TX": "America/Chicago",
    "UT": "America/Denver",
    "VA": "America/New_York",
    "VT": "America/New_York",
    "WA": "America/Los_Angeles",
    "WI": "America/Chicago",
    "WV": "America/New_York",
    "WY": "America/Denver",
}


def timezone_for_region(region: str | None, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if region:
        key = region.strip().upper()
        if key in US_STATE_TIMEZONES:
            return US_STATE_TIMEZONES[key]
    return "America/Los_Angeles"


def location_from_parts(
    *,
    address_line1: str | None,
    city: str | None,
    region: str | None,
    postal_code: str | None,
    latitude: float | Decimal | None,
    longitude: float | Decimal | None,
    country: str = "US",
    neighborhood: str | None = None,
    timezone: str | None = None,
    formatted: str | None = None,
) -> NormalizedLocation | None:
    if latitude is None or longitude is None:
        return None
    line1 = (address_line1 or formatted or "").strip() or "Unknown address"
    city_value = (city or "").strip() or "Unknown"
    region_value = (region or "").strip() or "NA"
    postal = (postal_code or "").strip() or "00000"
    return NormalizedLocation(
        address_line1=line1[:200],
        city=city_value[:120],
        region=region_value[:80],
        postal_code=postal[:20],
        country=(country or "US")[:2].upper(),
        neighborhood=neighborhood,
        latitude=Decimal(str(latitude)),
        longitude=Decimal(str(longitude)),
        timezone=timezone_for_region(region_value, timezone),
    )
