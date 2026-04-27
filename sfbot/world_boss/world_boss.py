from sfbot.constants import VALUES_DELIMITER
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.session import GameSession
from sfbot.world_boss.constants import (
    CATAPULT_BREAK_INDEX,
    ES_END_INDEX,
    ES_START_INDEX,
    ES_TYPE_INDEX,
    MAX_CATAPULT_HOURS,
    PROJECTILE_STORE_FIELDS,
    PROJECTILE_STORE_ITEMS,
    UPGRADE_FIELDS_PER_SLOT,
    UPGRADE_SLOT_COUNT,
    UPGRADE_STORE_FIELDS,
    UPGRADE_STORE_ITEMS,
    WB_BATTLE_REWARD_CHESTS_INDEX,
    WB_CATALYSTS_INDEX,
    WB_SEGMENT_INDEX,
    WORLD_BOSS_EVENT_TYPE,
    WT_FIRST_MAX_HP_INDEX,
    WT_HAS_HIT_INDEX,
    WT_WEAK_POINT_INDEX,
    PriceType,
    ProjectileType,
    TowerSegment,
    UpgradeType,
)
from sfbot.world_boss.models import (
    Catapult,
    CatapultUpgrade,
    Projectile,
    ProjectileOffer,
    UpgradeOffer,
)


