from sfbot.constants import (
    ITEM_FIELD_COUNT,
    VALUES_DELIMITER,
    CharClass,
)
from sfbot.constants.enums import GemAttr
from sfbot.exceptions import APIError
from sfbot.inventory import Inventory
from sfbot.items import Item, parse_item
from sfbot.logging import get_main_logger
from sfbot.session import GameSession

# --- arcanetoilet field indices ---
TOILET_AURA_INDEX = 0
TOILET_MANA_INDEX = 1
TOILET_LAST_FLUSH_INDEX = 2
TOILET_MANA_TOTAL_INDEX = 3

# --- toiletstate field indices ---
TOILET_FILL_PERCENT_INDEX = 0
TOILET_SACRIFICES_LEFT_INDEX = 2


class Toilet:
    """Arcane Toilet - flush items for enchantments."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data
        toilet = data["arcanetoilet"].split(VALUES_DELIMITER)
        self.aura: int = int(toilet[TOILET_AURA_INDEX])
        self.mana: int = int(toilet[TOILET_MANA_INDEX])
        self.last_flush: int = int(toilet[TOILET_LAST_FLUSH_INDEX])
        self.mana_total: int = int(toilet[TOILET_MANA_TOTAL_INDEX])

        state = data["toiletstate"].split(VALUES_DELIMITER)
        self.fill_pct: int = int(state[TOILET_FILL_PERCENT_INDEX])
        self.sacrifices_left: int = int(state[TOILET_SACRIFICES_LEFT_INDEX])

    @property
    def can_flush(self) -> bool:
        return self.mana >= self.mana_total

    @property
    def can_sacrifice(self) -> bool:
        # When you throw item you get self.fill_pct to 0. If you did not sacrificed yet it will be fill_pct = 100.
        # Maybe handle if can sacrifice need to be calculated with self.fill_pct or we do not need that.
        return not (self.sacrifices_left == 0 and self.fill_pct == 0)

    @property
    def is_completed(self) -> bool:
        return not self.can_sacrifice

    def refresh(self) -> None:
        self._parse()

    def status(self) -> None:
        print(f"  Aura: {self.aura}")
        print(
            f"  Mana: {self.mana}/{self.mana_total} {'(READY)' if self.can_flush else ''}"
        )
        print(f"  Fill: {self.fill_pct}%")
        print(f"  Sacrifices left: {self.sacrifices_left}")

    async def flush_async(self) -> Item:
        result = await self.session.request_and_update_async("PlayerToilettFlush")
        return self._parse_flushed_item(result)

    def _parse_flushed_item(self, result: dict[str, str]) -> Item:
        spawn_slot = int(result["toilettSpawnSlot"])
        raw_data: list[str] = result["backpack"].split(VALUES_DELIMITER)
        vals = [int(x) for x in raw_data if x]
        offset = (spawn_slot - 1) * ITEM_FIELD_COUNT
        item = parse_item(vals[offset : offset + ITEM_FIELD_COUNT])
        if item is None:
            raise APIError(f"Failed to parse flushed item at slot {spawn_slot}")
        return item

    async def sacrifice_async(
        self,
        inventory: Inventory,
        char_class: CharClass,
    ) -> None:
        """Sacrifice a gem or item into the toilet."""
        self.refresh()
        if not self.can_sacrifice:
            return

        gem_protected_attrs = {GemAttr[char_class.main_attr.name], GemAttr.CONSTITUTION}
        slot = inventory.get_item_to_sacrifice(gem_protected_attrs)
        if slot and slot.item:
            await self.sacrifice_slot_async(slot.wire, slot.item.format())

    async def sacrifice_slot_async(self, wire: str, label: str) -> bool:
        logger = get_main_logger()
        try:
            await self.session.request_and_update_async("PlayerToilettLoad", str(wire))
            logger.info(f"Toilet: dropped {label}")
            return True
        except APIError as exc:
            logger.warning(f"Toilet: failed to drop {label}: {exc}")
            return False

    async def flush_toilet_async(self) -> None:
        """Flush the toilet if mana is full."""
        logger = get_main_logger()
        self.refresh()
        if not self.can_flush:
            return

        try:
            item = await self.flush_async()
            logger.info(f"Toilet: flushed → {item.format()}")
        except APIError as exc:
            logger.warning(f"Toilet: {exc}")

    async def wash_async(self, wire: str) -> None:
        """Wash an inventory item to re-roll its attrs."""
        await self.session.request_and_update_async("PlayerToilettWash", wire)
