from sfbot.constants import VALUES_DELIMITER
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.session import GameSession
from sfbot.underworld.constants import (
    BUILD_QUEUE,
    BUILDING_COUNT,
    BUILDING_LEVEL_BASE,
    GOLD_PIT_GATE_LEVEL,
    LAST_COLLECTION_TIME,
    LURE_LEVEL,
    LURED_TODAY,
    MAX_BUILDING_LEVEL,
    MAX_LURES_PER_DAY,
    PRICE_FIELDS_PER_BUILDING,
    PRICE_SILVER,
    PRICE_SOULS,
    PRICE_TIME,
    REQUIRED_HEART_LEVEL,
    SILVER_COLLECTABLE,
    SILVER_LIMIT,
    SILVER_PER_HOUR,
    SOULS_COLLECTABLE,
    SOULS_LIMIT_BUILDING,
    SOULS_LIMIT_TOTAL,
    SOULS_PER_HOUR,
    THIRST_CURRENT,
    THIRST_LIMIT,
    THIRST_PER_DAY,
    UNCAPPED_BY_HEART,
    UNIT_BUILDINGS,
    UNIT_COUNT,
    UNIT_DATA_BASE,
    UNIT_DATA_STRIDE,
    UNIT_LEVEL,
    UNIT_PRICE_FIELDS,
    UNIT_PRICE_NEXT_LEVEL,
    UNIT_PRICE_SILVER,
    UNIT_PRICE_SOULS,
    UNIT_TOTAL_ATTRIBUTES,
    UNIT_UPGRADE_QUEUE,
    UNIT_UPGRADED_AMOUNT,
    UPGRADE_BEGIN,
    UPGRADE_BUILDING,
    UPGRADE_FINISH,
    BuildingType,
    UnitType,
)


