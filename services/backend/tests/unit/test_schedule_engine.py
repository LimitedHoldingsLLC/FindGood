from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.domain.schedules.engine import (
    AvailabilityStatus,
    ScheduleWindow,
    evaluate_deal_availability,
)

LA = "America/Los_Angeles"
UTC = ZoneInfo("UTC")


def _at(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    # Interpret the clock as Los Angeles local, then convert to UTC for the caller.
    local = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(LA))
    return local.astimezone(UTC)


WEEKDAY_HH = ScheduleWindow(
    days_of_week=frozenset({1, 2, 3, 4, 5}),
    start_time=time(15, 0),
    end_time=time(18, 0),
)


def test_active_now_honors_venue_timezone_not_utc() -> None:
    # Friday 2026-08-14 15:30 in LA is 22:30 UTC. A UTC-naive check would miss this.
    result = evaluate_deal_availability([WEEKDAY_HH], LA, _at(2026, 8, 14, 15, 30))
    assert result.status == AvailabilityStatus.ACTIVE_NOW
    assert result.timezone == LA
    assert result.ends_at is not None
    assert result.label.startswith("Until")


def test_not_active_when_only_utc_would_match() -> None:
    # Friday 10:00 LA / 17:00 UTC — UTC 17:00 looks like happy hour; LA is morning.
    result = evaluate_deal_availability([WEEKDAY_HH], LA, _at(2026, 8, 14, 10, 0))
    assert result.status == AvailabilityStatus.ACTIVE_LATER_TODAY
    assert result.next_occurrence is not None
    assert result.next_occurrence.hour == 15


def test_starts_soon() -> None:
    result = evaluate_deal_availability([WEEKDAY_HH], LA, _at(2026, 8, 14, 14, 30))
    assert result.status == AvailabilityStatus.STARTS_SOON


def test_ended_today() -> None:
    result = evaluate_deal_availability([WEEKDAY_HH], LA, _at(2026, 8, 14, 19, 0))
    assert result.status == AvailabilityStatus.ENDED_TODAY


def test_weekend_unavailable_with_next_monday() -> None:
    result = evaluate_deal_availability([WEEKDAY_HH], LA, _at(2026, 8, 15, 16, 0))  # Saturday
    assert result.status == AvailabilityStatus.CURRENTLY_UNAVAILABLE
    assert result.next_occurrence is not None
    assert result.next_occurrence.isoweekday() == 1


def test_all_day_tuesday() -> None:
    window = ScheduleWindow(days_of_week=frozenset({2}), start_time=None, end_time=None)
    result = evaluate_deal_availability([window], LA, _at(2026, 8, 11, 11, 0))  # Tuesday
    assert result.status == AvailabilityStatus.ACTIVE_NOW


def test_sunday_nine_to_close() -> None:
    window = ScheduleWindow(
        days_of_week=frozenset({7}),
        start_time=time(21, 0),
        end_time=None,
        ends_at_close=True,
    )
    active = evaluate_deal_availability([window], LA, _at(2026, 8, 16, 22, 0))
    assert active.status == AvailabilityStatus.ACTIVE_NOW
    assert active.label == "Until close"
    early = evaluate_deal_availability([window], LA, _at(2026, 8, 16, 18, 0))
    assert early.status == AvailabilityStatus.ACTIVE_LATER_TODAY


def test_expired_limited_time() -> None:
    from datetime import date

    window = ScheduleWindow(
        days_of_week=frozenset({1, 2, 3, 4, 5}),
        start_time=time(17, 0),
        end_time=time(20, 0),
        valid_from=date(2026, 6, 1),
        valid_until=date(2026, 7, 15),
    )
    result = evaluate_deal_availability([window], LA, _at(2026, 8, 14, 17, 30))
    assert result.status == AvailabilityStatus.CURRENTLY_UNAVAILABLE
    assert result.next_occurrence is None


def test_overnight_window() -> None:
    window = ScheduleWindow(
        days_of_week=frozenset({5}),
        start_time=time(21, 0),
        end_time=time(1, 0),
    )
    late = evaluate_deal_availability([window], LA, _at(2026, 8, 14, 22, 30))
    assert late.status == AvailabilityStatus.ACTIVE_NOW
    after_midnight = evaluate_deal_availability([window], LA, _at(2026, 8, 15, 0, 30))
    assert after_midnight.status == AvailabilityStatus.ACTIVE_NOW
