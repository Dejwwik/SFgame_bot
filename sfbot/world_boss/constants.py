from enum import IntEnum

# ── eventstatus ──────────────────────────────────────────────────────────────
ES_TYPE_INDEX = 0
ES_START_INDEX = 2
ES_END_INDEX = 3
WORLD_BOSS_EVENT_TYPE = 6

# ── wbcharacter ──────────────────────────────────────────────────────────────
WB_CATALYSTS_INDEX = 0
WB_SEGMENT_INDEX = 3
WB_BATTLE_REWARD_CHESTS_INDEX = 12

# ── wbupgrade ────────────────────────────────────────────────────────────────
CATAPULT_BREAK_INDEX = 0
UPGRADE_FIELDS_PER_SLOT = 4
UPGRADE_SLOT_COUNT = 4

# ── Store layout ─────────────────────────────────────────────────────────────
UPGRADE_STORE_ITEMS = 3
UPGRADE_STORE_FIELDS = 7

PROJECTILE_STORE_ITEMS = 3
PROJECTILE_STORE_FIELDS = 6

# ── wbtower ──────────────────────────────────────────────────────────────────
WT_WEAK_POINT_INDEX = 2
WT_HAS_HIT_INDEX = 3
WT_FIRST_MAX_HP_INDEX = 6

# ── Tuning ───────────────────────────────────────────────────────────────────
MAX_CATAPULT_HOURS = 10


class TowerSegment(IntEnum):
    NONE = 0
    TOP = 1
    MIDDLE = 2
    BOTTOM = 3


class UpgradeType(IntEnum):
    MOTOR = 1  # damage bonus (has segment restriction)
    THREAD = 2  # shot speed
    AIMING_DEVICE = 3  # extra crit chance
    BOWL = 4  # extra crit damage


class ProjectileType(IntEnum):
    IMPACTING = 1  # always active
    BITING = 2  # only below 30% boss HP
    MANGLING = 3  # only above 70% boss HP


class PriceType(IntEnum):
    """Wire value for upgrade offer currency (raw wire - 1 maps to RewardType)."""

    MUSHROOMS = 3
    SILVER = 4
    LUCKY_COINS = 5
    WOOD = 6
    STONE = 7
    ARCANE = 8
    METAL = 9
    SOULS = 10
