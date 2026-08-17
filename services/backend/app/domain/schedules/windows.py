"""Named time-of-day buckets for discovery. Honors overnight windows; no timezone math here.

Callers pass already-local schedule clocks. Weekday is ISO Monday=1.
"""

from datetime import time

from app.domain.schedules.engine import ScheduleWindow
from app.domain.taxonomy.discovery import TimeBucket

# Half-open local clock ranges. late_night wraps midnight.
_BUCKET_CLOCK: dict[TimeBucket, tuple[time, time]] = {
    TimeBucket.LUNCH: (time(11, 0), time(15, 0)),
    TimeBucket.AFTERNOON: (time(15, 0), time(17, 0)),
    TimeBucket.EVENING: (time(17, 0), time(21, 0)),
    TimeBucket.LATE_NIGHT: (time(21, 0), time(2, 0)),
}


def deal_matches_time_filter(
    schedules: list[ScheduleWindow],
    *,
    when: TimeBucket | None = None,
    weekday: int | None = None,
) -> bool:
    """True if any schedule can be used in the selected bucket and/or weekday."""
    if not schedules:
        return False
    return any(_schedule_matches(window, when=when, weekday=weekday) for window in schedules)


def _schedule_matches(
    window: ScheduleWindow,
    *,
    when: TimeBucket | None,
    weekday: int | None,
) -> bool:
    if weekday is not None and weekday not in window.days_of_week:
        return False
    if when is None:
        return True
    return _overlaps_bucket(window, when)


def _overlaps_bucket(window: ScheduleWindow, bucket: TimeBucket) -> bool:
    start, end = _BUCKET_CLOCK[bucket]
    return _ranges_overlap(_schedule_segments(window), _clock_segments(start, end))


def _minutes(clock: time) -> int:
    return clock.hour * 60 + clock.minute


def _clock_segments(start: time, end: time) -> list[tuple[int, int]]:
    begin = _minutes(start)
    finish = _minutes(end)
    if finish <= begin:
        return [(begin, 1440), (0, finish)]
    return [(begin, finish)]


def _schedule_segments(window: ScheduleWindow) -> list[tuple[int, int]]:
    if window.start_time is None and window.end_time is None:
        return [(0, 1440)]
    begin = _minutes(window.start_time) if window.start_time else 0
    if window.end_time is None:
        return [(begin, 1440)]
    finish = _minutes(window.end_time)
    if finish <= begin:
        return [(begin, 1440), (0, finish)]
    return [(begin, finish)]


def _ranges_overlap(left: list[tuple[int, int]], right: list[tuple[int, int]]) -> bool:
    for left_start, left_end in left:
        for right_start, right_end in right:
            if left_start < right_end and right_start < left_end:
                return True
    return False
