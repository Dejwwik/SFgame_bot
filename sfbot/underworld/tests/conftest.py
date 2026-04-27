from unittest.mock import MagicMock

import pytest

from sfbot.underworld.constants import (
    BUILD_QUEUE,
    MAX_BUILDING_LEVEL,
    BuildingType,
    UnitType,
)
from sfbot.underworld.underworld import Underworld

B: type[BuildingType] = BuildingType
UNLIMITED: int = 999_999_999

QUEUE_TARGET: dict[BuildingType, int] = {}
for _tgt, _blds in BUILD_QUEUE:
    for _b in _blds:
        QUEUE_TARGET[_b] = max(QUEUE_TARGET.get(_b, 0), _tgt)


def all_at_zero() -> dict[BuildingType, int]:
    return {bt: 0 for bt in BuildingType}


def all_at_queue_target() -> dict[BuildingType, int]:
    return {bt: QUEUE_TARGET.get(bt, 0) for bt in BuildingType}


def all_at_max() -> dict[BuildingType, int]:
    return {bt: MAX_BUILDING_LEVEL[bt] for bt in BuildingType}


def levels(**building_levels: int) -> dict[BuildingType, int]:
    result = all_at_zero()
    for name, lvl in building_levels.items():
        result[B[name]] = lvl
    return result


def free_costs() -> dict[BuildingType, tuple[int, int, int]]:
    return {bt: (0, 0, 0) for bt in BuildingType}


def expensive_costs() -> dict[BuildingType, tuple[int, int, int]]:
    return {bt: (0, 9999, 9999) for bt in BuildingType}


def make_underworld(
    building_levels: dict[BuildingType, int] | None = None,
    building_costs: dict[BuildingType, tuple[int, int, int]] | None = None,
    upgrading: BuildingType | None = None,
    upgrade_finish: int = 0,
    unit_levels: dict[UnitType, int] | None = None,
    unit_counts: dict[UnitType, int] | None = None,
    unit_upgrade_costs: dict[UnitType, tuple[int, int, int]] | None = None,
    lure_level: int = 0,
    lured_today: int = 0,
    souls_collectable: int = 0,
    max_souls: int = 0,
) -> Underworld:
    session = MagicMock()
    session.login_data = {}
    session.server_time.return_value = 0
    uw = Underworld(session)

    if building_levels is not None:
        uw.building_levels = dict(building_levels)
    if building_costs is not None:
        uw.building_costs = dict(building_costs)
    elif building_levels is not None:
        uw.building_costs = free_costs()
    uw.upgrade_target = upgrading
    uw.upgrade_finish = upgrade_finish
    if unit_levels is not None:
        uw.unit_levels = dict(unit_levels)
    if unit_counts is not None:
        uw.unit_counts = dict(unit_counts)
    if unit_upgrade_costs is not None:
        uw.unit_upgrade_costs = dict(unit_upgrade_costs)
    uw.lure_level = lure_level
    uw.lured_today = lured_today
    uw.souls_collectable = souls_collectable
    uw.max_souls = max_souls
    return uw


def pick_upgrade(
    building_levels: dict[BuildingType, int],
    **kwargs,  # type: ignore[no-untyped-def]
) -> BuildingType | None:
    uw = make_underworld(building_levels=building_levels, **kwargs)
    return uw.pick_upgrade(UNLIMITED, UNLIMITED)


def run_full_progression(
    starting_levels: dict[BuildingType, int] | None = None,
) -> Underworld:
    uw = make_underworld(building_levels=starting_levels or all_at_zero())
    for _ in range(2000):
        building = uw.pick_upgrade(UNLIMITED, UNLIMITED)
        if building is None:
            break
        uw.building_levels[building] = uw.building_level(building) + 1
    return uw


@pytest.fixture
def fresh_underworld() -> Underworld:
    return make_underworld(building_levels=all_at_zero())
