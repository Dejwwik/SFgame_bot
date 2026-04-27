from unittest.mock import MagicMock

from sfbot.arena_manager.arena_manager import ArenaManager
from sfbot.arena_manager.constants import (
    IDLE_BUILDING_COUNT,
    IDLE_BUILDING_EARNING_BASE,
    IDLE_BUILDING_LEVEL_BASE,
    IDLE_CURRENT_MONEY_INDEX,
    IDLE_CURRENT_RUNES_INDEX,
    IDLE_CYCLE_END_BASE,
    IDLE_CYCLE_START_BASE,
    IDLE_MERCHANT_NEW_GOODS_INDEX,
    IDLE_MIN_FIELDS,
    IDLE_MONEY_BOOST_BASE,
    IDLE_OFFER_COST_BASE,
    IDLE_OFFER_TYPE_BASE,
    IDLE_RESETS_INDEX,
    IDLE_SACRIFICE_RUNES_INDEX,
    IDLE_SPEED_BOOST_BASE,
    IDLE_TOTAL_SACRIFICED_INDEX,
    IDLE_UPGRADE_COST_1X_BASE,
    IDLE_UPGRADE_COST_10X_BASE,
    IDLE_UPGRADE_COST_25X_BASE,
    IDLE_UPGRADE_COST_100X_BASE,
    IdleBuildingType,
)
from sfbot.arena_manager.models import IdleBuilding


def _build_idle_data(
    resets: int = 0,
    levels: list[int] | None = None,
    earnings: list[int] | None = None,
    cycle_starts: list[int] | None = None,
    cycle_ends: list[int] | None = None,
    speed_boosts: list[int] | None = None,
    money_boosts: list[int] | None = None,
    merchant_new_goods: int = 0,
    offer_types: list[int] | None = None,
    offer_costs: list[int] | None = None,
    current_money: int = 0,
    total_sacrificed: int = 0,
    sacrifice_runes: int = 0,
    current_runes: int = 0,
    upgrade_costs_1x: list[int] | None = None,
    upgrade_costs_10x: list[int] | None = None,
    upgrade_costs_25x: list[int] | None = None,
    upgrade_costs_100x: list[int] | None = None,
) -> str:
    n = IDLE_MIN_FIELDS
    vals = ["0"] * n

    vals[IDLE_RESETS_INDEX] = str(resets)
    vals[IDLE_CURRENT_MONEY_INDEX] = str(current_money)
    vals[IDLE_TOTAL_SACRIFICED_INDEX] = str(total_sacrificed)
    vals[IDLE_SACRIFICE_RUNES_INDEX] = str(sacrifice_runes)
    vals[IDLE_CURRENT_RUNES_INDEX] = str(current_runes)
    vals[IDLE_MERCHANT_NEW_GOODS_INDEX] = str(merchant_new_goods)

    _levels = levels or [0] * IDLE_BUILDING_COUNT
    _earnings = earnings or [0] * IDLE_BUILDING_COUNT
    _cycle_starts = cycle_starts or [0] * IDLE_BUILDING_COUNT
    _cycle_ends = cycle_ends or [0] * IDLE_BUILDING_COUNT
    _speed = speed_boosts or [0] * IDLE_BUILDING_COUNT
    _money = money_boosts or [0] * IDLE_BUILDING_COUNT
    _offers_t = offer_types or [0, 0, 0]
    _offers_c = offer_costs or [0, 0, 0]
    _c1 = upgrade_costs_1x or [100] * IDLE_BUILDING_COUNT
    _c10 = upgrade_costs_10x or [900] * IDLE_BUILDING_COUNT
    _c25 = upgrade_costs_25x or [2000] * IDLE_BUILDING_COUNT
    _c100 = upgrade_costs_100x or [7000] * IDLE_BUILDING_COUNT

    for i in range(IDLE_BUILDING_COUNT):
        vals[IDLE_BUILDING_LEVEL_BASE + i] = str(_levels[i])
        vals[IDLE_BUILDING_EARNING_BASE + i] = str(_earnings[i])
        vals[IDLE_CYCLE_START_BASE + i] = str(_cycle_starts[i])
        vals[IDLE_CYCLE_END_BASE + i] = str(_cycle_ends[i])
        vals[IDLE_SPEED_BOOST_BASE + i] = str(_speed[i])
        vals[IDLE_MONEY_BOOST_BASE + i] = str(_money[i])
        vals[IDLE_UPGRADE_COST_1X_BASE + i] = str(_c1[i])
        vals[IDLE_UPGRADE_COST_10X_BASE + i] = str(_c10[i])
        vals[IDLE_UPGRADE_COST_25X_BASE + i] = str(_c25[i])
        vals[IDLE_UPGRADE_COST_100X_BASE + i] = str(_c100[i])

    for i in range(3):
        vals[IDLE_OFFER_TYPE_BASE + i] = str(_offers_t[i])
        vals[IDLE_OFFER_COST_BASE + i] = str(_offers_c[i])

    return "/".join(vals)


def make_arena_manager(
    idle_data: str = "",
    server_time: int = 1000000,
    character_id: str = "test_account",
) -> ArenaManager:
    session = MagicMock()
    session.login_data = {"idle.idlesave": idle_data} if idle_data else {}
    session.server_time.return_value = server_time
    session.character_id = character_id
    return ArenaManager(session)


def make_building(
    building_type: IdleBuildingType = IdleBuildingType.SEAT,
    level: int = 0,
    cycle_start: int = 0,
    cycle_end: int = 0,
    upgrade_cost_1x: int = 100,
    upgrade_cost_10x: int = 900,
    upgrade_cost_25x: int = 2000,
    upgrade_cost_100x: int = 7000,
) -> IdleBuilding:
    return IdleBuilding(
        building_type=building_type,
        level=level,
        earning=0,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        speed_boost=0,
        money_boost=0,
        upgrade_cost_1x=upgrade_cost_1x,
        upgrade_cost_10x=upgrade_cost_10x,
        upgrade_cost_25x=upgrade_cost_25x,
        upgrade_cost_100x=upgrade_cost_100x,
    )
