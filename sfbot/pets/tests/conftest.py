from datetime import datetime, timezone

import pytest

from sfbot.constants import Event, Weekday


@pytest.fixture
def no_events() -> frozenset[Event]:
    return frozenset()


@pytest.fixture
def summer_day_params() -> dict:
    """Wednesday July 9, 12:00 — summer day."""
    return make_params(weekday=Weekday.WEDNESDAY, month=7, day=9, hour=12)


@pytest.fixture
def winter_day_params() -> dict:
    """Monday January 5, 12:00 — winter day."""
    return make_params(weekday=Weekday.MONDAY, month=1, day=5, hour=12)


@pytest.fixture
def fall_night_params() -> dict:
    """Thursday October 2, 22:00 — fall night."""
    return make_params(weekday=Weekday.THURSDAY, month=10, day=2, hour=22)


@pytest.fixture
def spring_night_params() -> dict:
    """Saturday April 12, 22:00 — spring night."""
    return make_params(weekday=Weekday.SATURDAY, month=4, day=12, hour=22)


def make_params(
    weekday: Weekday = Weekday.WEDNESDAY,
    events: frozenset[Event] = frozenset(),
    month: int = 6,
    day: int = 15,
    hour: int = 12,
    year: int | None = None,
) -> dict:
    """Build check() kwargs. Finds a year where month/day falls on weekday."""
    if year is not None:
        dt = datetime(year, month, day, hour, tzinfo=timezone.utc)
    else:
        for y in range(2020, 2035):
            try:
                if datetime(y, month, day).weekday() == weekday.value:
                    dt = datetime(y, month, day, hour, tzinfo=timezone.utc)
                    break
            except ValueError:
                continue
        else:
            dt = datetime(2026, month, day, hour, tzinfo=timezone.utc)
    return dict(events=events, server_time=int(dt.timestamp()))
