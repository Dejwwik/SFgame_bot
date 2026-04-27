from enum import IntEnum

from sfbot.constants import VALUES_DELIMITER
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.session import GameSession


class BuildingType(IntEnum):
    FORTRESS = 0
    LABORERS_QUARTERS = 1
    WOODCUTTER = 2
    QUARRY = 3
    GEM_MINE = 4
    ACADEMY = 5
    ARCHERY_GUILD = 6
    BARRACKS = 7
    MAGES_TOWER = 8
    TREASURY = 9
    SMITHY = 10
    WALL = 11


class ResourceType(IntEnum):
    WOOD = 0
    STONE = 1
    EXPERIENCE = 2


class UnitType(IntEnum):
    SOLDIER = 0
    MAGICIAN = 1
    ARCHER = 2


REQUIRED_FORTRESS_LEVEL: dict[BuildingType, int] = {
    BuildingType.FORTRESS: 0,
    BuildingType.LABORERS_QUARTERS: 1,
    BuildingType.QUARRY: 1,
    BuildingType.SMITHY: 1,
    BuildingType.WOODCUTTER: 1,
    BuildingType.TREASURY: 2,
    BuildingType.GEM_MINE: 3,
    BuildingType.BARRACKS: 4,
    BuildingType.WALL: 4,
    BuildingType.ARCHERY_GUILD: 5,
    BuildingType.ACADEMY: 6,
    BuildingType.MAGES_TOWER: 7,
}

UNIT_BUILDINGS: dict[UnitType, BuildingType] = {
    UnitType.SOLDIER: BuildingType.BARRACKS,
    UnitType.ARCHER: BuildingType.ARCHERY_GUILD,
    UnitType.MAGICIAN: BuildingType.MAGES_TOWER,
}

BUILDING_UNITS: dict[BuildingType, UnitType] = {v: k for k, v in UNIT_BUILDINGS.items()}

UNIT_LIMIT_MULTIPLIER: dict[UnitType, int] = {
    UnitType.SOLDIER: 3,
    UnitType.ARCHER: 2,
    UnitType.MAGICIAN: 1,
}

MAX_BUILDING_LEVEL: dict[BuildingType, int] = {
    BuildingType.FORTRESS: 20,
    BuildingType.LABORERS_QUARTERS: 15,
    BuildingType.WOODCUTTER: 20,
    BuildingType.QUARRY: 20,
    BuildingType.GEM_MINE: 100,
    BuildingType.ACADEMY: 20,
    BuildingType.ARCHERY_GUILD: 15,
    BuildingType.BARRACKS: 15,
    BuildingType.MAGES_TOWER: 15,
    BuildingType.TREASURY: 45,
    BuildingType.SMITHY: 20,
    BuildingType.WALL: 20,
}

# Buildings whose level can exceed the Fortress level
UNCAPPED_BY_FORTRESS: set[BuildingType] = {
    BuildingType.GEM_MINE,
    BuildingType.TREASURY,
}

