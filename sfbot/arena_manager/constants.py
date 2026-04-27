from enum import IntEnum


class IdleBuildingType(IntEnum):
    SEAT = 1
    POPCORN_STAND = 2
    PARKING_LOT = 3
    TRAP = 4
    DRINKS = 5
    DEADLY_TRAP = 6
    VIP_SEAT = 7
    SNACKS = 8
    STRAYING_MONSTERS = 9
    TOILET = 10


class IdleUpgradeAmount(IntEnum):
    ONE = 1
    TEN = 10
    TWENTY_FIVE = 25
    HUNDRED = 100


# --- Parsing indices (from idle.idlesave) ---
IDLE_RESETS_INDEX = 2
IDLE_BUILDING_LEVEL_BASE = 3
IDLE_BUILDING_EARNING_BASE = 13
IDLE_CYCLE_START_BASE = 23
IDLE_CYCLE_END_BASE = 33
IDLE_SPEED_BOOST_BASE = 43
IDLE_MONEY_BOOST_BASE = 53
IDLE_MERCHANT_NEW_GOODS_INDEX = 63
IDLE_OFFER_TYPE_BASE = 65
IDLE_OFFER_COST_BASE = 68
IDLE_CURRENT_MONEY_INDEX = 72
IDLE_TOTAL_SACRIFICED_INDEX = 73
IDLE_SACRIFICE_RUNES_INDEX = 75
IDLE_CURRENT_RUNES_INDEX = 76
IDLE_UPGRADE_COST_1X_BASE = 78
IDLE_UPGRADE_COST_10X_BASE = 88
IDLE_UPGRADE_COST_25X_BASE = 98
IDLE_UPGRADE_COST_100X_BASE = 108

IDLE_MIN_FIELDS = 118
IDLE_BUILDING_COUNT = 10
IDLE_OFFER_COUNT = 3

# --- Config ---
ARENA_MANAGER_UNLOCK_LEVEL = 105
MERCHANT_SPEED_TOILET = IdleBuildingType.TOILET  # type 10
MERCHANT_MONEY_TOILET = IdleBuildingType.TOILET + 10  # type 20
NO_RUNES_SACRIFICE_THRESHOLD = 20

