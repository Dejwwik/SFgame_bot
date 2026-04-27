from dataclasses import dataclass

from sfbot.constants import (
    ITEM_FIELD_COUNT,
    VALUES_DELIMITER,
    ItemType,
    Rarity,
    ShopType,
)
from sfbot.exceptions import APIError, MoveError
from sfbot.inventory import Inventory
from sfbot.items import Item, format_item, parse_item
from sfbot.items.comparison import (
    ITEM_TYPE_TO_EQUIP_SLOT,
    ComparisonProfile,
    _would_oscillate,
    get_equip_wire_position,
    load_equipped_data,
    profile_equipped_items,
    score_item_best,
)
from sfbot.logging import get_main_logger
from sfbot.session import GameSession

BUY_EPIC_ITEMS = False
SPECIAL_ITEM_TYPES = {
    ItemType.SPECIAL,
    ItemType.SCRAPBOOK,
    ItemType.PET_ITEM,
    ItemType.QUICK_SAND_GLASS,
    ItemType.HEART_OF_DARKNESS,
    ItemType.WHEEL_OF_FORTUNE,
    ItemType.MANNEQUIN,
}


@dataclass(slots=True)
class ShopItem:
    """An item in a shop slot."""

    shop_position: int
    item: Item


class Shop:
    """Weapon and Magic shop access."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._checked: dict[str, str] = {}

    @property
    def _snapshot(self) -> str:
        w = self.session.login_data.get("storeitemsshakes", "")
        m = self.session.login_data.get("storeitemsfidget", "")
        return w + m

    def is_done(self, task: str) -> bool:
        return task in self._checked and self._checked[task] == self._snapshot

    def mark_done(self, task: str) -> None:
        self._checked[task] = self._snapshot

    # KEY IS storeitemsshakes | storeitemsfidget
    def _get_shop_items(self, key: str) -> list[ShopItem]:
        """Parse shop items from a response key."""
        raw = self.session.login_data[key].split(VALUES_DELIMITER)
        vals = [int(x) for x in raw if x]
        items: list[ShopItem] = []
        for i in range(6):
            offset = i * ITEM_FIELD_COUNT
            chunk = vals[offset : offset + ITEM_FIELD_COUNT]
            parsed = parse_item(chunk)

            # Should not happen!
            if not parsed:
                get_main_logger().warning(
                    f"Shop: failed to parse item in slot {i + 1} with data {chunk}"
                )
                raise APIError(f"Shop: failed to parse item in slot {i + 1}")

            items.append(ShopItem(shop_position=i + 1, item=parsed))
        return items

    def get_weapon_shop_items(self) -> list[ShopItem]:
        return self._get_shop_items("storeitemsshakes")

    def get_magic_shop_items(self) -> list[ShopItem]:
        return self._get_shop_items("storeitemsfidget")

    def show_shop(self, shop_type: ShopType = ShopType.WEAPON_SHOP) -> None:
        if shop_type == ShopType.WEAPON_SHOP:
            items = self.get_weapon_shop_items()
            print("\n=== Weapon Shop ===")
        else:
            items = self.get_magic_shop_items()
            print("\n=== Magic Shop ===")

        for si in items:
            print(
                f"  Slot {si.shop_position}: {format_item(si.item)} [Cost: {si.item.cost.format()}]"
            )

    def find_potions_in_shop(self) -> list[ShopItem]:
        """Find potions/elixirs in the magic shop."""
        return [
            si
            for si in self.get_magic_shop_items()
            if si.item.item_type == ItemType.POTION
        ]

    def find_free_potions_in_shop(self) -> list[ShopItem]:
        """Find free potions/elixirs in the magic shop."""
        return list(
            filter(lambda si: si.item.cost.mushrooms == 0, self.find_potions_in_shop())
        )

    def find_special_items_in_shop(self) -> list[tuple[ShopType, ShopItem]]:
        """Find special items across both shops. Returns (shop_type, item) pairs."""
        results: list[tuple[ShopType, ShopItem]] = []
        for shop_type, items in [
            (ShopType.WEAPON_SHOP, self.get_weapon_shop_items()),
            (ShopType.MAGIC_SHOP, self.get_magic_shop_items()),
        ]:
            for si in items:
                if si.item.item_type in SPECIAL_ITEM_TYPES:
                    results.append((shop_type, si))
        return results

    def find_free_special_items_in_shop(self) -> list[tuple[ShopType, ShopItem]]:
        """Find free special items across both shops. Returns (shop_type, item) pairs."""
        return list(
            filter(
                lambda pair: pair[1].item.cost.mushrooms == 0,
                self.find_special_items_in_shop(),
            )
        )

    def find_best_item(
        self,
        level: int,
        profiles: list[ComparisonProfile],
    ) -> tuple[ShopType, ShopItem, ComparisonProfile] | None:
        """Find shop items that score higher than current equipment.

        Returns (shop_type, shop_item, winning_profile) for the best candidate,
        or None if nothing beats current equipment.
        """
        equipped = load_equipped_data(self.session, profiles)

        results: list[tuple[ShopType, ShopItem, float, ComparisonProfile]] = []

        for shop_type, shop_items in [
            (ShopType.WEAPON_SHOP, self.get_weapon_shop_items()),
            (ShopType.MAGIC_SHOP, self.get_magic_shop_items()),
        ]:
            for shop_item in shop_items:
                item = shop_item.item
                if item.item_type not in ITEM_TYPE_TO_EQUIP_SLOT:
                    continue
                # Skip normal rarity items that cost mushrooms, as these are often not worth it.
                if item.cost.mushrooms > 0 and item.rarity == Rarity.NORMAL:
                    continue

                winner, item_score = score_item_best(
                    item,
                    level,
                    equipped,
                )
                if winner is not None:
                    entry = next(e for e in equipped if e.profile is winner)
                    current_item = entry.items[ITEM_TYPE_TO_EQUIP_SLOT[item.item_type]]
                    if _would_oscillate(item, current_item, level, entry):
                        continue
                    results.append((shop_type, shop_item, item_score, winner))

        # Sort based by the score of the winning profile, winner is first.
        results.sort(key=lambda x: x[2], reverse=True)
        best = results[0] if results else None

        if not best:
            return None

        # Return only needed data
        return best[0], best[1], best[3]

    def find_satisfable_best_item(
        self,
        level: int,
        profiles: list[ComparisonProfile],
        mushrooms: int,
        silver_total: int,
    ) -> tuple[ShopType, ShopItem, ComparisonProfile] | None:
        """Find shop items that improve on current equipment and are affordable."""
        logger = get_main_logger()

        best_item = self.find_best_item(level, profiles)
        if not best_item:
            return None

        cost = best_item[1].item.cost
        is_epic_or_above: bool = best_item[1].item.rarity != Rarity.NORMAL

        # If we want to buy epic, do not care about cost.
        if BUY_EPIC_ITEMS and is_epic_or_above:
            if cost.mushrooms > mushrooms or cost.silver > silver_total:
                logger.warning(
                    f"Shop: cannot afford {best_item[1].item.format()} "
                    f"(need {cost.mushrooms}m/{cost.silver}s, have {mushrooms}m/{silver_total}s)"
                )
                return None
            return best_item

        if cost.mushrooms == 0:
            return best_item
        return None

    async def buy_and_equip_item_async(
        self,
        inventory: Inventory,
        found: tuple[ShopType, ShopItem, ComparisonProfile],
    ) -> bool:
        """Buy a pre-found upgrade from the shop and equip it."""
        logger = get_main_logger()

        shop_type, shop_item, winner = found
        item = shop_item.item
        equip_slot = ITEM_TYPE_TO_EQUIP_SLOT[item.item_type]
        free_slot = inventory.get_free_slot()
        equip_wire = get_equip_wire_position(equip_slot, winner)

        old_item = profile_equipped_items(self.session, winner)[equip_slot]

        try:
            await self.buy_item_async(
                shop_type,
                shop_item.shop_position,
                free_slot.wire,  # type: ignore
                item,
            )
            # Re-read: shop price differs from inventory sell price, ident must match
            inventory_item = inventory.get_item_at_wire(free_slot.wire)  # type: ignore
            await inventory.move_item_async(free_slot.wire, equip_wire, inventory_item)  # type: ignore
            logger.info(f"Shop: bought and equipped {item.item_type.name}")
            logger.info(f"\told: {old_item.format() if old_item else None}")
            logger.info(f"\tnew: {item.format()}")
            return True
        except (APIError, MoveError) as exc:
            logger.warning(f"Shop: {exc}")
            return False

    async def buy_free_special_items_async(self, inventory: Inventory) -> None:
        """Buy all free special items from both shops."""
        logger = get_main_logger()
        for shop_type, si in self.find_free_special_items_in_shop():
            free_slot = inventory.get_free_slot()
            if not free_slot:
                logger.warning("Shop: inventory full")
                return
            try:
                await self.buy_item_async(
                    shop_type,
                    si.shop_position,
                    free_slot.wire,
                    si.item,
                )
                logger.info(f"Shop: bought {si.item.format()}")
            except APIError as exc:
                logger.warning(f"Shop: {exc}")

    async def buy_free_potions_async(self, inventory: Inventory) -> None:
        """Buy all free potions from the magic shop."""
        logger = get_main_logger()
        for si in self.find_free_potions_in_shop():
            free_slot = inventory.get_free_slot()
            if not free_slot:
                logger.warning("Elixir: inventory full")
                return
            try:
                await self.buy_item_async(
                    ShopType.MAGIC_SHOP,
                    si.shop_position,
                    free_slot.wire,
                    si.item,
                )
                logger.info(f"Elixir: bought {si.item.format()}")
            except APIError as exc:
                logger.warning(f"Elixir: {exc}")

    async def buy_item_async(
        self,
        shop_type: ShopType,
        shop_index: int,
        inventory_slot: str,
        item: Item,
    ) -> None:
        params = f"{shop_type}/{shop_index}/{inventory_slot}/{item.item_type}/{item.model}/{item.cost.silver}/{item.cost.mushrooms}"
        await self.session.request_and_update_async("PlayerItemMove", params)
