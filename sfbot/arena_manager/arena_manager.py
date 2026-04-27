from datetime import datetime, timezone

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
    IDLE_OFFER_COUNT,
    IDLE_OFFER_TYPE_BASE,
    IDLE_RESETS_INDEX,
    IDLE_SACRIFICE_RUNES_INDEX,
    IDLE_SPEED_BOOST_BASE,
    IDLE_TOTAL_SACRIFICED_INDEX,
    IDLE_UPGRADE_COST_1X_BASE,
    IDLE_UPGRADE_COST_10X_BASE,
    IDLE_UPGRADE_COST_25X_BASE,
    IDLE_UPGRADE_COST_100X_BASE,
    MERCHANT_MONEY_TOILET,
    MERCHANT_SPEED_TOILET,
    NO_RUNES_SACRIFICE_THRESHOLD,
    UPGRADE_ORDER,
    IdleBuildingType,
    IdleUpgradeAmount,
)
from sfbot.arena_manager.models import IdleBuilding, MerchantOffer
from sfbot.constants import VALUES_DELIMITER
from sfbot.logging import get_main_logger
from sfbot.session import GameSession
from sfbot.utils import format_large_number


class ArenaManager:
    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.resets: int = 0
        self.current_money: int = 0
        self.current_runes: int = 0
        self.sacrifice_runes: int = 0
        self.total_sacrificed: int = 0
        self.merchant_new_goods: int = 0
        self.buildings: dict[IdleBuildingType, IdleBuilding] = {}
        self.merchant_offers: list[MerchantOffer] = []
        self._next_sacrifice_after: int = 0
        self._parse()

    def _parse(self) -> None:
        raw = self.session.login_data.get("idle.idlesave", "")
        if not raw:
            return
        vals = raw.split(VALUES_DELIMITER)
        if len(vals) < IDLE_MIN_FIELDS:
            return

        self.resets = int(vals[IDLE_RESETS_INDEX])
        self.current_money = int(vals[IDLE_CURRENT_MONEY_INDEX])
        self.total_sacrificed = int(vals[IDLE_TOTAL_SACRIFICED_INDEX])
        self.sacrifice_runes = int(vals[IDLE_SACRIFICE_RUNES_INDEX])
        self.current_runes = int(vals[IDLE_CURRENT_RUNES_INDEX])
        self.merchant_new_goods = int(vals[IDLE_MERCHANT_NEW_GOODS_INDEX])

        self.buildings = {}
        for i in range(IDLE_BUILDING_COUNT):
            bt = IdleBuildingType(i + 1)
            self.buildings[bt] = IdleBuilding(
                building_type=bt,
                level=int(vals[IDLE_BUILDING_LEVEL_BASE + i]),
                earning=int(vals[IDLE_BUILDING_EARNING_BASE + i]),
                cycle_start=int(vals[IDLE_CYCLE_START_BASE + i]),
                cycle_end=int(vals[IDLE_CYCLE_END_BASE + i]),
                speed_boost=int(vals[IDLE_SPEED_BOOST_BASE + i]),
                money_boost=int(vals[IDLE_MONEY_BOOST_BASE + i]),
                upgrade_cost_1x=int(vals[IDLE_UPGRADE_COST_1X_BASE + i]),
                upgrade_cost_10x=int(vals[IDLE_UPGRADE_COST_10X_BASE + i]),
                upgrade_cost_25x=int(vals[IDLE_UPGRADE_COST_25X_BASE + i]),
                upgrade_cost_100x=int(vals[IDLE_UPGRADE_COST_100X_BASE + i]),
            )

        self.merchant_offers = []
        for i in range(IDLE_OFFER_COUNT):
            offer_type = int(vals[IDLE_OFFER_TYPE_BASE + i])
            offer_cost = int(vals[IDLE_OFFER_COST_BASE + i])
            if offer_type != 0:
                self.merchant_offers.append(
                    MerchantOffer(index=i + 1, offer_type=offer_type, cost=offer_cost)
                )

    def refresh(self) -> None:
        self._parse()

    @property
    def is_unlocked(self) -> bool:
        return bool(self.buildings)

    @property
    def toilet(self) -> IdleBuilding:
        return self.buildings[IdleBuildingType.TOILET]

    @property
    def has_toilet(self) -> bool:
        return self.toilet.level > 0

    def should_sacrifice(self) -> bool:
        if self.sacrifice_runes <= 0:
            return False

        # Scenario 1: NO_RUNES — sacrifice when enough runes available
        if self.current_runes == 0:
            return self.sacrifice_runes >= NO_RUNES_SACRIFICE_THRESHOLD

        # Scenario 2: NO_TOILET — sacrifice when gain >= current
        if not self.has_toilet:
            return self.sacrifice_runes >= self.current_runes

        # Scenario 3: HAS_TOILET — wait until first post-upgrade cycle completes
        if self._next_sacrifice_after <= 0:
            return True
        now = self.session.server_time()
        next_at = datetime.fromtimestamp(self._next_sacrifice_after, tz=timezone.utc)
        if now <= self._next_sacrifice_after:
            get_main_logger().debug(f"Arena Manager: next sacrifice at {next_at:%H:%M:%S}")
            return False
        get_main_logger().debug(
            f"Arena Manager: sacrifice ready (was scheduled {next_at:%H:%M:%S})"
        )
        return True

    @property
    def has_merchant_offers(self) -> bool:
        return len(self.merchant_offers) > 0

    def get_toilet_offers(self) -> list[MerchantOffer]:
        # Only Speed Boost (type 10) and Money Boost (type 20) for Toilet.
        # Skip Time offers (types 21-23) are excluded — they apply globally
        # and are not worth the mushroom cost. To add them later, match
        # offer_type in (21, 22, 23) here.
        result: list[MerchantOffer] = []
        for offer in self.merchant_offers:
            if offer.offer_type in (MERCHANT_SPEED_TOILET, MERCHANT_MONEY_TOILET):
                result.append(offer)
        return result

    def get_next_upgrade(
        self, start: int = 0
    ) -> tuple[IdleBuildingType, IdleUpgradeAmount, int] | None:
        for i in range(start, len(UPGRADE_ORDER)):
            bt, target = UPGRADE_ORDER[i]
            building = self.buildings[bt]
            if building is None:
                return None
            if building.level >= target:
                continue

            remaining = target - building.level
            amount, cost = self._pick_bulk(building, remaining)
            if amount is None or cost > self.current_money:
                return None
            return bt, amount, i

        return None

    def _pick_bulk(
        self, building: IdleBuilding, remaining: int
    ) -> tuple[IdleUpgradeAmount | None, int]:
        candidates: list[tuple[IdleUpgradeAmount, int]] = [
            (IdleUpgradeAmount.HUNDRED, building.upgrade_cost_100x),
            (IdleUpgradeAmount.TWENTY_FIVE, building.upgrade_cost_25x),
            (IdleUpgradeAmount.TEN, building.upgrade_cost_10x),
            (IdleUpgradeAmount.ONE, building.upgrade_cost_1x),
        ]
        for amount, cost in candidates:
            if amount <= remaining and cost <= self.current_money:
                return amount, cost
        return None, 0

    async def upgrade_building_async(
        self, building_type: IdleBuildingType, amount: IdleUpgradeAmount
    ) -> None:
        await self.session.request_and_update_async(
            "IdleIncrease", f"{building_type}/{amount}"
        )
        self.refresh()

    def mark_post_upgrade_cycle(self) -> None:
        if self.has_toilet and self.toilet.cycle_end > 0:
            self._next_sacrifice_after = self.toilet.cycle_end
            next_at = datetime.fromtimestamp(
                self._next_sacrifice_after, tz=timezone.utc
            )
            get_main_logger().info(f"Arena Manager: next sacrifice after {next_at:%H:%M:%S}")

    async def sacrifice_async(self) -> None:
        gained = self.sacrifice_runes
        new_total = self.current_runes + self.sacrifice_runes
        await self.session.request_and_update_async("IdlePrestige", "0")
        self.refresh()
        now_str = datetime.fromtimestamp(
            self.session.server_time(), tz=timezone.utc
        ).strftime("%H:%M:%S")
        get_main_logger().info(
            f"Arena Manager: sacrificed at {now_str}, gained {format_large_number(gained)} runes "
            f"(total: {format_large_number(new_total)})"
        )

    async def buy_merchant_offer_async(self, offer: MerchantOffer) -> None:
        await self.session.request_and_update_async(
            "IdleMercantBuy",
            f"{offer.index}/{offer.offer_type}/{offer.cost}",
        )
        kind = "Speed Boost" if offer.is_speed_boost else "Money Boost"
        building = offer.building_type
        building_name = building.name if building else "unknown"
        get_main_logger().info(
            f"Arena Manager: bought {kind} for {building_name} "
            f"(cost: {offer.cost} mushrooms)"
        )