class WorldBoss:
    """World Boss event — catapult management, upgrades, projectiles, chests."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        # Event timing (from eventstatus)
        self.event_start: int = 0
        self.event_end: int = 0
        # Character state (from wbcharacter)
        self.catalysts: int = 0
        self.segment: TowerSegment = TowerSegment.TOP
        self.battle_reward_chests: int = 0
        # Equipment
        self.catapult: Catapult | None = None
        self.projectile: Projectile | None = None
        # Stores
        self.upgrade_offers: list[UpgradeOffer] = []
        self.projectile_offers: list[ProjectileOffer] = []
        # Daily chests (from wbdailychests)
        self.daily_chests: list[int] = []
        # Tower state (from wbtower)
        self.weak_point: TowerSegment = TowerSegment.NONE
        self.has_hit_weak_point: bool = False
        self.segment_hp: dict[TowerSegment, int] = {}
        self.parse()

    def parse(self) -> None:
        data = self.session.login_data
        self._parse_event_status(data)
        if "wbcharacter" not in data:
            return
        self._parse_character(data)
        if "wbupgrade" in data:
            self._parse_catapult(data)
        if "wbammo" in data:
            self._parse_projectile(data)
        if "wbupgradestore" in data:
            self._parse_upgrade_store(data)
        if "wbammostore" in data:
            self._parse_projectile_store(data)
        if "wbdailychests" in data:
            self._parse_daily_chests(data)
        if "wbtower" in data:
            self._parse_tower(data)

    def _parse_event_status(self, data: dict[str, str]) -> None:
        if "eventstatus" not in data:
            return
        vals = [int(x) for x in data["eventstatus"].split(VALUES_DELIMITER) if x]
        if vals[ES_TYPE_INDEX] != WORLD_BOSS_EVENT_TYPE:
            return
        self.event_start = vals[ES_START_INDEX]
        self.event_end = vals[ES_END_INDEX]

    def _parse_character(self, data: dict[str, str]) -> None:
        vals = data["wbcharacter"].split(VALUES_DELIMITER)
        self.catalysts = int(vals[WB_CATALYSTS_INDEX])
        self.segment = TowerSegment(int(vals[WB_SEGMENT_INDEX]))
        self.battle_reward_chests = int(vals[WB_BATTLE_REWARD_CHESTS_INDEX])

    def _parse_catapult(self, data: dict[str, str]) -> None:
        self.catapult = None
        vals = [int(x) for x in data["wbupgrade"].split(VALUES_DELIMITER) if x]
        if vals[CATAPULT_BREAK_INDEX] == 0:
            return
        catapult = Catapult(breaks=vals[CATAPULT_BREAK_INDEX])
        remaining = vals[1:]
        for i in range(UPGRADE_SLOT_COUNT):
            start = i * UPGRADE_FIELDS_PER_SLOT
            end = start + UPGRADE_FIELDS_PER_SLOT
            if end > len(remaining):
                break
            chunk = remaining[start:end]
            if all(v == 0 for v in chunk):
                continue
            catapult.upgrades[i] = CatapultUpgrade(
                typ=UpgradeType(chunk[0]),
                restriction=TowerSegment(chunk[1]),
                amount=chunk[2],
                effect=chunk[3],
            )
        self.catapult = catapult

    def _parse_projectile(self, data: dict[str, str]) -> None:
        self.projectile = None
        vals = [int(x) for x in data["wbammo"].split(VALUES_DELIMITER) if x]
        if vals[0] == 0:
            return
        self.projectile = Projectile(
            typ=ProjectileType(vals[0]),
            amount=vals[1],
            extra_dmg=vals[2],
        )

    def _parse_upgrade_store(self, data: dict[str, str]) -> None:
        self.upgrade_offers = []
        vals = [int(x) for x in data["wbupgradestore"].split(VALUES_DELIMITER) if x]
        for i in range(UPGRADE_STORE_ITEMS):
            start = i * UPGRADE_STORE_FIELDS
            end = start + UPGRADE_STORE_FIELDS
            if end > len(vals):
                break
            chunk = vals[start:end]
            if all(v == 0 for v in chunk):
                continue
            self.upgrade_offers.append(
                UpgradeOffer(
                    slot=i + 1,
                    typ=UpgradeType(chunk[0]),
                    restriction=TowerSegment(chunk[1]),
                    effect=chunk[2],
                    main_price=chunk[3],
                    price_type=PriceType(chunk[4]),
                    catalyst_price=chunk[5],
                    mushroom_price=chunk[6],
                )
            )

    def _parse_projectile_store(self, data: dict[str, str]) -> None:
        self.projectile_offers = []
        vals = [int(x) for x in data["wbammostore"].split(VALUES_DELIMITER) if x]
        for i in range(PROJECTILE_STORE_ITEMS):
            start = i * PROJECTILE_STORE_FIELDS
            end = start + PROJECTILE_STORE_FIELDS
            if end > len(vals):
                break
            chunk = vals[start:end]
            if all(v == 0 for v in chunk):
                continue
            self.projectile_offers.append(
                ProjectileOffer(
                    slot=i + 1,
                    typ=ProjectileType(chunk[0]),
                    small_amount=chunk[1],
                    large_amount=chunk[2],
                    effect=chunk[3],
                    small_price=chunk[4],
                    large_price=chunk[5],
                )
            )

    def _parse_daily_chests(self, data: dict[str, str]) -> None:
        self.daily_chests = [
            int(x) for x in data["wbdailychests"].split(VALUES_DELIMITER) if x
        ]

    def _parse_tower(self, data: dict[str, str]) -> None:
        parts = data["wbtower"].split(VALUES_DELIMITER)
        wp = int(parts[WT_WEAK_POINT_INDEX])
        self.weak_point = TowerSegment(wp) if wp else TowerSegment.NONE
        self.has_hit_weak_point = int(parts[WT_HAS_HIT_INDEX]) != 0
        self.segment_hp = {}
        if len(parts) > WT_FIRST_MAX_HP_INDEX + 1:
            max_hp_str = parts[WT_FIRST_MAX_HP_INDEX]
            order = [TowerSegment.TOP, TowerSegment.MIDDLE, TowerSegment.BOTTOM]
            seg_idx = 0
            for i in range(WT_FIRST_MAX_HP_INDEX, len(parts) - 1):
                if parts[i] == max_hp_str and seg_idx < len(order):
                    self.segment_hp[order[seg_idx]] = int(parts[i + 1])
                    seg_idx += 1

    def refresh(self) -> None:
        self.parse()

    @property
    def is_active(self) -> bool:
        if self.event_end == 0:
            return False
        now = self.session.server_time()
        return self.event_start <= now < self.event_end

    @property
    def has_catapult(self) -> bool:
        if self.catapult is None:
            return False
        return self.catapult.breaks > self.session.server_time()

    @property
    def has_daily_chests(self) -> bool:
        return any(c > 0 for c in self.daily_chests)

    # ── Segment selection ────────────────────────────────────────────────

    def get_best_segment(self) -> TowerSegment:
        # Priority 1: hit the weak point if not done yet
        if (
            self.weak_point
            and self.weak_point != TowerSegment.NONE
            and not self.has_hit_weak_point
        ):
            return self.weak_point
        # Priority 2: match existing upgrade segment restriction
        upgrade_seg = self._get_upgrade_segment()
        if upgrade_seg:
            return upgrade_seg
        # Priority 3: segment with most HP remaining
        return self._get_most_hp_segment()

    def _get_upgrade_segment(self) -> TowerSegment | None:
        if not self.catapult:
            return None
        for upgrade in self.catapult.upgrades:
            if upgrade and upgrade.restriction != TowerSegment.NONE:
                return upgrade.restriction
        return None

    def _get_most_hp_segment(self) -> TowerSegment:
        if not self.segment_hp:
            return self.segment
        return max(self.segment_hp, key=lambda s: self.segment_hp[s])

    # ── API methods ──────────────────────────────────────────────────────

    async def enter_async(self) -> None:
        await self.session.request_and_update_async("WorldBossEnter")
        self.refresh()

    async def collect_daily_chests_async(self) -> None:
        await self.session.request_and_update_async("WorldBossOpenChest", "1")
        self.refresh()
        get_main_logger().info("World Boss: collected daily chests")

    async def collect_battle_rewards_async(self) -> None:
        count = self.battle_reward_chests
        await self.session.request_and_update_async("WorldBossOpenChest", "0")
        self.refresh()
        get_main_logger().info(f"World Boss: collected {count} battle reward chests")

    async def buy_catapult_async(self, hours: int = MAX_CATAPULT_HOURS) -> None:
        length = min(hours, self.catalysts, MAX_CATAPULT_HOURS)
        if length <= 0:
            return
        await self.session.request_and_update_async(
            "WorldBossUpgradeUnlock", str(length)
        )
        self.refresh()
        get_main_logger().info(
            f"World Boss: bought catapult ({length}h,"
            f" {self.catalysts} catalysts remaining)"
        )

    async def change_segment_async(self, segment: TowerSegment) -> None:
        await self.session.request_and_update_async(
            "WorldBossChangeLevel", str(segment.value)
        )
        self.refresh()
        get_main_logger().info(f"World Boss: changed to segment {self.segment.name}")

    async def buy_upgrade_async(self, slot: int) -> None:
        await self.session.request_and_update_async("WorldBossUpgradeBuy", f"{slot}/1")
        self.refresh()

    async def buy_projectile_async(self, slot: int, large: bool = False) -> None:
        amount = 2 if large else 1
        await self.session.request_and_update_async(
            "WorldBossAmmoBuy", f"{slot}/{amount}"
        )
        self.refresh()

    # ── High-level orchestration ─────────────────────────────────────────

    async def manage_async(self) -> None:
        await self.enter_async()

        if not self.is_active:
            return

        logger = get_main_logger()
        logger.info(
            f"World Boss: entered (catalysts={self.catalysts},"
            f" segment={self.segment.name},"
            f" catapult={'active' if self.has_catapult else 'none'})"
        )

        # Collect chests first (before any purchases)
        if self.has_daily_chests:
            try:
                await self.collect_daily_chests_async()
            except APIError as exc:
                logger.warning(f"World Boss: daily chest collection failed: {exc}")

        if self.battle_reward_chests > 0:
            try:
                await self.collect_battle_rewards_async()
            except APIError as exc:
                logger.warning(f"World Boss: battle reward collection failed: {exc}")

        # Buy catapult if missing or broken
        if not self.has_catapult and self.catalysts > 0:
            try:
                await self.buy_catapult_async()
            except APIError as exc:
                logger.warning(f"World Boss: catapult purchase failed: {exc}")

        # Buy upgrades if catapult is active
        if self.has_catapult and self.upgrade_offers:
            await self._buy_all_upgrades_async()

        # Buy projectiles if none equipped
        if self.projectile is None or self.projectile.amount == 0:
            await self._buy_projectiles_async()

        # Switch to best segment (after all purchases are done)
        best = self.get_best_segment()
        if best != self.segment:
            try:
                await self.change_segment_async(best)
            except APIError as exc:
                logger.warning(f"World Boss: segment switch failed: {exc}")

    async def _buy_all_upgrades_async(self) -> None:
        target = self._get_upgrade_segment()
        for offer in list(self.upgrade_offers):
            if (
                target
                and offer.restriction != TowerSegment.NONE
                and offer.restriction != target
            ):
                continue
            try:
                await self.buy_upgrade_async(offer.slot)
                get_main_logger().info(
                    f"World Boss: bought upgrade slot {offer.slot} ({offer.typ.name})"
                )
                if offer.restriction != TowerSegment.NONE:
                    target = offer.restriction
            except APIError:
                break

    async def _buy_projectiles_async(self) -> None:
        for offer in self.projectile_offers:
            if self.catalysts >= offer.small_price:
                try:
                    await self.buy_projectile_async(offer.slot)
                    get_main_logger().info(
                        f"World Boss: bought projectile {offer.typ.name}"
                        f" ({offer.small_price} catalysts)"
                    )
                    return
                except APIError:
                    continue
