"""Consumer map use-case: viewport in, lightweight FindGood pins out.

Google never decides which restaurants appear. We read stored coordinates
and published deals, pick one offer per location, and cap the payload.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.api.schemas import MapListOut, MapOfferOut, MapPinOut
from app.core.config import Settings
from app.core.exceptions import ValidationFailed
from app.db.models import Deal, VenueLocation
from app.db.repositories.map_repository import MapRepository
from app.domain.map.bounds import InvalidBounds, ViewportBounds, parse_bounds
from app.domain.map.cache_key import encode, precision_for_zoom
from app.domain.map.labels import marker_label
from app.domain.map.ranking import pick_best_offer
from app.domain.schedules.engine import ScheduleWindow, evaluate_deal_availability
from app.domain.schedules.windows import deal_matches_time_filter
from app.domain.taxonomy.discovery import MapWhen, TimeBucket
from app.domain.taxonomy.verticals import resolve_consumer_vertical
from app.services.presenters import utcnow


class MapService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.locations = MapRepository(db)

    def list_pins(
        self,
        *,
        north: Decimal,
        south: Decimal,
        east: Decimal,
        west: Decimal,
        zoom: int = 12,
        q: str | None = None,
        offering_kind: str | None = None,
        deal_type: str | None = None,
        cuisine: str | None = None,
        price_level: int | None = None,
        when: str | None = None,
        weekday: int | None = None,
        vertical: str | None = None,
        now: datetime | None = None,
        record_demand: bool = True,
    ) -> MapListOut:
        try:
            bounds = parse_bounds(north=north, south=south, east=east, west=west)
        except InvalidBounds as exc:
            raise ValidationFailed(str(exc)) from exc
        zoom = min(max(zoom, 1), 21)
        instant = now or utcnow()
        weekday, bucket, active_now, weekend = _resolve_when(when, weekday, instant)
        cache_key = _cache_key(
            bounds,
            zoom,
            q=q,
            offering_kind=offering_kind,
            deal_type=deal_type,
            cuisine=cuisine,
            price_level=price_level,
            when=when,
            weekday=weekday,
            vertical=vertical,
        )
        cached = _cache_get(self.settings, cache_key)
        if cached is not None:
            return MapListOut.model_validate({**cached, "cache_hit": True})

        fetch_limit = min(self.settings.map_max_results * 3, 240)
        rows = self.locations.locations_in_bounds(
            bounds,
            offering_kind=offering_kind,
            deal_type=deal_type,
            cuisine=cuisine,
            price_level=price_level,
            q=q,
            weekday=None if weekend else weekday,
            vertical=resolve_consumer_vertical(vertical),
            limit=fetch_limit,
        )
        pins: list[MapPinOut] = []
        for location in rows:
            pin = self._pin_for_location(
                location,
                now=instant,
                bucket=bucket,
                weekday=weekday,
                weekend=weekend,
                active_now=active_now,
            )
            if pin is not None:
                pins.append(pin)
        pins.sort(key=lambda pin: pin.name)
        max_results = self.settings.map_max_results
        truncated = len(pins) > max_results
        zoom_required = truncated and bounds.too_wide_for_pins()
        items = pins[:max_results]
        payload = MapListOut(
            items=items,
            result_count=len(pins),
            truncated=truncated,
            zoom_required=zoom_required,
            cache_hit=False,
        )
        _cache_set(self.settings, cache_key, payload.model_dump(mode="json"))
        if record_demand and not self.settings.is_test:
            self.locations.increment_demand([pin.id for pin in items])
        return payload

    def _pin_for_location(
        self,
        location: VenueLocation,
        *,
        now: datetime,
        bucket: TimeBucket | None,
        weekday: int | None,
        weekend: bool,
        active_now: bool,
    ) -> MapPinOut | None:
        venue = location.venue
        deals: list[Deal] = []
        availabilities = {}
        for deal in location.deals:
            windows = _windows(deal)
            if weekend and not any(day in {6, 7} for window in windows for day in window.days_of_week):
                continue
            if weekday is not None and not weekend:
                if not any(weekday in window.days_of_week for window in windows):
                    continue
            if bucket and not deal_matches_time_filter(windows, when=bucket, weekday=weekday):
                continue
            availability = evaluate_deal_availability(windows, location.timezone, now)
            if active_now and availability.status.value != "active_now":
                continue
            deals.append(deal)
            availabilities[deal.id] = availability
        best = pick_best_offer(deals, availabilities)
        if best is None:
            return None
        try:
            lat = Decimal(str(location.latitude))
            lng = Decimal(str(location.longitude))
        except Exception:
            return None
        offer = best.deal
        return MapPinOut(
            id=location.id,
            venue_id=venue.id,
            slug=venue.slug,
            name=venue.name,
            lat=lat,
            lng=lng,
            neighborhood=location.neighborhood,
            category=venue.primary_category,
            location_confidence=location.location_confidence,
            best_offer=MapOfferOut(
                id=offer.id,
                label=marker_label(title=offer.title, deal_type=offer.deal_type, items=offer.items),
                title=offer.title,
                freshness=best.freshness,
                availability_status=best.availability.status.value,
                availability_label=best.availability.label,
                extra_offer_count=best.extra_offer_count,
            ),
        )


def _windows(deal: Deal) -> list[ScheduleWindow]:
    return [
        ScheduleWindow(
            days_of_week=frozenset(schedule.days_of_week),
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            ends_at_close=schedule.ends_at_close,
            valid_from=schedule.valid_from,
            valid_until=schedule.valid_until,
        )
        for schedule in deal.schedules
    ]


def _resolve_when(
    when: str | None,
    weekday: int | None,
    now: datetime,
) -> tuple[int | None, TimeBucket | None, bool, bool]:
    if when is None:
        return weekday, None, False, False
    try:
        bucket = MapWhen(when)
    except ValueError as exc:
        raise ValidationFailed("Unknown map time filter") from exc
    local = now.astimezone(ZoneInfo("America/Los_Angeles"))
    today = local.isoweekday()
    if bucket == MapWhen.NOW:
        return weekday, None, True, False
    if bucket == MapWhen.TONIGHT:
        return weekday or today, TimeBucket.EVENING, False, False
    if bucket == MapWhen.TODAY:
        return today, None, False, False
    if bucket == MapWhen.TOMORROW:
        return (today % 7) + 1, None, False, False
    if bucket == MapWhen.WEEKEND:
        return None, None, False, True
    return weekday, TimeBucket(bucket.value), False, False


def _cache_key(bounds: ViewportBounds, zoom: int, **filters: object) -> str:
    precision = precision_for_zoom(zoom)
    cell = encode(float((bounds.north + bounds.south) / 2), float((bounds.east + bounds.west) / 2), precision=precision)
    blob = json.dumps(filters, sort_keys=True, default=str)
    digest = hashlib.sha256(blob.encode()).hexdigest()[:12]
    return f"map:v1:{cell}:{zoom}:{digest}"


def _cache_get(settings: Settings, key: str) -> dict | None:
    if settings.queue_backend != "redis" or settings.is_test:
        return None
    try:
        import redis

        raw = redis.Redis.from_url(settings.redis_url).get(key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


def _cache_set(settings: Settings, key: str, payload: dict) -> None:
    if settings.queue_backend != "redis" or settings.is_test:
        return
    try:
        import redis

        redis.Redis.from_url(settings.redis_url).setex(key, settings.map_cache_ttl_seconds, json.dumps(payload))
    except Exception:
        return