# Chronological build queue — each stage is (target_level, [buildings]).
# All buildings in a stage must reach target_level before moving to the next.
# Within a stage, the lowest-level building is upgraded first (level-by-level).
# HoK is excluded — it's upgraded automatically via a separate command.
BUILD_QUEUE: list[tuple[int, list[BuildingType]]] = [
    # STAGE 1: Early game - unlock generation
    (
        1,
        [
            BuildingType.FORTRESS,
            BuildingType.WOODCUTTER,
            BuildingType.QUARRY,
            BuildingType.LABORERS_QUARTERS,
            BuildingType.GEM_MINE,
        ],
    ),
    # STAGE 2: Core buildings to Lv 4 (Prerequisite for Barracks)
    (
        4,
        [
            BuildingType.FORTRESS,
            BuildingType.LABORERS_QUARTERS,
            BuildingType.WOODCUTTER,
            BuildingType.QUARRY,
        ],
    ),
    # STAGE 3: Unlock Barracks and push all production to Lv 5
    (
        5,
        [
            BuildingType.FORTRESS,
            BuildingType.LABORERS_QUARTERS,
            BuildingType.WOODCUTTER,
            BuildingType.QUARRY,
            BuildingType.BARRACKS,
        ],
    ),
    # STAGE 4: The Raiding Sweet Spot (18 soldiers)
    (
        6,
        [
            BuildingType.FORTRESS,
            BuildingType.LABORERS_QUARTERS,
            BuildingType.BARRACKS,
        ],
    ),
    # STAGE 5: Mid-game Efficiency push (Gem Mine stays Level 1 for cheap gems)
    (
        10,
        [
            BuildingType.FORTRESS,
            BuildingType.LABORERS_QUARTERS,
        ],
    ),
    # STAGE 6: Underworld Prep (Only if near Character Level 100)
    (10, [BuildingType.GEM_MINE]),
    # STAGE 7: The "Golden Milestone" (75% Construction Time Reduction)
    (
        15,
        [
            BuildingType.FORTRESS,
            BuildingType.LABORERS_QUARTERS,
        ],
    ),
    # STAGE 8: Mandatory Defensive Anchors (Unlock only - KEEP AT LV 1)
    # Required only as a prerequisite for the Smithy.
    (
        1,
        [
            BuildingType.WALL,
            BuildingType.ARCHERY_GUILD,
            BuildingType.MAGES_TOWER,
        ],
    ),
    # STAGE 9: Combat scaling (Only if raiding becomes difficult)
    (
        9,
        [BuildingType.SMITHY],
    ),
    # STAGE 10: Utility and Experience scaling
    (
        10,
        [
            BuildingType.ACADEMY,
            BuildingType.TREASURY,
            BuildingType.BARRACKS,
        ],
    ),
    # STAGE 11: Maxing Fortress for maximum Wheel/Quest rewards
    (
        20,
        [BuildingType.FORTRESS],
    ),
    # STAGE 12: Late game functional maxing
    (
        15,
        [BuildingType.BARRACKS, BuildingType.WOODCUTTER, BuildingType.QUARRY],
    ),
    (
        20,
        [
            BuildingType.ACADEMY,
        ],
    ),
    (
        45,
        [
            BuildingType.TREASURY,
        ],
    ),
    # STAGE 13: Breaking the Shield (Final late-game maxing)
    # Only upgrade defense once resources are no longer a major concern.
    (
        20,
        [
            BuildingType.WALL,
            BuildingType.SMITHY,
        ],
    ),
    (
        15,
        [
            BuildingType.ARCHERY_GUILD,
            BuildingType.MAGES_TOWER,
        ],
    ),
    # STAGE 14: The 5.5 Year Plan (Final project)
    (
        100,
        [
            BuildingType.GEM_MINE,
        ],
    ),
]

# --- Fortress main data field indices (from Rust: fortress.update()) ---
# Building levels at [0..11] for each BuildingType
FORTRESS_BUILDING_LEVEL_BASE = 0
FORTRESS_BUILDING_COUNT = 12
FORTRESS_UPGRADE_TARGET_INDEX = 12  # building being upgraded (1-based, 0=none)
FORTRESS_UPGRADE_FINISH_INDEX = 13
FORTRESS_UPGRADE_START_INDEX = 14
FORTRESS_UPGRADES_INDEX = 15
FORTRESS_HONOR_INDEX = 16
FORTRESS_RANK_INDEX = 17
FORTRESS_ATTACK_FREE_REROLL_INDEX = 18
FORTRESS_ATTACK_TARGET_INDEX = 19
FORTRESS_GEM_TARGET_INDEX = 22
FORTRESS_GEM_FINISH_INDEX = 23
FORTRESS_GEM_START_INDEX = 24
FORTRESS_HOK_LEVEL_INDEX = 25

