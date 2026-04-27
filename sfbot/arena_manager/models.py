from dataclasses import dataclass

from sfbot.arena_manager.constants import IdleBuildingType


@dataclass(slots=True)
class IdleBuilding:
    building_type: IdleBuildingType
    level: int
    earning: int
    cycle_start: int
    cycle_end: int
    speed_boost: int
    money_boost: int
    upgrade_cost_1x: int
    upgrade_cost_10x: int
    upgrade_cost_25x: int
    upgrade_cost_100x: int


@dataclass(slots=True)
class MerchantOffer:
    index: int  # 1-based position (1, 2, or 3)
    offer_type: int
    cost: int

    @property
    def is_speed_boost(self) -> bool:
        return 1 <= self.offer_type <= 10

    @property
    def is_money_boost(self) -> bool:
        return 11 <= self.offer_type <= 20

    @property
    def building_type(self) -> IdleBuildingType | None:
        if self.is_speed_boost:
            return IdleBuildingType(self.offer_type)
        if self.is_money_boost:
            return IdleBuildingType(self.offer_type - 10)
        return None
