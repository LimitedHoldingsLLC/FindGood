from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

# ISO-8601 weekdays: Monday=1 ... Sunday=7. Matches datetime.isoweekday().
ISO_WEEKDAYS = frozenset(range(1, 8))
STARTS_SOON_MINUTES = 60


class AvailabilityStatus(StrEnum):
    ACTIVE_NOW = "active_now"
    STARTS_SOON = "starts_soon"
    ACTIVE_LATER_TODAY = "active_later_today"
    ENDED_TODAY = "ended_today"
    CURRENTLY_UNAVAILABLE = "currently_unavailable"


@dataclass(frozen=True)
class ScheduleWindow:
    days_of_week: frozenset[int]
    start_time: time | None
    end_time: time | None
    ends_at_close: bool = False
    valid_from: date | None = None
    valid_until: date | None = None

    def __post_init__(self) -> None:
        invalid = set(self.days_of_week) - ISO_WEEKDAYS
        if invalid:
            raise ValueError(f"Invalid ISO weekdays: {sorted(invalid)}")
        if not self.days_of_week:
            raise ValueError("Schedule must include at least one weekday")


@dataclass(frozen=True)
class DealAvailability:
    status: AvailabilityStatus
    timezone: str
    local_time: datetime
    ends_at: datetime | None
    next_occurrence: datetime | None
    label: str


def evaluate_deal_availability(
    schedules: list[ScheduleWindow],
    timezone_name: str,
    at: datetime,
    *,
    starts_soon_minutes: int = STARTS_SOON_MINUTES,
) -> DealAvailability:
    """Evaluate recurring schedules in the venue location timezone.

    `at` may be timezone-aware in any zone, or naive (treated as UTC).
    """
    tz = ZoneInfo(timezone_name)
    instant = _as_aware_utc(at).astimezone(tz)
    local_date = instant.date()
    local_time = instant.timetz().replace(tzinfo=None)

    applicable = [window for window in schedules if _date_in_range(window, local_date)]
    active = _find_active(applicable, instant, local_time)
    if active is not None:
        ends_at = _end_datetime(active, instant)
        return DealAvailability(
            status=AvailabilityStatus.ACTIVE_NOW,
            timezone=timezone_name,
            local_time=instant,
            ends_at=ends_at,
            next_occurrence=instant,
            label=_active_label(ends_at, active),
        )

    upcoming_today = _next_start_on_date(applicable, instant, local_date, after=instant)
    if upcoming_today is not None:
        delta = upcoming_today - instant
        if timedelta(0) < delta <= timedelta(minutes=starts_soon_minutes):
            status = AvailabilityStatus.STARTS_SOON
            label = f"Starts soon at {_format_time(upcoming_today)}"
        else:
            status = AvailabilityStatus.ACTIVE_LATER_TODAY
            label = f"Starts at {_format_time(upcoming_today)}"
        return DealAvailability(
            status=status,
            timezone=timezone_name,
            local_time=instant,
            ends_at=None,
            next_occurrence=upcoming_today,
            label=label,
        )

    if _had_window_earlier_today(applicable, instant):
        next_occurrence = _next_start_after(applicable, instant)
        return DealAvailability(
            status=AvailabilityStatus.ENDED_TODAY,
            timezone=timezone_name,
            local_time=instant,
            ends_at=None,
            next_occurrence=next_occurrence,
            label="Ended earlier today",
        )

    next_occurrence = _next_start_after(applicable, instant)
    if next_occurrence is None:
        label = "Currently unavailable"
    else:
        label = f"Next {_format_next(next_occurrence)}"
    return DealAvailability(
        status=AvailabilityStatus.CURRENTLY_UNAVAILABLE,
        timezone=timezone_name,
        local_time=instant,
        ends_at=None,
        next_occurrence=next_occurrence,
        label=label,
    )


def _as_aware_utc(at: datetime) -> datetime:
    if at.tzinfo is None:
        return at.replace(tzinfo=ZoneInfo("UTC"))
    return at


def _date_in_range(window: ScheduleWindow, on: date) -> bool:
    if window.valid_from and on < window.valid_from:
        return False
    if window.valid_until and on > window.valid_until:
        return False
    return True