# --- Fortress storage data field indices (from Rust: fortress.update_resources()) ---
# last_collectable: [0]=wood, [1]=stone, [2]=xp
# production_limit: [3]=wood, [4]=stone, [5]=xp
# resource_limit: [6]=wood, [7]=stone
# per_hour: [8]=wood, [9]=stone, [10]=xp
# last_updated: [11]
# limit_next_level: [12]=wood, [13]=stone
# secret_storage_limit: [14]=wood, [15]=stone
STORAGE_COLLECTABLE_WOOD = 0
STORAGE_COLLECTABLE_STONE = 1
STORAGE_COLLECTABLE_XP = 2
STORAGE_PRODUCTION_LIMIT_WOOD = 3
STORAGE_PRODUCTION_LIMIT_STONE = 4
STORAGE_RESOURCE_LIMIT_WOOD = 6
STORAGE_RESOURCE_LIMIT_STONE = 7
STORAGE_PER_HOUR_WOOD = 8
STORAGE_PER_HOUR_STONE = 9
STORAGE_LAST_UPDATED = 11

# --- Fortress price data field indices (from Rust: fortress.update_prices()) ---
# 12 buildings × 4 fields each (time, silver, wood, stone)
PRICE_FIELDS_PER_BUILDING = 4
PRICE_TIME_OFFSET = 0
PRICE_SILVER_OFFSET = 1
PRICE_WOOD_OFFSET = 2
PRICE_STONE_OFFSET = 3

# --- Fortress units data field indices (from Rust: fortress.update_units()) ---
UNITS_COUNT_BASE = 0  # [0]=soldiers, [1]=mages, [2]=archers
UNITS_IN_TRAINING_BASE = 3
UNITS_TRAINING_START_BASE = 6
UNITS_TRAINING_FINISH_BASE = 9
UNITS_LEVEL_BASE = 12  # [12]=soldier_lvl, [13]=mage_lvl, [14]=archer_lvl

# --- Unit training cost indices (from unitprice.fortressPrice(3)) ---
# 3 unit types × 4 fields each (time, silver, wood, stone)
UNIT_PRICE_FIELDS = 4
UNIT_PRICE_TIME = 0
UNIT_PRICE_SILVER = 1
UNIT_PRICE_WOOD = 2
UNIT_PRICE_STONE = 3

# --- Opponent fortress info indices (from otherplayerfortressinfo) ---
# [0]=upgrades, [1]=wall_lvl, [2]=archers, [3]=mages, [4]=raid_wood, [5]=raid_stone
OPPONENT_RAID_WOOD = 4
OPPONENT_RAID_STONE = 5

# --- Attack strategy constants ---
ATTACK_SOLDIER_BUFFER = 2  # extra soldiers beyond advice
ATTACK_ROI_THRESHOLD = 5  # each resource gained must exceed 5x training cost
ATTACK_MAX_CAPACITY_RATIO = 0.9  # skip if advice > 90% of max soldiers

UNLOCK_LEVEL = 25
HOK_MAX_LEVEL = 20


