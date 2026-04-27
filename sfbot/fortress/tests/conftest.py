from unittest.mock import MagicMock

import pytest

from sfbot.fortress.fortress import (
    BUILD_QUEUE,
    MAX_BUILDING_LEVEL,
    BuildingType,
    Fortress,
    UnitType,
)

B: type[BuildingType] = BuildingType
UNLIMITED: int = 999_999_999

# Highest target each building reaches in BUILD_QUEUE (F2P strategy targets)
QUEUE_TARGET: dict[BuildingType, int] = {}
for _tgt, _blds in BUILD_QUEUE:
    for _b in _blds:
        QUEUE_TARGET[_b] = max(QUEUE_TARGET.get(_b, 0), _tgt)


# ── Level dict builders ──


def all_at_zero() -> dict[BuildingType, int]:
    return {bt: 0 for bt in BuildingType}


def all_at_queue_target() -> dict[BuildingType, int]:
    return {bt: QUEUE_TARGET[bt] for bt in BuildingType}


def all_at_max() -> dict[BuildingType, int]:
    return {bt: MAX_BUILDING_LEVEL[bt] for bt in BuildingType}


def levels(**building_levels: int) -> dict[BuildingType, int]:
    result = all_at_zero()
    for name, lvl in building_levels.items():
        result[B[name]] = lvl
    return result


def free_costs() -> dict[BuildingType, tuple[int, int, int, int]]:
    return {bt: (0, 0, 0, 0) for bt in BuildingType}


def expensive_costs() -> dict[BuildingType, tuple[int, int, int, int]]:
    return {bt: (0, 9999, 9999, 9999) for bt in BuildingType}


# ── Fortress factory ──


def make_fortress(
    building_levels: dict[BuildingType, int] | None = None,
    building_costs: dict[BuildingType, tuple[int, int, int, int]] | None = None,
    upgrading: BuildingType | None = None,
    hok_level: int = 0,
    hok_cost: tuple[int, int, int, int] | None = None,
    unit_levels: dict[UnitType, int] | None = None,
    unit_counts: dict[UnitType, int] | None = None,
    unit_in_training: dict[UnitType, int] | None = None,
    unit_training_finish: dict[UnitType, int] | None = None,
) -> Fortress:
    session = MagicMock()
    session.login_data = {}
    session.server_time.return_value = 0
    fortress = Fortress(session)

    if building_levels is not None:
        fortress.building_levels = dict(building_levels)
    if building_costs is not None:
        fortress.building_costs = dict(building_costs)
    else:
        fortress.building_costs = free_costs()
    fortress.upgrade_target = upgrading
    fortress.hok_level = hok_level
    fortress.hok_cost = hok_cost
    if unit_levels is not None:
        fortress.unit_levels = dict(unit_levels)
    if unit_counts is not None:
        fortress.unit_counts = dict(unit_counts)
    if unit_in_training is not None:
        fortress.unit_in_training = dict(unit_in_training)
    if unit_training_finish is not None:
        fortress.unit_training_finish = dict(unit_training_finish)
    return fortress


def pick_upgrade(
    building_levels: dict[BuildingType, int],
    **kwargs,  # type: ignore[no-untyped-def]
) -> BuildingType | None:
    fortress = make_fortress(building_levels=building_levels, **kwargs)
    return fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)


def run_full_progression(
    starting_levels: dict[BuildingType, int] | None = None,
) -> Fortress:
    fortress = make_fortress(building_levels=starting_levels or all_at_zero())
    for _ in range(2000):
        building = fortress.pick_upgrade(UNLIMITED, UNLIMITED, UNLIMITED)
        if building is None:
            break
        fortress.building_levels[building] = fortress.building_level(building) + 1
    return fortress


# ── Pytest fixtures ──


@pytest.fixture
def fresh_fortress() -> Fortress:
    return make_fortress(building_levels=all_at_zero())


@pytest.fixture
def unlocked_empty_fortress() -> Fortress:
    return make_fortress(building_levels={})


@pytest.fixture
def maxed_fortress() -> Fortress:
    return make_fortress(building_levels=all_at_max())


@pytest.fixture
def completed_queue_fortress() -> Fortress:
    return make_fortress(building_levels=all_at_queue_target())


@pytest.fixture
def upgrading_fortress() -> Fortress:
    return make_fortress(building_levels=all_at_zero(), upgrading=B.FORTRESS)


@pytest.fixture
def completed_progression() -> Fortress:
    return run_full_progression()


# ── Common mid-game snapshots ──

STAGE1_COMPLETE: dict[BuildingType, int] = levels(
    FORTRESS=1,
    LABORERS_QUARTERS=1,
    WOODCUTTER=1,
    QUARRY=1,
    GEM_MINE=1,
)

STAGE2_COMPLETE: dict[BuildingType, int] = levels(
    FORTRESS=5,
    LABORERS_QUARTERS=5,
    WOODCUTTER=5,
    QUARRY=5,
    BARRACKS=5,
    GEM_MINE=1,
)

STAGE3_COMPLETE: dict[BuildingType, int] = levels(
    FORTRESS=6,
    LABORERS_QUARTERS=6,
    WOODCUTTER=5,
    QUARRY=5,
    BARRACKS=6,
    GEM_MINE=1,
)

STAGES_1_TO_7_COMPLETE: dict[BuildingType, int] = levels(
    FORTRESS=15,
    LABORERS_QUARTERS=15,
    WOODCUTTER=5,
    QUARRY=5,
    BARRACKS=6,
    GEM_MINE=10,
    WALL=1,
    ARCHERY_GUILD=1,
    MAGES_TOWER=1,
    SMITHY=9,
)

STAGES_1_TO_8_COMPLETE: dict[BuildingType, int] = levels(
    FORTRESS=15,
    LABORERS_QUARTERS=15,
    WOODCUTTER=5,
    QUARRY=5,
    BARRACKS=10,
    GEM_MINE=10,
    WALL=1,
    ARCHERY_GUILD=1,
    MAGES_TOWER=1,
    SMITHY=9,
    ACADEMY=10,
    TREASURY=10,
)

ENDGAME_ONLY_GEM_MINE_LEFT: dict[BuildingType, int] = levels(
    FORTRESS=20,
    LABORERS_QUARTERS=15,
    WOODCUTTER=15,
    QUARRY=15,
    BARRACKS=15,
    GEM_MINE=30,
    SMITHY=20,
    ACADEMY=20,
    TREASURY=45,
    WALL=20,
    ARCHERY_GUILD=15,
    MAGES_TOWER=15,
)

STAGE1_BUILDINGS: list[BuildingType] = [
    B.FORTRESS,
    B.LABORERS_QUARTERS,
    B.WOODCUTTER,
    B.QUARRY,
    B.GEM_MINE,
]