def _is_overnight(window: ScheduleWindow) -> bool:
    return window.start_time is not None and window.end_time is not None and window.end_time <= window.start_time


def _window_contains(window: ScheduleWindow, weekday: int, t: time) -> bool:
    if weekday in window.days_of_week:
        if window.start_time is None and window.end_time is None:
            return True
        if window.ends_at_close and window.end_time is None:
            return window.start_time is None or t >= window.start_time
        if _is_overnight(window):
            assert window.start_time is not None
            return t >= window.start_time
        if window.start_time and t < window.start_time:
            return False
        if window.end_time and t >= window.end_time:
            return False
        return True
    if (
        _is_overnight(window)
        and window.end_time is not None
        and t < window.end_time
        and _previous_weekday(weekday) in window.days_of_week
    ):
        return True
    return False


def _find_active(windows: list[ScheduleWindow], instant: datetime, local_time: time) -> ScheduleWindow | None:
    weekday = instant.isoweekday()
    for window in windows:
        if _window_contains(window, weekday, local_time):
            return window
    return None


def _end_datetime(window: ScheduleWindow, instant: datetime) -> datetime | None:
    if window.ends_at_close and window.end_time is None:
        return None
    if window.end_time is None:
        end_of_day = datetime.combine(instant.date(), time(23, 59, 59), tzinfo=instant.tzinfo)
        return end_of_day
    end = datetime.combine(instant.date(), window.end_time, tzinfo=instant.tzinfo)
    if _is_overnight(window) and instant.timetz().replace(tzinfo=None) >= (window.start_time or time.min):
        end = end + timedelta(days=1)
    if _is_overnight(window) and instant.time() < window.end_time:
        return end
    return end


def _had_window_earlier_today(windows: list[ScheduleWindow], instant: datetime) -> bool:
    weekday = instant.isoweekday()
    t = instant.timetz().replace(tzinfo=None)
    for window in windows:
        if weekday not in window.days_of_week:
            continue
        if window.start_time is None and window.end_time is None:
            return True
        if window.end_time and not _is_overnight(window) and t >= window.end_time:
            return True
        if window.ends_at_close and window.start_time and t >= window.start_time:
            return True
    return False


def _next_start_on_date(
    windows: list[ScheduleWindow],
    instant: datetime,
    on: date,
    *,
    after: datetime,
) -> datetime | None:
    weekday = on.isoweekday()
    candidates: list[datetime] = []
    for window in windows:
        if weekday not in window.days_of_week:
            continue
        if not _date_in_range(window, on):
            continue
        start = window.start_time or time(0, 0)
        start_dt = datetime.combine(on, start, tzinfo=instant.tzinfo)
        if start_dt > after:
            candidates.append(start_dt)
    return min(candidates) if candidates else None


def _next_start_after(windows: list[ScheduleWindow], instant: datetime) -> datetime | None:
    if not windows:
        return None
    cursor = instant
    for offset in range(0, 15):
        day = (instant + timedelta(days=offset)).date()
        after = (
            cursor
            if offset == 0
            else datetime.combine(day, time.min, tzinfo=instant.tzinfo) - timedelta(microseconds=1)
        )
        found = _next_start_on_date(windows, instant, day, after=after)
        if found is not None:
            return found
    return None


def _previous_weekday(weekday: int) -> int:
    return 7 if weekday == 1 else weekday - 1


def _format_time(dt: datetime) -> str:
    return dt.strftime("%-I:%M %p").replace(" 0", " ") if False else _format_time_portable(dt)


def _format_time_portable(dt: datetime) -> str:
    hour = dt.hour % 12 or 12
    suffix = "AM" if dt.hour < 12 else "PM"
    if dt.minute == 0:
        return f"{hour} {suffix}"
    return f"{hour}:{dt.minute:02d} {suffix}"


def _format_next(dt: datetime) -> str:
    return f"{dt.strftime('%A')} {_format_time_portable(dt)}"


def _active_label(ends_at: datetime | None, window: ScheduleWindow) -> str:
    if window.ends_at_close and window.end_time is None:
        return "Until close"
    if ends_at is None:
        return "Happening now"
    return f"Until {_format_time_portable(ends_at)}"