class Fortress:
    """Fortress management — buildings, resources, gems, attacks."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.building_levels: dict[BuildingType, int] = {}
        self.upgrade_target: BuildingType | None = None
        self.upgrade_finish: int = 0
        self.honor: int = 0
        self.rank: int = 0
        self.attack_target: int = 0
        self.attack_free_reroll: int = 0
        self.gem_search_finish: int = 0
        self.hok_level: int = 0

        # Storage
        self.wood_collectable: int = 0
        self.stone_collectable: int = 0
        self.xp_collectable: int = 0
        self.wood_production_limit: int = 0
        self.stone_production_limit: int = 0
        self.wood_limit: int = 0
        self.stone_limit: int = 0
        self.wood_per_hour: int = 0
        self.stone_per_hour: int = 0
        self.storage_last_updated: int = 0

        # Units
        self.unit_counts: dict[UnitType, int] = {
            UnitType.SOLDIER: 0,
            UnitType.MAGICIAN: 0,
            UnitType.ARCHER: 0,
        }
        self.unit_in_training: dict[UnitType, int] = {
            UnitType.SOLDIER: 0,
            UnitType.MAGICIAN: 0,
            UnitType.ARCHER: 0,
        }
        self.unit_training_finish: dict[UnitType, int] = {
            UnitType.SOLDIER: 0,
            UnitType.MAGICIAN: 0,
            UnitType.ARCHER: 0,
        }
        self.unit_levels: dict[UnitType, int] = {
            UnitType.SOLDIER: 0,
            UnitType.MAGICIAN: 0,
            UnitType.ARCHER: 0,
        }

        # Prices (populated from fortressprice)
        self.building_costs: dict[BuildingType, tuple[int, int, int, int]] = {}
        # HoK upgrade cost: (time, silver, wood, stone)
        self.hok_cost: tuple[int, int, int, int] | None = None
        # Unit training costs: unit -> (time, silver, wood, stone)
        self.unit_training_costs: dict[UnitType, tuple[int, int, int, int]] = {}

        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data

        # --- Main fortress data ---
        raw = data.get("fortress", "")
        if not raw:
            return
        vals = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
        if len(vals) < FORTRESS_HOK_LEVEL_INDEX + 1:
            return

        for bt in BuildingType:
            self.building_levels[bt] = vals[FORTRESS_BUILDING_LEVEL_BASE + bt.value]

        upgrade_raw = vals[FORTRESS_UPGRADE_TARGET_INDEX]
        if upgrade_raw > 0:
            self.upgrade_target = BuildingType(upgrade_raw - 1)
        else:
            self.upgrade_target = None
        self.upgrade_finish = vals[FORTRESS_UPGRADE_FINISH_INDEX]
        self.honor = vals[FORTRESS_HONOR_INDEX]
        self.rank = vals[FORTRESS_RANK_INDEX]
        self.attack_free_reroll = vals[FORTRESS_ATTACK_FREE_REROLL_INDEX]
        self.attack_target = vals[FORTRESS_ATTACK_TARGET_INDEX]
        self.gem_search_finish = vals[FORTRESS_GEM_FINISH_INDEX]
        self.hok_level = vals[FORTRESS_HOK_LEVEL_INDEX]

        # --- Storage data ---
        storage_raw = data.get("fortressstorage", "")
        if storage_raw:
            svals = [int(x) for x in storage_raw.split(VALUES_DELIMITER) if x]
            if len(svals) > STORAGE_LAST_UPDATED:
                self.wood_collectable = svals[STORAGE_COLLECTABLE_WOOD]
                self.stone_collectable = svals[STORAGE_COLLECTABLE_STONE]
                self.xp_collectable = svals[STORAGE_COLLECTABLE_XP]
                self.wood_production_limit = svals[STORAGE_PRODUCTION_LIMIT_WOOD]
                self.stone_production_limit = svals[STORAGE_PRODUCTION_LIMIT_STONE]
                self.wood_limit = svals[STORAGE_RESOURCE_LIMIT_WOOD]
                self.stone_limit = svals[STORAGE_RESOURCE_LIMIT_STONE]
                self.wood_per_hour = svals[STORAGE_PER_HOUR_WOOD]
                self.stone_per_hour = svals[STORAGE_PER_HOUR_STONE]
                self.storage_last_updated = svals[STORAGE_LAST_UPDATED]

        # --- Unit data ---
        units_raw = data.get("fortressunits", "")
        if units_raw:
            uvals = [int(x) for x in units_raw.split(VALUES_DELIMITER) if x]
            if len(uvals) > UNITS_LEVEL_BASE + UnitType.ARCHER:
                for ut in UnitType:
                    self.unit_counts[ut] = uvals[UNITS_COUNT_BASE + ut]
                    self.unit_in_training[ut] = uvals[UNITS_IN_TRAINING_BASE + ut]
                    self.unit_training_finish[ut] = uvals[
                        UNITS_TRAINING_FINISH_BASE + ut
                    ]
                    self.unit_levels[ut] = uvals[UNITS_LEVEL_BASE + ut]

        # --- Building prices ---
        price_raw = data.get("fortressprice.fortressPrice(13)", "")
        if price_raw:
            pvals = [int(x) for x in price_raw.split(VALUES_DELIMITER) if x]
            for bt in BuildingType:
                base = bt.value * PRICE_FIELDS_PER_BUILDING
                if base + PRICE_STONE_OFFSET < len(pvals):
                    self.building_costs[bt] = (
                        pvals[base + PRICE_TIME_OFFSET],
                        pvals[base + PRICE_SILVER_OFFSET],
                        pvals[base + PRICE_WOOD_OFFSET],
                        pvals[base + PRICE_STONE_OFFSET],
                    )

        # --- Hall of Knights price ---
        hok_raw = data.get("fortressGroupPrice.fortressPrice", "")
        if hok_raw:
            hvals = [int(x) for x in hok_raw.split(VALUES_DELIMITER) if x]
            if len(hvals) >= 4:
                self.hok_cost = (hvals[0], hvals[1], hvals[2], hvals[3])

        # --- Unit training prices ---
        unit_price_raw = data.get("unitprice.fortressPrice(3)", "")
        if unit_price_raw:
            upvals = [int(x) for x in unit_price_raw.split(VALUES_DELIMITER) if x]
            for ut in UnitType:
                base = ut.value * UNIT_PRICE_FIELDS
                if base + UNIT_PRICE_STONE < len(upvals):
                    self.unit_training_costs[ut] = (
                        upvals[base + UNIT_PRICE_TIME],
                        upvals[base + UNIT_PRICE_SILVER],
                        upvals[base + UNIT_PRICE_WOOD],
                        upvals[base + UNIT_PRICE_STONE],
                    )

    @property
    def current_wood_collectable(self) -> int:
        """Actual wood ready to collect, extrapolated from last snapshot."""
        if self.storage_last_updated == 0:
            return self.wood_collectable
        elapsed = max(0, self.session.server_time() - self.storage_last_updated)
        accumulated = self.wood_collectable + int(self.wood_per_hour * elapsed / 3600)
        return min(accumulated, self.wood_production_limit)

    @property
    def current_stone_collectable(self) -> int:
        """Actual stone ready to collect, extrapolated from last snapshot."""
        if self.storage_last_updated == 0:
            return self.stone_collectable
        elapsed = max(0, self.session.server_time() - self.storage_last_updated)
        accumulated = self.stone_collectable + int(self.stone_per_hour * elapsed / 3600)
        return min(accumulated, self.stone_production_limit)

    def refresh(self) -> None:
        self._parse()

    @property
    def fortress_level(self) -> int:
        return self.building_levels.get(BuildingType.FORTRESS, 0)

    @property
    def is_unlocked(self) -> bool:
        return bool(self.building_levels)

    @property
    def is_upgrading(self) -> bool:
        return self.upgrade_target is not None

    @property
    def upgrade_is_finished(self) -> bool:
        if self.upgrade_target is None:
            return False
        return self.upgrade_finish <= self.session.server_time()

    @property
    def is_gem_searching(self) -> bool:
        return self.gem_search_finish > 0

    @property
    def gem_search_is_finished(self) -> bool:
        if not self.is_gem_searching:
            return False
        return self.gem_search_finish <= self.session.server_time()

    def is_training(self, unit: UnitType) -> bool:
        return self.unit_training_finish[unit] > self.session.server_time()

    @property
    def is_training_soldiers(self) -> bool:
        return self.is_training(UnitType.SOLDIER)

    @property
    def has_soldiers(self) -> bool:
        return self.unit_counts[UnitType.SOLDIER] > 0

    @property
    def has_attack_target(self) -> bool:
        return self.attack_target > 0

    @property
    def soldier_max_capacity(self) -> int:
        return (
            self.building_level(BuildingType.BARRACKS)
            * UNIT_LIMIT_MULTIPLIER[UnitType.SOLDIER]
        )

    @property
    def available_soldiers(self) -> int:
        return self.unit_counts[UnitType.SOLDIER]

    @property
    def soldiers_after_training(self) -> int:
        return (
            self.unit_counts[UnitType.SOLDIER] + self.unit_in_training[UnitType.SOLDIER]
        )

    @property
    def soldier_cost_wood(self) -> int:
        cost = self.unit_training_costs.get(UnitType.SOLDIER)
        return cost[UNIT_PRICE_WOOD] if cost else 0

    @property
    def soldier_cost_stone(self) -> int:
        cost = self.unit_training_costs.get(UnitType.SOLDIER)
        return cost[UNIT_PRICE_STONE] if cost else 0

    @property
    def can_free_reroll(self) -> bool:
        return self.attack_free_reroll <= self.session.server_time()

    async def fetch_opponent_info_async(self) -> tuple[int, int, int] | None:
        logger = get_main_logger()
        if self.attack_target <= 0:
            return None
        try:
            result = await self.session.request_and_update_async(
                "PlayerLookAt", str(self.attack_target)
            )
            advice_raw = result.get("soldieradvice", "")
            info_raw = result.get("otherplayerfortressinfo", "")
            if not advice_raw or not info_raw:
                logger.debug("Fortress: opponent info unavailable")
                return None
            advice = int(advice_raw)
            info_vals = [int(x) for x in info_raw.split(VALUES_DELIMITER) if x]
            if len(info_vals) <= OPPONENT_RAID_STONE:
                return None
            raid_wood = info_vals[OPPONENT_RAID_WOOD]
            raid_stone = info_vals[OPPONENT_RAID_STONE]
            return (advice, raid_wood, raid_stone)
        except APIError as exc:
            logger.warning(f"Fortress: fetch opponent info failed — {exc}")
            return None

    async def reroll_opponent_async(self) -> bool:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("FortressEnemy", "0")
            self.refresh()
            logger.info("Fortress: rerolled opponent (free)")
            return True
        except APIError as exc:
            logger.warning(f"Fortress: reroll failed — {exc}")
            return False

    def can_train(self, unit: UnitType) -> bool:
        building = UNIT_BUILDINGS[unit]
        if self.building_level(building) < 1:
            return False
        if self.upgrade_target == building:
            return False
        return self.trainable_count(unit) > 0

    def trainable_count(self, unit: UnitType) -> int:
        building = UNIT_BUILDINGS[unit]
        limit = self.building_level(building) * UNIT_LIMIT_MULTIPLIER[unit]
        return max(
            0,
            limit - self.unit_counts[unit] - self.unit_in_training[unit],
        )

    def building_level(self, building: BuildingType) -> int:
        return self.building_levels.get(building, 0)

    def is_building_maxed(self, building: BuildingType) -> bool:
        return self.building_level(building) >= MAX_BUILDING_LEVEL[building]

    @property
    def is_hok_maxed(self) -> bool:
        return self.hok_level >= HOK_MAX_LEVEL

    def can_upgrade_hok(
        self, available_wood: int, available_stone: int, available_silver: int
    ) -> bool:
        if self.is_hok_maxed:
            return False
        if self.hok_level >= self.fortress_level:
            return False
        if not self.hok_cost:
            return False
        _, cost_silver, cost_wood, cost_stone = self.hok_cost
        return (
            available_wood >= cost_wood
            and available_stone >= cost_stone
            and available_silver >= cost_silver
        )

    @property
    def smithy_level(self) -> int:
        return self.building_level(BuildingType.SMITHY)

    def unit_level(self, unit: UnitType) -> int:
        return self.unit_levels.get(unit, 0)

    def can_upgrade_unit(self, unit: UnitType) -> bool:
        building = UNIT_BUILDINGS[unit]
        if self.building_level(building) < 1:
            return False
        return self.unit_level(unit) < self.smithy_level

    def can_upgrade(
        self,
        building: BuildingType,
        available_wood: int,
        available_stone: int,
        available_silver: int,
    ) -> bool:
        if self.is_upgrading:
            return False
        unit = BUILDING_UNITS.get(building)
        if unit is not None and self.is_training(unit):
            return False
        if building == BuildingType.GEM_MINE and self.is_gem_searching:
            return False
        level = self.building_level(building)
        if level >= MAX_BUILDING_LEVEL[building]:
            return False

        # Fortress level cap only applies to buildings NOT in UNCAPPED set
        if (
            building != BuildingType.FORTRESS
            and building not in UNCAPPED_BY_FORTRESS
            and level >= self.fortress_level
        ):
            return False

        if self.fortress_level < REQUIRED_FORTRESS_LEVEL[building]:
            return False

        costs = self.building_costs.get(building)
        if not costs:
            return False
        _, cost_silver, cost_wood, cost_stone = costs
        return (
            available_wood >= cost_wood
            and available_stone >= cost_stone
            and available_silver >= cost_silver
        )

    def _phase_is_complete(self, buildings: list[BuildingType]) -> bool:
        return all(self.is_building_maxed(b) for b in buildings)

    def _needs_upgrade(self, building: BuildingType, target_level: int) -> bool:
        return self.building_level(building) < target_level

    def pick_upgrade(
        self, available_wood: int, available_stone: int, available_silver: int
    ) -> BuildingType | None:
        # Walk the build queue and find the first incomplete stage.
        # Within that stage, pick the lowest-level building that needs work.
        # If a building is blocked (e.g. Fortress level too low), check
        # whether Fortress itself still needs upgrading in *any* upcoming
        # stage and upgrade it first as a prerequisite.
        for target_level, buildings in BUILD_QUEUE:
            if all(self.building_level(b) >= target_level for b in buildings):
                continue

            # Collect buildings below target, sorted by level then list order
            candidates = sorted(
                (
                    (self.building_level(b), idx, b)
                    for idx, b in enumerate(buildings)
                    if self._needs_upgrade(b, target_level)
                ),
                key=lambda x: (x[0], x[1]),
            )

            for _, _, building in candidates:
                if self.can_upgrade(
                    building, available_wood, available_stone, available_silver
                ):
                    return building

                # Building can't be upgraded — if it's blocked by the fortress
                # level cap or unlock gate, upgrading FORTRESS is the right
                # prerequisite. Any other reason (no resources) means we stop.
                building_level = self.building_level(building)
                capped_by_fortress = (
                    building != BuildingType.FORTRESS
                    and building not in UNCAPPED_BY_FORTRESS
                    and building_level >= self.fortress_level
                )
                gated_by_fortress = (
                    self.fortress_level < REQUIRED_FORTRESS_LEVEL[building]
                )
                if not capped_by_fortress and not gated_by_fortress:
                    return None

            # All candidates are blocked by fortress level — upgrade FORTRESS
            # as a prerequisite if we can afford it.
            if self.can_upgrade(
                BuildingType.FORTRESS,
                available_wood,
                available_stone,
                available_silver,
            ):
                return BuildingType.FORTRESS

            return None
        return None

    async def collect_wood_async(self) -> bool:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("FortressGather", "1")
            self.refresh()
            return True
        except APIError as exc:
            logger.warning(f"Fortress: collect wood failed — {exc}")
            return False

    async def collect_stone_async(self) -> bool:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("FortressGather", "2")
            self.refresh()
            return True
        except APIError as exc:
            logger.warning(f"Fortress: collect stone failed — {exc}")
            return False

    async def collect_xp_async(self) -> bool:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("FortressGather", "3")
            self.refresh()
            return True
        except APIError as exc:
            logger.warning(f"Fortress: collect XP failed — {exc}")
            return False

    async def collect_resources_async(self, wood: bool, stone: bool, xp: bool) -> None:
        logger = get_main_logger()
        parts: list[str] = []
        if wood and await self.collect_wood_async():
            parts.append("wood")
        if stone and await self.collect_stone_async():
            parts.append("stone")
        if xp and await self.collect_xp_async():
            parts.append("XP")
        if parts:
            logger.info(f"Fortress: collected {', '.join(parts)}")

    async def upgrade_building_async(self, building: BuildingType) -> None:
        logger = get_main_logger()
        param = str(building.value + 1)
        try:
            await self.session.request_and_update_async(
                "FortressBuildStart", f"{param}/0"
            )
            self.refresh()
            lvl = self.building_level(building)
            logger.info(f"Fortress: upgrading {building.name} to Lv{lvl + 1}")
        except APIError as exc:
            logger.warning(f"Fortress: upgrade failed — {exc}")

    async def finish_upgrade_async(self) -> None:
        logger = get_main_logger()
        if self.upgrade_target is None:
            return
        target = self.upgrade_target
        param = str(target.value + 1)
        try:
            await self.session.request_and_update_async(
                "FortressBuildFinished", f"{param}/0"
            )

            self.refresh()
            lvl = self.building_level(target)
            logger.info(f"Fortress: finished {target.name} → Lv{lvl}")
        except APIError as exc:
            logger.warning(f"Fortress: finish upgrade failed — {exc}")

    async def start_gem_search_async(self) -> None:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("FortressGemstoneStart", "")
            logger.info("Fortress: started gem search")
        except APIError as exc:
            logger.warning(f"Fortress: gem search failed — {exc}")

    async def finish_gem_search_async(self) -> None:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("FortressGemstoneFinished", "0")
            logger.info("Fortress: collected gem")
        except APIError as exc:
            logger.warning(f"Fortress: gem collect failed — {exc}")

    async def train_unit_async(self, unit: UnitType, count: int = 1) -> None:
        logger = get_main_logger()
        param = f"{unit + 1}/{count}"
        try:
            await self.session.request_and_update_async("FortressBuildUnitStart", param)
            self.refresh()
            logger.info(f"Fortress: training {count} {unit.name.lower()}(s)")
        except APIError as exc:
            logger.warning(f"Fortress: train {unit.name.lower()} failed — {exc}")

    async def attack_async(self, soldiers: int) -> bool | None:
        logger = get_main_logger()
        try:
            result = await self.session.request_and_update_async(
                "FortressAttack", str(soldiers)
            )
            fight_raw = result["fightresult.fortresspillagerv1"]
            won = int(fight_raw.split(VALUES_DELIMITER)[0]) != 0
            self.refresh()
            return won
        except APIError as exc:
            logger.warning(f"Fortress: attack failed — {exc}")
            return None

    async def upgrade_hok_async(self) -> None:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("FortressGroupBonusUpgrade", "")
            self.refresh()
            logger.info(f"Fortress: upgraded Hall of Knights to Lv{self.hok_level}")
        except APIError as exc:
            logger.warning(f"Fortress: HoK upgrade failed — {exc}")

    async def upgrade_unit_async(self, unit: UnitType) -> None:
        logger = get_main_logger()
        param = str(unit.value + 1)
        try:
            await self.session.request_and_update_async("FortressUpgrade", param)
            self.refresh()
            lvl = self.unit_level(unit)
            logger.info(f"Fortress: upgraded {unit.name} to Lv{lvl}")
        except APIError as exc:
            logger.warning(f"Fortress: unit upgrade failed — {exc}")