UPGRADE_BREAKPOINTS: list[int] = [25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

# Predefined upgrade order: (building, target_level) pairs.
# Each entry must be reached before proceeding to the next.
UPGRADE_ORDER: list[tuple[IdleBuildingType, int]] = [
    (IdleBuildingType.SEAT, 25),
    (IdleBuildingType.SEAT, 50),
    (IdleBuildingType.SEAT, 100),
    (IdleBuildingType.POPCORN_STAND, 25),
    (IdleBuildingType.SEAT, 250),
    (IdleBuildingType.POPCORN_STAND, 50),
    (IdleBuildingType.POPCORN_STAND, 100),
    (IdleBuildingType.PARKING_LOT, 25),
    (IdleBuildingType.PARKING_LOT, 50),
    (IdleBuildingType.POPCORN_STAND, 250),
    (IdleBuildingType.PARKING_LOT, 100),
    (IdleBuildingType.TRAP, 25),
    (IdleBuildingType.TRAP, 50),
    (IdleBuildingType.PARKING_LOT, 250),
    (IdleBuildingType.TRAP, 100),
    (IdleBuildingType.SEAT, 500),
    (IdleBuildingType.POPCORN_STAND, 500),
    (IdleBuildingType.TRAP, 250),
    (IdleBuildingType.PARKING_LOT, 500),
    (IdleBuildingType.DRINKS, 25),
    (IdleBuildingType.DRINKS, 50),
    (IdleBuildingType.DRINKS, 100),
    (IdleBuildingType.TRAP, 500),
    (IdleBuildingType.DEADLY_TRAP, 25),
    (IdleBuildingType.DEADLY_TRAP, 50),
    (IdleBuildingType.DEADLY_TRAP, 100),
    (IdleBuildingType.VIP_SEAT, 25),
    (IdleBuildingType.VIP_SEAT, 50),
    (IdleBuildingType.VIP_SEAT, 100),
    (IdleBuildingType.SNACKS, 25),
    (IdleBuildingType.SNACKS, 50),
    (IdleBuildingType.SNACKS, 100),
    (IdleBuildingType.STRAYING_MONSTERS, 25),
    (IdleBuildingType.STRAYING_MONSTERS, 50),
    (IdleBuildingType.STRAYING_MONSTERS, 100),
    (IdleBuildingType.TOILET, 25),
    (IdleBuildingType.TOILET, 50),
    (IdleBuildingType.TOILET, 100),
    (IdleBuildingType.DRINKS, 250),
    (IdleBuildingType.DEADLY_TRAP, 250),
    (IdleBuildingType.VIP_SEAT, 250),
    (IdleBuildingType.SNACKS, 250),
    (IdleBuildingType.STRAYING_MONSTERS, 250),
    (IdleBuildingType.TOILET, 250),
    (IdleBuildingType.DRINKS, 500),
    (IdleBuildingType.DEADLY_TRAP, 500),
    (IdleBuildingType.VIP_SEAT, 500),
    (IdleBuildingType.SNACKS, 500),
    (IdleBuildingType.STRAYING_MONSTERS, 500),
    (IdleBuildingType.TOILET, 500),
    (IdleBuildingType.SEAT, 1000),
    (IdleBuildingType.POPCORN_STAND, 1000),
    (IdleBuildingType.PARKING_LOT, 1000),
    (IdleBuildingType.TRAP, 1000),
    (IdleBuildingType.DRINKS, 1000),
    (IdleBuildingType.DEADLY_TRAP, 1000),
    (IdleBuildingType.VIP_SEAT, 1000),
    (IdleBuildingType.SNACKS, 1000),
    (IdleBuildingType.STRAYING_MONSTERS, 1000),
    (IdleBuildingType.TOILET, 1000),
    (IdleBuildingType.SEAT, 2500),
    (IdleBuildingType.POPCORN_STAND, 2500),
    (IdleBuildingType.PARKING_LOT, 2500),
    (IdleBuildingType.TRAP, 2500),
    (IdleBuildingType.DRINKS, 2500),
    (IdleBuildingType.DEADLY_TRAP, 2500),
    (IdleBuildingType.VIP_SEAT, 2500),
    (IdleBuildingType.SNACKS, 2500),
    (IdleBuildingType.STRAYING_MONSTERS, 2500),
    (IdleBuildingType.TOILET, 2500),
    (IdleBuildingType.SEAT, 5000),
    (IdleBuildingType.POPCORN_STAND, 5000),
    (IdleBuildingType.PARKING_LOT, 5000),
    (IdleBuildingType.TRAP, 5000),
    (IdleBuildingType.DRINKS, 5000),
    (IdleBuildingType.DEADLY_TRAP, 5000),
    (IdleBuildingType.VIP_SEAT, 5000),
    (IdleBuildingType.SNACKS, 5000),
    (IdleBuildingType.STRAYING_MONSTERS, 5000),
    (IdleBuildingType.TOILET, 5000),
    (IdleBuildingType.SEAT, 10000),
    (IdleBuildingType.POPCORN_STAND, 10000),
    (IdleBuildingType.PARKING_LOT, 10000),
    (IdleBuildingType.TRAP, 10000),
    (IdleBuildingType.DRINKS, 10000),
    (IdleBuildingType.DEADLY_TRAP, 10000),
    (IdleBuildingType.VIP_SEAT, 10000),
    (IdleBuildingType.SNACKS, 10000),
    (IdleBuildingType.STRAYING_MONSTERS, 10000),
    (IdleBuildingType.TOILET, 10000),
]
