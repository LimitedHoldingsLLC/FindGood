from datetime import time

from app.domain.schedules.engine import ScheduleWindow
from app.domain.schedules.windows import deal_matches_time_filter
from app.domain.taxonomy.discovery import TimeBucket

HAPPY_HOUR = ScheduleWindow(
    days_of_week=frozenset({1, 2, 3, 4, 5}),
    start_time=time(15, 0),
    end_time=time(18, 0),
)
BRUNCH = ScheduleWindow(days_of_week=frozenset({6, 7}), start_time=time(9, 0), end_time=time(14, 0))
LATE = ScheduleWindow(days_of_week=frozenset({7}), start_time=time(21, 0), end_time=None, ends_at_close=True)
ALL_DAY = ScheduleWindow(days_of_week=frozenset({2}), start_time=None, end_time=None)


def test_afternoon_happy_hour_matches_afternoon_and_evening() -> None:
    assert deal_matches_time_filter([HAPPY_HOUR], when=TimeBucket.AFTERNOON)
    assert deal_matches_time_filter([HAPPY_HOUR], when=TimeBucket.EVENING)
    assert not deal_matches_time_filter([HAPPY_HOUR], when=TimeBucket.LUNCH)
    assert not deal_matches_time_filter([HAPPY_HOUR], when=TimeBucket.LATE_NIGHT)


def test_weekday_filter_excludes_weekend_only_brunch() -> None:
    assert deal_matches_time_filter([BRUNCH], weekday=6)
    assert not deal_matches_time_filter([BRUNCH], weekday=1)
    assert deal_matches_time_filter([BRUNCH], when=TimeBucket.LUNCH, weekday=7)
    assert not deal_matches_time_filter([BRUNCH], when=TimeBucket.LUNCH, weekday=1)


def test_late_night_until_close_matches_late_bucket() -> None:
    assert deal_matches_time_filter([LATE], when=TimeBucket.LATE_NIGHT)
    assert not deal_matches_time_filter([LATE], when=TimeBucket.LUNCH)


def test_all_day_matches_every_bucket_on_that_weekday() -> None:
    assert deal_matches_time_filter([ALL_DAY], when=TimeBucket.EVENING, weekday=2)
    assert not deal_matches_time_filter([ALL_DAY], when=TimeBucket.EVENING, weekday=3)
