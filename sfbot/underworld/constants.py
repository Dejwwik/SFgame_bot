from enum import IntEnum


class BuildingType(IntEnum):
    HEART_OF_DARKNESS = 0
    GATE = 1
    GOLD_PIT = 2
    SOUL_EXTRACTOR = 3
    GOBLIN_PIT = 4
    TORTURE_CHAMBER = 5
    GLADIATOR_TRAINER = 6
    TROLL_BLOCK = 7
    ADVENTUROMATIC = 8
    KEEPER = 9


class UnitType(IntEnum):
    GOBLIN = 0
    TROLL = 1
    KEEPER = 2


class ResourceType(IntEnum):
    SOULS = 0
    SILVER = 1
    THIRST = 2


UNIT_BUILDINGS: dict[UnitType, BuildingType] = {
    UnitType.GOBLIN: BuildingType.GOBLIN_PIT,
    UnitType.TROLL: BuildingType.TROLL_BLOCK,
    UnitType.KEEPER: BuildingType.KEEPER,
}

REQUIRED_HEART_LEVEL: dict[BuildingType, int] = {
    BuildingType.HEART_OF_DARKNESS: 0,
    BuildingType.GATE: 2,
    BuildingType.GOLD_PIT: 4,
    BuildingType.SOUL_EXTRACTOR: 1,
    BuildingType.GOBLIN_PIT: 1,
    BuildingType.TORTURE_CHAMBER: 2,
    BuildingType.GLADIATOR_TRAINER: 3,
    BuildingType.TROLL_BLOCK: 3,
    BuildingType.ADVENTUROMATIC: 5,
    BuildingType.KEEPER: 5,
}

MAX_BUILDING_LEVEL: dict[BuildingType, int] = {
    BuildingType.HEART_OF_DARKNESS: 15,
    BuildingType.GATE: 15,
    BuildingType.GOLD_PIT: 100,
    BuildingType.SOUL_EXTRACTOR: 15,
    BuildingType.GOBLIN_PIT: 15,
    BuildingType.TORTURE_CHAMBER: 15,
    BuildingType.GLADIATOR_TRAINER: 15,
    BuildingType.TROLL_BLOCK: 15,
    BuildingType.ADVENTUROMATIC: 15,
    BuildingType.KEEPER: 15,
}

# Buildings whose level can exceed the Heart of Darkness level after a threshold
UNCAPPED_BY_HEART: dict[BuildingType, int] = {
    BuildingType.GOLD_PIT: 15,
}

# --- Field offsets (from owntower.towerSave) ---
BUILDING_LEVEL_BASE = 448
BUILDING_COUNT = 10

UNIT_DATA_BASE = 146
UNIT_DATA_STRIDE = 148
# Offsets within each unit block
UNIT_UPGRADED_AMOUNT = 0
UNIT_COUNT = 1
UNIT_TOTAL_ATTRIBUTES = 2
UNIT_LEVEL = 3

SOULS_COLLECTABLE = 459
SOULS_LIMIT_BUILDING = 460
SOULS_LIMIT_TOTAL = 461
SOULS_PER_HOUR = 463

SILVER_COLLECTABLE = 464
SILVER_LIMIT = 465
SILVER_PER_HOUR = 466

THIRST_CURRENT = 473
THIRST_LIMIT = 474
THIRST_PER_DAY = 475

LAST_COLLECTION_TIME = 467
UPGRADE_BUILDING = 468
UPGRADE_FINISH = 469
UPGRADE_BEGIN = 470
LURE_LEVEL = 471
LURED_TODAY = 472

# --- Price data ---
PRICE_FIELDS_PER_BUILDING = 3  # time, silver, souls
PRICE_TIME = 0
PRICE_SILVER = 1
PRICE_SOULS = 2

UNIT_PRICE_FIELDS = 3  # next_level, silver, souls
UNIT_PRICE_NEXT_LEVEL = 0
UNIT_PRICE_SILVER = 1
UNIT_PRICE_SOULS = 2

# --- Unlock / limits ---
UNLOCK_LEVEL = 125
REQUIRED_GEM_MINE_LEVEL = 10
MAX_LURES_PER_DAY = 5

# --- Unit upgrade queue (staged) ---
# Each stage: (target_level, [units_to_upgrade_to_that_level])
# Within a stage, lowest-level unit is upgraded first.
UNIT_UPGRADE_QUEUE: list[tuple[int, list[UnitType]]] = [
    # Stage 1: Goblins are cheapest & available first
    (100, [UnitType.GOBLIN]),
    # Stage 2: Keeper is the main win condition
    (300, [UnitType.KEEPER]),
    # Stage 3: Catch-up round
    (300, [UnitType.GOBLIN, UnitType.TROLL]),
    # Stage 4: Push Keeper further
    (600, [UnitType.KEEPER]),
    # Stage 5: Catch-up round
    (600, [UnitType.GOBLIN, UnitType.TROLL]),
    # Stage 6: Keeper forever (gated behind Gold Pit 100)
    (99_999, [UnitType.KEEPER]),
]

# Gold Pit must reach this level before advancing past stage 1
GOLD_PIT_GATE_LEVEL = 100

# --- Build Queue ---
BUILD_QUEUE: list[tuple[int, list[BuildingType]]] = [
    # Stage 1: Bootstrap — get Heart + Extractor + initial defense
    (
        1,
        [
            BuildingType.HEART_OF_DARKNESS,
            BuildingType.SOUL_EXTRACTOR,
            BuildingType.GOBLIN_PIT,
        ],
    ),
    # Stage 2: Unlock lure slots via Gate, basic soul bonuses
    (
        5,
        [
            BuildingType.HEART_OF_DARKNESS,
            BuildingType.SOUL_EXTRACTOR,
            BuildingType.GATE,
            BuildingType.TORTURE_CHAMBER,
        ],
    ),
    # Stage 3: Unlock Keeper + Troll
    (
        1,
        [
            BuildingType.KEEPER,
            BuildingType.TROLL_BLOCK,
        ],
    ),
    # Stage 4: Push soul generation to mid-game
    (
        10,
        [
            BuildingType.HEART_OF_DARKNESS,
            BuildingType.SOUL_EXTRACTOR,
            BuildingType.GATE,
            BuildingType.TORTURE_CHAMBER,
            BuildingType.KEEPER,
        ],
    ),
    # Stage 5: Character development buildings
    (
        10,
        [
            BuildingType.GLADIATOR_TRAINER,
            BuildingType.ADVENTUROMATIC,
            BuildingType.GOLD_PIT,
        ],
    ),
    # Stage 6: Max core buildings
    (
        15,
        [
            BuildingType.HEART_OF_DARKNESS,
            BuildingType.SOUL_EXTRACTOR,
            BuildingType.GATE,
            BuildingType.TORTURE_CHAMBER,
            BuildingType.KEEPER,
        ],
    ),
    # Stage 7: Max utility buildings
    (
        15,
        [
            BuildingType.GLADIATOR_TRAINER,
            BuildingType.ADVENTUROMATIC,
            BuildingType.GOLD_PIT,
        ],
    ),
    # Stage 8: Push Gold Pit beyond (uncapped by Heart)
    (
        100,
        [
            BuildingType.GOLD_PIT,
        ],
    ),
]