class Underworld:
    """Underworld management — buildings, resources, units, lure."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.building_levels: dict[BuildingType, int] = {}
        self.upgrade_target: BuildingType | None = None
        self.upgrade_finish: int = 0
        self.upgrade_begin: int = 0

        # Resources
        self.souls_collectable: int = 0
        self.souls_limit_building: int = 0
        self.souls_limit_total: int = 0
        self.souls_per_hour: int = 0
        self.silver_collectable: int = 0
        self.silver_limit: int = 0
        self.silver_per_hour: int = 0
        self.thirst_current: int = 0
        self.thirst_limit: int = 0
        self.thirst_per_day: int = 0
        self.last_collection_time: int = 0

        # Units
        self.unit_levels: dict[UnitType, int] = {u: 0 for u in UnitType}
        self.unit_counts: dict[UnitType, int] = {u: 0 for u in UnitType}
        self.unit_upgraded_amount: dict[UnitType, int] = {u: 0 for u in UnitType}
        self.unit_total_attributes: dict[UnitType, int] = {u: 0 for u in UnitType}

        # Lure
        self.lure_level: int = 0
        self.lured_today: int = 0

        # Costs
        self.building_costs: dict[BuildingType, tuple[int, int, int]] = {}
        self.unit_upgrade_costs: dict[UnitType, tuple[int, int, int]] = {}
        self.max_souls: int = 0

        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data

        raw = data.get("owntower.towerSave", "")
        if raw:
            vals = [int(x) for x in raw.split(VALUES_DELIMITER) if x]

            # Building levels
            if len(vals) > BUILDING_LEVEL_BASE + BUILDING_COUNT - 1:
                for bt in BuildingType:
                    self.building_levels[bt] = vals[BUILDING_LEVEL_BASE + bt.value]

            # Unit data
            for ut in UnitType:
                start = UNIT_DATA_BASE + ut.value * UNIT_DATA_STRIDE
                if start + UNIT_LEVEL < len(vals):
                    self.unit_upgraded_amount[ut] = vals[start + UNIT_UPGRADED_AMOUNT]
                    self.unit_counts[ut] = vals[start + UNIT_COUNT]
                    self.unit_total_attributes[ut] = vals[start + UNIT_TOTAL_ATTRIBUTES]
                    self.unit_levels[ut] = vals[start + UNIT_LEVEL]

            # Production - Souls
            if SOULS_PER_HOUR < len(vals):
                self.souls_collectable = vals[SOULS_COLLECTABLE]
                self.souls_limit_building = vals[SOULS_LIMIT_BUILDING]
                self.souls_limit_total = vals[SOULS_LIMIT_TOTAL]
                self.souls_per_hour = vals[SOULS_PER_HOUR]

            # Production - Silver
            if SILVER_PER_HOUR < len(vals):
                self.silver_collectable = vals[SILVER_COLLECTABLE]
                self.silver_limit = vals[SILVER_LIMIT]
                self.silver_per_hour = vals[SILVER_PER_HOUR]

            # Production - Thirst
            if THIRST_PER_DAY < len(vals):
                self.thirst_current = vals[THIRST_CURRENT]
                self.thirst_limit = vals[THIRST_LIMIT]
                self.thirst_per_day = vals[THIRST_PER_DAY]

            # State
            if LURED_TODAY < len(vals):
                self.last_collection_time = vals[LAST_COLLECTION_TIME]
                upgrade_raw = vals[UPGRADE_BUILDING]
                if upgrade_raw > 0:
                    self.upgrade_target = BuildingType(upgrade_raw - 1)
                else:
                    self.upgrade_target = None
                self.upgrade_finish = vals[UPGRADE_FINISH]
                self.upgrade_begin = vals[UPGRADE_BEGIN]
                self.lure_level = vals[LURE_LEVEL]
                self.lured_today = vals[LURED_TODAY]

        # Building costs
        price_raw = data.get("underworldprice.underworldPrice(10)", "")
        if price_raw:
            pvals = [int(x) for x in price_raw.split(VALUES_DELIMITER) if x]
            for bt in BuildingType:
                base = bt.value * PRICE_FIELDS_PER_BUILDING
                if base + PRICE_SOULS < len(pvals):
                    self.building_costs[bt] = (
                        pvals[base + PRICE_TIME],
                        pvals[base + PRICE_SILVER],
                        pvals[base + PRICE_SOULS],
                    )

        # Unit upgrade costs
        unit_price_raw = data.get(
            "underworldupgradeprice.underworldupgradePrice(3)", ""
        )
        if unit_price_raw:
            upvals = [int(x) for x in unit_price_raw.split(VALUES_DELIMITER) if x]
            for ut in UnitType:
                base = ut.value * UNIT_PRICE_FIELDS
                if base + UNIT_PRICE_SOULS < len(upvals):
                    self.unit_upgrade_costs[ut] = (
                        upvals[base + UNIT_PRICE_NEXT_LEVEL],
                        upvals[base + UNIT_PRICE_SILVER],
                        upvals[base + UNIT_PRICE_SOULS],
                    )

        # Max souls
        max_souls_raw = data.get("underworldmaxsouls", "")
        if max_souls_raw:
            self.max_souls = int(max_souls_raw)

    def refresh(self) -> None:
        self._parse()

    # --- Properties ---

    @property
    def heart_level(self) -> int:
        return self.building_levels.get(BuildingType.HEART_OF_DARKNESS, 0)

    @property
    def is_unlocked(self) -> bool:
        return bool(self.building_costs)

    @property
    def is_upgrading(self) -> bool:
        return self.upgrade_target is not None

    @property
    def upgrade_is_finished(self) -> bool:
        if self.upgrade_target is None:
            return False
        return self.upgrade_finish <= self.session.server_time()

    @property
    def max_lures(self) -> int:
        gate_level = self.building_level(BuildingType.GATE)
        return min(gate_level, MAX_LURES_PER_DAY)

    @property
    def can_lure(self) -> bool:
        if self.max_lures < 1:
            return False
        return self.lured_today < self.max_lures

    def building_level(self, building: BuildingType) -> int:
        return self.building_levels.get(building, 0)

    def is_building_maxed(self, building: BuildingType) -> bool:
        return self.building_level(building) >= MAX_BUILDING_LEVEL[building]

    @property
    def current_souls_collectable(self) -> int:
        if self.last_collection_time == 0:
            return self.souls_collectable
        elapsed = max(0, self.session.server_time() - self.last_collection_time)
        accumulated = self.souls_collectable + int(self.souls_per_hour * elapsed / 3600)
        return min(accumulated, self.souls_limit_building)

    @property
    def current_silver_collectable(self) -> int:
        if self.last_collection_time == 0:
            return self.silver_collectable
        elapsed = max(0, self.session.server_time() - self.last_collection_time)
        accumulated = self.silver_collectable + int(
            self.silver_per_hour * elapsed / 3600
        )
        return min(accumulated, self.silver_limit)

    @property
    def current_thirst_collectable(self) -> int:
        if self.last_collection_time == 0:
            return self.thirst_current
        elapsed = max(0, self.session.server_time() - self.last_collection_time)
        accumulated = self.thirst_current + int(self.thirst_per_day * elapsed / 86400)
        return min(accumulated, self.thirst_limit)

    def can_upgrade_unit(self, unit: UnitType) -> bool:
        building = UNIT_BUILDINGS[unit]
        if self.building_level(building) < 1:
            return False
        cost = self.unit_upgrade_costs.get(unit)
        if not cost:
            return False
        next_level, _, _ = cost
        return next_level > 0

    def can_upgrade(
        self,
        building: BuildingType,
        available_silver: int,
        available_souls: int,
    ) -> bool:
        if self.is_upgrading:
            return False
        level = self.building_level(building)
        if level >= MAX_BUILDING_LEVEL[building]:
            return False

        # Heart level cap
        if building != BuildingType.HEART_OF_DARKNESS:
            required = REQUIRED_HEART_LEVEL[building]
            uncap = UNCAPPED_BY_HEART.get(building)
            if uncap is not None and level >= uncap:
                if self.heart_level < required:
                    return False
            else:
                if self.heart_level < max(required, level + 1):
                    return False

        costs = self.building_costs.get(building)
        if not costs:
            return False
        _, cost_silver, cost_souls = costs
        return available_silver >= cost_silver and available_souls >= cost_souls

    def next_building_soul_cost(self) -> int:
        """Souls needed for the next building upgrade, 0 if none or already upgrading."""
        building = self.pick_upgrade(999_999_999, 999_999_999)
        if building is None:
            return 0
        cost = self.building_costs.get(building)
        if not cost:
            return 0
        return cost[PRICE_SOULS]

    def pick_upgrade(
        self, available_silver: int, available_souls: int
    ) -> BuildingType | None:
        for target_level, buildings in BUILD_QUEUE:
            if all(self.building_level(b) >= target_level for b in buildings):
                continue

            candidates = sorted(
                (
                    (self.building_level(b), idx, b)
                    for idx, b in enumerate(buildings)
                    if self.building_level(b) < target_level
                ),
                key=lambda x: (x[0], x[1]),
            )

            for _, _, building in candidates:
                if self.can_upgrade(building, available_silver, available_souls):
                    return building

                # If blocked by Heart level cap, try upgrading Heart instead
                level = self.building_level(building)
                required = REQUIRED_HEART_LEVEL.get(building, 0)
                uncap = UNCAPPED_BY_HEART.get(building)
                capped_by_heart = (
                    building != BuildingType.HEART_OF_DARKNESS
                    and not (uncap is not None and level >= uncap)
                    and self.heart_level < max(required, level + 1)
                )
                if not capped_by_heart:
                    return None

            # All candidates blocked by Heart — try upgrading Heart
            if self.can_upgrade(
                BuildingType.HEART_OF_DARKNESS, available_silver, available_souls
            ):
                return BuildingType.HEART_OF_DARKNESS

            return None
        return None

    def pick_unit_upgrade(self) -> UnitType | None:
        """Pick the next unit to upgrade based on the staged queue."""
        for i, (target_level, units) in enumerate(UNIT_UPGRADE_QUEUE):
            if all(self.unit_levels.get(u, 0) >= target_level for u in units):
                continue
            # Last stage: pause until Gold Pit reaches gate level
            if (
                i == len(UNIT_UPGRADE_QUEUE) - 1
                and self.building_level(BuildingType.GOLD_PIT) < GOLD_PIT_GATE_LEVEL
            ):
                return None
            candidates = [
                u
                for u in units
                if self.unit_levels.get(u, 0) < target_level
                and self.can_upgrade_unit(u)
            ]
            if not candidates:
                return None
            return min(candidates, key=lambda u: self.unit_levels.get(u, 0))
        return None

    # --- Async API methods ---

    async def collect_souls_async(self) -> bool:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("UnderworldGather", "2")
            self.refresh()
            return True
        except APIError as exc:
            logger.warning(f"Underworld: collect souls failed — {exc}")
            return False

    async def collect_silver_async(self) -> bool:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("UnderworldGather", "1")
            self.refresh()
            return True
        except APIError as exc:
            logger.warning(f"Underworld: collect silver failed — {exc}")
            return False

    async def collect_thirst_async(self) -> bool:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("UnderworldGather", "3")
            self.refresh()
            return True
        except APIError as exc:
            logger.warning(f"Underworld: collect thirst failed — {exc}")
            return False

    async def collect_resources_async(self, souls: bool, silver: bool) -> None:
        logger = get_main_logger()
        parts: list[str] = []
        if souls and await self.collect_souls_async():
            parts.append("souls")
        if silver and await self.collect_silver_async():
            parts.append("silver")
        if parts:
            logger.info(f"Underworld: collected {', '.join(parts)}")

    async def upgrade_building_async(self, building: BuildingType) -> None:
        logger = get_main_logger()
        param = str(building.value + 1)
        try:
            await self.session.request_and_update_async(
                "UnderworldBuildStart", f"{param}/0"
            )
            self.refresh()
            lvl = self.building_level(building)
            logger.info(f"Underworld: upgrading {building.name} to Lv{lvl + 1}")
        except APIError as exc:
            logger.warning(f"Underworld: upgrade failed — {exc}")

    async def finish_upgrade_async(self) -> None:
        logger = get_main_logger()
        if self.upgrade_target is None:
            return
        target = self.upgrade_target
        param = str(target.value + 1)
        try:
            await self.session.request_and_update_async(
                "UnderworldBuildFinished", f"{param}/0"
            )
            self.refresh()
            lvl = self.building_level(target)
            logger.info(f"Underworld: finished {target.name} → Lv{lvl}")
        except APIError as exc:
            logger.warning(f"Underworld: finish upgrade failed — {exc}")

    async def upgrade_unit_async(self, unit: UnitType) -> None:
        logger = get_main_logger()
        param = str(unit.value + 1)
        try:
            await self.session.request_and_update_async("UnderworldUpgradeUnit", param)
            self.refresh()
            lvl = self.unit_levels.get(unit, 0)
            logger.info(f"Underworld: upgraded {unit.name} to Lv{lvl}")
        except APIError as exc:
            logger.warning(f"Underworld: unit upgrade failed — {exc}")

    async def get_lure_suggestion_async(self) -> str | None:
        logger = get_main_logger()
        try:
            # Step 1: get suggested rank
            result = await self.session.request_and_update_async(
                "PlayerGetHallOfFame", "-4//0/0"
            )
            rank = result["Arenarank"]

            # Step 2: resolve rank → player name
            result = await self.session.request_and_update_async(
                "PlayerGetHallOfFame", f"{rank}//0/1"
            )
            entry = result["Ranklistplayer.r"].strip(";")
            name = entry.split(",")[1]

            # Step 3: resolve name → player_id
            result = await self.session.request_and_update_async("PlayerLookAt", name)
            return result["otherplayer.playerlookat"].split(VALUES_DELIMITER)[0]
        except APIError as exc:
            logger.warning(f"Underworld: lure suggestion failed — {exc}")
            return None
        except (KeyError, IndexError) as exc:
            logger.warning(f"Underworld: lure suggestion parse error — {exc}")
            return None

    async def lure_hero_async(self, player_id: str) -> tuple[bool, int] | None:
        logger = get_main_logger()
        try:
            result = await self.session.request_and_update_async(
                "UnderworldAttack", player_id
            )
            raw = result.get("fightresult.underworldpillage", "")
            vals = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
            won = vals[0] != 0 if vals else False
            souls_gained = vals[3] if len(vals) > 3 else 0
            self.refresh()
            if won:
                logger.info(f"Underworld: lured hero (won), +{souls_gained} souls")
            else:
                logger.info("Underworld: lured hero (lost)")
            return won, souls_gained
        except APIError as exc:
            logger.warning(f"Underworld: lure failed — {exc}")
            return None
