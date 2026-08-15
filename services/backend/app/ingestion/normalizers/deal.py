from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse, urlunparse

from app.domain.deals.money import parse_money

DAY_ALIASES = {
    "mon": 1,
    "monday": 1,
    "tue": 2,
    "tues": 2,
    "tuesday": 2,
    "wed": 3,
    "wednesday": 3,
    "thu": 4,
    "thur": 4,
    "thurs": 4,
    "thursday": 4,
    "fri": 5,
    "friday": 5,
    "sat": 6,
    "saturday": 6,
    "sun": 7,
    "sunday": 7,
}

DEAL_TYPE_ALIASES = {
    "happy hour": "happy_hour",
    "happy_hour": "happy_hour",
    "food special": "food_special",
    "drink special": "drink_special",
    "prix fixe": "prix_fixe",
    "prix-fixe": "prix_fixe",
    "oyster": "oyster",
    "taco night": "taco_night",
    "taco tuesday": "taco_night",
    "brunch": "brunch",
    "lunch": "lunch",
    "late night": "late_night",
    "limited time": "limited_time",
}


def collapse_ws(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").casefold()
    path = parsed.path.rstrip("/") or ""
    return urlunparse((parsed.scheme or "https", host, path, "", "", ""))


def normalize_day(value: object) -> int:
    if isinstance(value, int):
        if value in range(1, 8):
            return value
        raise ValueError(f"Invalid weekday number: {value}")
    key = str(value).strip().casefold()
    if key not in DAY_ALIASES:
        raise ValueError(f"Unknown weekday: {value}")
    return DAY_ALIASES[key]


def normalize_time(value: object | None) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip().casefold()
    if text in {"close", "until close", "closing"}:
        return "close"
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not match:
        if re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", text):
            return text[:5]
        raise ValueError(f"Unparseable time: {value}")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)
    if meridiem:
        if hour == 12:
            hour = 0 if meridiem == "am" else 12
        elif meridiem == "pm":
            hour += 12
    if hour == 24:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Impossible time: {value}")
    return f"{hour:02d}:{minute:02d}"


def normalize_deal_type(value: str | None) -> str:
    if not value:
        return "other"
    key = value.strip().casefold()
    return DEAL_TYPE_ALIASES.get(key, key.replace(" ", "_"))


class DealNormalizer:
    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        venue = payload.get("venue") or {}
        items = []
        for item in payload.get("items") or []:
            normal = item.get("normal_price")
            deal = item.get("deal_price")
            items.append(
                {
                    "name": collapse_ws(item.get("name")) or "Untitled item",
                    "description": collapse_ws(item.get("description")),
                    "category": collapse_ws(item.get("category")),
                    "normal_price": str(parse_money(normal)) if normal not in (None, "") else None,
                    "deal_price": str(parse_money(deal)) if deal not in (None, "") else None,
                    "currency": (item.get("currency") or "USD").upper(),
                }
            )
        schedules = []
        for raw in payload.get("schedules") or []:
            days = [normalize_day(day) for day in raw.get("days") or raw.get("days_of_week") or []]
            start = normalize_time(raw.get("start") or raw.get("start_time"))
            end = normalize_time(raw.get("end") or raw.get("end_time"))
            ends_at_close = bool(raw.get("ends_at_close")) or end == "close"
            if end == "close":
                end = None
            schedules.append(
                {
                    "days_of_week": days,
                    "start_time": start,
                    "end_time": end,
                    "ends_at_close": ends_at_close,
                    "valid_from": raw.get("valid_from"),
                    "valid_until": raw.get("valid_until"),
                }
            )
        offering = (payload.get("offering_kind") or "both").strip().casefold()
        if offering not in {"food", "drink", "both"}:
            offering = "both"
        return {
            "venue": {
                "name": collapse_ws(venue.get("name")),
                "website_url": normalize_url(venue.get("website") or venue.get("website_url")),
                "phone": collapse_ws(venue.get("phone")),
            },
            "title": collapse_ws(payload.get("title")) or "Untitled deal",
            "description": collapse_ws(payload.get("description")),
            "deal_type": normalize_deal_type(payload.get("deal_type")),
            "offering_kind": offering,
            "schedules": schedules,
            "items": items,
            "venue_location_hint": collapse_ws(payload.get("venue_location_hint")),
        }
