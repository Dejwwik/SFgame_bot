from sfbot.constants import (
    RESOURCE_ARCANE_INDEX,
    RESOURCE_HOURGLASSES_INDEX,
    RESOURCE_LUCKY_COINS_INDEX,
    RESOURCE_METAL_INDEX,
    RESOURCE_MUSHROOMS_INDEX,
    RESOURCE_SILVER_RAW_INDEX,
    RESOURCE_SOULS_INDEX,
    RESOURCE_STONE_INDEX,
    RESOURCE_WOOD_INDEX,
    VALUES_DELIMITER,
)
from sfbot.session import GameSession


class Resources:
    """Player resources (gold, mushrooms, etc.)."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()

    def _parse(self) -> None:
        resource_raw = self.session.login_data.get("resources", "").split(
            VALUES_DELIMITER
        )
        values = [int(x) for x in resource_raw if x]
        self.silver_total: int = values[RESOURCE_SILVER_RAW_INDEX]
        self.gold: int = self.silver_total // 100
        self.silver: int = self.silver_total % 100
        self.mushrooms: int = values[RESOURCE_MUSHROOMS_INDEX]
        self.lucky_coins: int = values[RESOURCE_LUCKY_COINS_INDEX]
        self.hourglasses: int = values[RESOURCE_HOURGLASSES_INDEX]
        self.wood: int = values[RESOURCE_WOOD_INDEX]
        self.stone: int = values[RESOURCE_STONE_INDEX]
        self.metal: int = values[RESOURCE_METAL_INDEX]
        self.arcane: int = values[RESOURCE_ARCANE_INDEX]
        self.souls: int = values[RESOURCE_SOULS_INDEX]

    def refresh(self) -> None:
        self._parse()

    def show(self) -> None:
        print("\n=== Resources ===")
        print(f"  Gold: {self.gold:,}")
        print(f"  Silver: {self.silver}")
        print(f"  Mushrooms: {self.mushrooms:,}")
        print(f"  Lucky Coins: {self.lucky_coins:,}")
        print(f"  Hourglasses: {self.hourglasses:,}")
        print(f"  Souls: {self.souls:,}")
        print(f"  Arcane: {self.arcane:,}")
        print(f"  Metal: {self.metal:,}")
