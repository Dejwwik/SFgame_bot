from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sfbot.constants import (
    BLACK_GEM_ATTR_RATIO,
    BLACK_GEM_SELL_RATIO,
    ITEM_FIELD_COUNT,
    LARGE_POTION_LEVEL,
    LEGENDARY_GEM_ATTR_RATIO,
    MAIN_BACKPACK_SLOT_COUNT,
    MEDIUM_POTION_LEVEL,
    VALUES_DELIMITER,
    WINGS_MODEL_ID,
    WIRE_EXTENDED_BACKPACK,
    WIRE_MAIN_BACKPACK,
    Attribute,
    EquipmentSlot,
    GemAttr,
    PotionAttributeType,
    PotionSize,
    Rarity,
    ShopType,
)
from sfbot.exceptions import APIError, GemExtractedAlert, InventoryStuckError, MoveError
from sfbot.items import Item, format_full_item, parse_item
from sfbot.items.comparison import (
    GEM_KEEP_RATIO,
    ITEM_TYPE_TO_EQUIP_SLOT,
    ComparisonProfile,
    _would_oscillate,
    get_equip_wire_position,
    load_equipped_data,
    profile_equipped_items,
    score_gem_best_placement,
    score_item_best,
)
from sfbot.logging import get_main_logger
from sfbot.potions.potions import POTIONS_PER_CYCLE, InventoryPotion, Potion
from sfbot.session import GameSession

if TYPE_CHECKING:
    from sfbot.character import Character
    from sfbot.smith.smith import Smith
    from sfbot.toilet.toilet import Toilet


# Rarity priority for selling items (epic first, legendary last)
SELL_RARITY_ORDER: list[Rarity] = [Rarity.EPIC, Rarity.LEGENDARY]


def get_max_potion_size(level: int) -> PotionSize:
    """Max potion size the character can receive at this level."""
    if level >= LARGE_POTION_LEVEL:
        return PotionSize.LARGE
    if level >= MEDIUM_POTION_LEVEL:
        return PotionSize.MEDIUM
    return PotionSize.SMALL


@dataclass(slots=True)
class InventorySlot:
    """A single occupied inventory slot."""

    index: int
    wire: str
    item: Item | None


def inventory_index_to_wire(index: int) -> str:
    """Convert a 0-based backpack index to wire position string."""
    if index < MAIN_BACKPACK_SLOT_COUNT:
        return f"{WIRE_MAIN_BACKPACK}/{index + 1}"
    return f"{WIRE_EXTENDED_BACKPACK}/{index - MAIN_BACKPACK_SLOT_COUNT + 1}"


class Inventory:
    """Backpack and equipment management."""

    def __init__(self, session: GameSession) -> None:
        self.session = session

    # --- Parsing ---

    def get_backpack(self) -> tuple[list[InventorySlot], int]:
        """Parse a slash-separated item list into (slots, total_slot_count)."""
        raw = self.session.login_data["backpack"].split(VALUES_DELIMITER)
        values = [int(x) for x in raw if x]
        total = len(values) // ITEM_FIELD_COUNT
        slots = [
            InventorySlot(
                index=i,
                wire=inventory_index_to_wire(i),
                item=parse_item(
                    values[i * ITEM_FIELD_COUNT : (i + 1) * ITEM_FIELD_COUNT]
                ),
            )
            for i in range(total)
        ]
        return slots, total

    def get_item_at_wire(self, wire: str) -> Item | None:
        """Get the item at a specific wire position from current login_data."""
        slots, _ = self.get_backpack()
        return next((s.item for s in slots if s.wire == wire), None)

    # --- Slot queries ---

    def get_free_slot(self) -> InventorySlot | None:
        """Find a free backpack slot, or None if inventory is full."""
        slots, _ = self.get_backpack()
        return next((s for s in slots if s.item is None), None)

    def has_free_slot(self) -> bool:
        return bool(self.get_free_slot())

    def get_gems(self) -> list[InventorySlot]:
        """Find gems in backpack."""
        slots, _ = self.get_backpack()
        return [s for s in slots if s.item and s.item.is_gem]

    def get_equippable_items(self) -> list[InventorySlot]:
        """Find equippable items (weapons, armor, etc.) in backpack."""
        slots, _ = self.get_backpack()
        return [
            s for s in slots if s.item and s.item.item_type in ITEM_TYPE_TO_EQUIP_SLOT
        ]

    def get_items_with_gems(self) -> list[InventorySlot]:
        """Find equippable items that have an inserted gem."""
        return [
            s for s in self.get_equippable_items() if s.item and s.item.inserted_gem
        ]

    def get_washable_items(self) -> list[InventorySlot]:
        """Find equippable items in backpack that haven't been washed yet."""
        return [s for s in self.get_equippable_items() if s.item and not s.item.washed]

    def get_potions(self) -> list[InventoryPotion]:
        """Get a list of inventory slots containing potions."""
        slots, _ = self.get_backpack()
        potions: list[InventoryPotion] = []
        for slot in slots:
            item = slot.item
            if not item or not item.is_potion:
                continue
            is_wings = item.model == WINGS_MODEL_ID
            attr = (
                PotionAttributeType.HP
                if is_wings
                else PotionAttributeType(item.potion_attr)
            )
            size = None if is_wings else PotionSize((item.model - 1) // 5 + 1)
            potions.append(
                InventoryPotion(
                    potion=Potion(attr=attr, size=size),
                    wire=slot.wire,
                    item=item,
                )
            )
        return potions

    def get_drinkable_potions(
        self,
        main_attr: Attribute,
        active_sizes: dict[PotionAttributeType, PotionSize | None],
    ) -> list[InventoryPotion]:
        """Return potions that should be drunk and can be drunk."""
        return [
            p
            for p in self.get_potions()
            if p.potion.should_drink(main_attr)
            and p.potion.can_drink(active_sizes.get(p.potion.attr))
        ]

    def has_drinkable_potions(
        self,
        main_attr: Attribute,
        active_sizes: dict[PotionAttributeType, PotionSize | None],
    ) -> bool:
        """True if the backpack contains potions that can be drunk."""
        return bool(self.get_drinkable_potions(main_attr, active_sizes))

    def get_potions_for_dungeon(
        self,
        main_attr: Attribute,
        credits: dict[PotionAttributeType, int],
    ) -> list[InventoryPotion]:
        """Return dungeon potions to drink for one 144h cycle, minus credits.

        Returns [] if inventory cannot guarantee the full cycle.
        """
        main_potion_attr = PotionAttributeType(main_attr.value)
        con_needed = max(
            0, POTIONS_PER_CYCLE - credits[PotionAttributeType.CONSTITUTION]
        )
        main_needed = max(0, POTIONS_PER_CYCLE - credits[main_potion_attr])
        wings_needed = max(0, 1 - credits[PotionAttributeType.HP])

        all_potions = self.get_potions()
        con = [
            p
            for p in all_potions
            if p.potion.attr == PotionAttributeType.CONSTITUTION
            and p.potion.size == PotionSize.LARGE
        ]
        main = [
            p
            for p in all_potions
            if p.potion.attr == main_potion_attr and p.potion.size == PotionSize.LARGE
        ]
        wings_list = [p for p in all_potions if p.potion.attr == PotionAttributeType.HP]

        if (
            con_needed > len(con)
            or main_needed > len(main)
            or wings_needed > len(wings_list)
        ):
            return []

        return con[:con_needed] + main[:main_needed] + wings_list[:wings_needed]

    def has_potions_for_dungeon(
        self,
        main_attr: Attribute,
        credits: dict[PotionAttributeType, int],
    ) -> bool:
        """True if inventory can cover one 144h dungeon cycle minus credits."""
        return bool(self.get_potions_for_dungeon(main_attr, credits))

    # --- Finders for ensure_free_slot priority chain ---

    def get_off_attr_potion(
        self,
        potion_attrs_to_keep: set[PotionAttributeType],
    ) -> InventorySlot | None:
        """Find an off-attr potion to sell (stage 3)."""
        return next(
            (
                InventorySlot(
                    0, p.wire, p.item
                )  # index unused, only wire matters for selling
                for p in self.get_potions()
                if p.item
                and p.item.model != WINGS_MODEL_ID
                and p.potion.attr not in potion_attrs_to_keep
            ),
            None,
        )

    def get_sub_max_potion(
        self,
        potion_attrs_to_keep: set[PotionAttributeType],
        max_potion_size: PotionSize,
    ) -> InventorySlot | None:
        """Find a kept-attr potion below max size to sell (stage 4)."""
        return next(
            (
                InventorySlot(
                    0, p.wire, p.item
                )  # index unused, only wire matters for selling
                for p in self.get_potions()
                if p.item
                and p.item.model != WINGS_MODEL_ID
                and p.potion.attr in potion_attrs_to_keep
                and p.potion.size
                and p.potion.size < max_potion_size
            ),
            None,
        )

    def get_sellable_gem(self, gem_attrs_to_keep: set[GemAttr]) -> InventorySlot | None:
        """Sell the first gem whose attr is NOT in gem_attrs_to_keep.

        Legendary gems are always skipped regardless of gem_attrs_to_keep.
        No value check — any unprotected gem is immediately sellable.
        Used in stages 2, 5, and 10.

        See get_low_value_gem() for value-aware gem selling.
        """
        for slot in self.get_gems():
            item = slot.item
            if not item:
                continue
            if item.gem_attr == GemAttr.LEGENDARY:
                continue
            if item.gem_attr not in gem_attrs_to_keep:
                return slot
        return None

    def get_sellable_item(
        self,
        sell_rarity: Rarity,
        protected_gem_attrs: set[GemAttr],
    ) -> InventorySlot | None:
        for slot in self.get_equippable_items():
            item = slot.item
            if not item:
                continue
            if item.rarity != sell_rarity:
                continue
            if item.inserted_gem and item.inserted_gem.attr in protected_gem_attrs:
                continue
            return slot
        return None

    def get_low_value_gem(
        self,
        average_gem_single_attr_value: float,
        restrict_to_attrs: set[GemAttr],
    ) -> InventorySlot | None:
        """Sell a gem only if its value is below a threshold.

        Unlike get_sellable_gem() which sells any gem outside the protected
        set regardless of value, this function checks gem power against the
        server average before selling.

        Two modes:

        Restricted (stage 8): restrict_to_attrs is non-empty (e.g. {STR, CON}).
            Only sells gems whose attr is in that set (minus legendary/black).
            A gem is "low value" if its power < average * GEM_KEEP_RATIO.
            Purpose: sell weak main-attr/CON gems we'd normally protect.

        Unrestricted (stage 12): restrict_to_attrs is empty.
            Sells ANY non-legendary gem. Single-attr gems are always sellable
            (we're desperate for space). Black gems only if their value is
            below average * GEM_KEEP_RATIO * BLACK_GEM_ATTR_RATIO (lower bar
            because black gems contribute to all 5 attrs).
        """
        # sellable_attrs — attrs we're willing to sell, with legendary/black stripped
        #   non-empty = restricted mode (only sell gems matching these attrs)
        #   empty     = unrestricted mode (sell any non-legendary gem)
        sellable_attrs = restrict_to_attrs - {GemAttr.LEGENDARY, GemAttr.BLACK}

        for slot in self.get_gems():
            item = slot.item
            if not item or item.gem_attr is None or item.gem_value is None:
                continue
            if item.gem_attr == GemAttr.LEGENDARY:
                continue

            if sellable_attrs:
                # --- Restricted mode (stage 8) ---
                # Only consider gems whose attr is in the sellable set (e.g. STR, CON)
                if item.gem_attr not in sellable_attrs:
                    continue
                # Sell if the gem's value is below the keep threshold
                if item.gem_value < average_gem_single_attr_value * GEM_KEEP_RATIO:
                    return slot
            else:
                # --- Unrestricted mode (stage 12) ---
                # Any single-attr gem (STR/DEX/INT/CON/LUCK) is sellable — we need space
                if item.gem_attr != GemAttr.BLACK:
                    return slot
                # Black gems contribute to all 5 attrs so they have a lower
                # sell threshold: average * GEM_KEEP_RATIO * BLACK_GEM_ATTR_RATIO
                if (
                    item.gem_value
                    < average_gem_single_attr_value
                    * BLACK_GEM_SELL_RATIO
                    * BLACK_GEM_ATTR_RATIO
                ):
                    return slot
        return None

    def get_worst_gem_by_attr(self, gem_attr: GemAttr) -> InventorySlot | None:
        """Return the backpack gem with the lowest power matching gem_attr."""
        worst: InventorySlot | None = None
        worst_power = float("inf")
        for slot in self.get_gems():
            item = slot.item
            if not item or item.gem_attr != gem_attr or item.gem_value is None:
                continue
            if item.gem_value < worst_power:
                worst = slot
                worst_power = item.gem_value
        return worst

    def get_item_with_low_value_gem(
        self, average_gem_single_attr_value: float
    ) -> InventorySlot | None:
        for slot in self.get_items_with_gems():
            item = slot.item
            if not item or not item.inserted_gem:
                continue
            gem = item.inserted_gem
            if gem.attr == GemAttr.LEGENDARY:
                continue
            # Get rid of items with single-attr gems
            if gem.attr != GemAttr.BLACK:
                return slot
            # Keep item with the black gem if gem is almost average
            if (
                gem.power
                < average_gem_single_attr_value
                * BLACK_GEM_SELL_RATIO
                * BLACK_GEM_ATTR_RATIO
            ):
                return slot
        return None

    def get_item_with_extractable_gem(
        self,
        average_gem_single_attr_value: float,
        keep_gem_attrs: set[GemAttr],
    ) -> InventorySlot | None:
        rescue_attrs = keep_gem_attrs - {GemAttr.LEGENDARY, GemAttr.BLACK}
        for slot in self.get_items_with_gems():
            item = slot.item
            if not item or not item.inserted_gem:
                continue
            gem = item.inserted_gem
            # Extract legendary if per-attr power justifies it (2 attrs: main + CON)
            if gem.attr == GemAttr.LEGENDARY:
                if (
                    gem.power
                    and gem.power
                    >= average_gem_single_attr_value * LEGENDARY_GEM_ATTR_RATIO
                ):
                    return slot
                continue
            # Extract valuable main-attr/CON gems above threshold
            if gem.attr in rescue_attrs:
                if (
                    gem.power
                    and gem.power >= average_gem_single_attr_value * GEM_KEEP_RATIO
                ):
                    return slot
                continue
            # For black gems the threshold is lower (contributes to all 5 attrs)
            if gem.attr == GemAttr.BLACK:
                if (
                    gem.power
                    and gem.power
                    >= average_gem_single_attr_value
                    * GEM_KEEP_RATIO
                    * BLACK_GEM_ATTR_RATIO
                ):
                    return slot
        return None

    def get_item_with_rescuable_gem(
        self,
        keep_gem_attrs: set[GemAttr],
        profiles: list[ComparisonProfile],
    ) -> InventorySlot | None:
        """Find an item with a socketed gem worth extracting before relaxed sell.

        Only considers gems in keep_gem_attrs minus LEGENDARY/BLACK (those
        are already protected by the precious_gems filter in later stages).
        Returns the item only if the gem would be an upgrade via scoring.
        """
        rescue_attrs = keep_gem_attrs - {GemAttr.LEGENDARY, GemAttr.BLACK}
        if not rescue_attrs:
            return None

        equipped_data = load_equipped_data(self.session, profiles)

        for slot in self.get_items_with_gems():
            item = slot.item
            if not item or not item.inserted_gem:
                continue
            gem = item.inserted_gem
            if gem.attr not in rescue_attrs:
                continue
            _, _, score = score_gem_best_placement(gem.attr, gem.power, equipped_data)
            if score > 0:
                return slot
        return None

    def get_item_to_dismantle(
        self, black_gem_attr_threshold: float
    ) -> InventorySlot | None:
        """Find best equippable item to dismantle, skipping legendary-gem items."""
        candidates = [
            slot
            for slot in self.get_equippable_items()
            if slot.item
            and not slot.item.has_legendary_gem
            and not (
                slot.item.inserted_gem
                and slot.item.inserted_gem.attr == GemAttr.BLACK
                and slot.item.inserted_gem.power
                >= black_gem_attr_threshold * BLACK_GEM_SELL_RATIO
            )
        ]
        return (
            max(candidates, key=lambda s: s.item.rarity if s.item else 0)
            if candidates
            else None
        )

    def get_item_to_sacrifice(
        self, gem_protected_attrs: set[GemAttr]
    ) -> InventorySlot | None:
        """Find an item to sacrifice in the toilet."""
        if gem := self.get_sellable_gem(gem_protected_attrs):
            return gem
        return next(
            (
                s
                for s in self.get_equippable_items()
                if s.item and not s.item.has_legendary_gem
            ),
            None,
        )

    # --- Actions ---

    async def move_item_async(self, from_wire: str, to_wire: str, item: Item) -> None:
        """Async move item from one slot to another."""
        params = f"{from_wire}/{to_wire}/{item.item_type}/{item.model}/{item.cost.silver}/{item.cost.mushrooms}"
        try:
            await self.session.request_and_update_async("PlayerItemMove", params)
        except APIError as exc:
            raise MoveError(str(exc)) from exc

    async def use_potion_async(self, wire: str, item: Item) -> None:
        """Async drink a potion from inventory."""
        await self.move_item_async(wire, "1/0", item)

    async def sell_item_at_slot_async(self, slot: InventorySlot, stage: str) -> bool:
        if not slot.item:
            return False
        logger = get_main_logger()
        if slot.item.is_potion:
            try:
                await self.use_potion_async(slot.wire, slot.item)
                logger.info(f"Inventory: Drank potion, stage {stage}")
                logger.info(f"  Item: {slot.item.format()}")
                return True
            except MoveError:
                pass
        try:
            await self.move_item_async(
                slot.wire, f"{ShopType.WEAPON_SHOP}/1", slot.item
            )
            logger.info(f"Inventory: Sold item, stage {stage}")
            logger.info(f"  Item: {slot.item.format()}")
            return True
        except MoveError as exc:
            logger.warning(f"Inventory: sell failed, stage {stage}: {exc}")
            return False

    async def drink_potion_async(
        self,
        main_attr: Attribute,
        active_sizes: dict[PotionAttributeType, PotionSize | None],
    ) -> None:
        """Drink the first drinkable potion in the backpack."""
        if not (potions := self.get_drinkable_potions(main_attr, active_sizes)):
            return
        potion = potions[0]
        logger = get_main_logger()
        try:
            await self.use_potion_async(potion.wire, potion.item)
            logger.info(f"Elixir: drank {potion.item.format()}")
        except MoveError as exc:
            logger.warning(f"Elixir: drink {potion.item.format()} failed: {exc}")

    async def ensure_free_slot_async(
        self,
        *,
        main_potion_attr: PotionAttributeType,
        max_potion_size: PotionSize,
        smith: Smith | None,
        toilet: Toilet | None,
        keep_gem_attrs: set[GemAttr],
        average_single_attr_gem: float,
        profiles: list[ComparisonProfile],
        character: Character,
    ) -> bool:
        """Try to free one backpack slot via a priority chain.

        Returns True if a slot was freed (or extraction happened), False if
        nothing could be done. The caller is responsible for pre-requisites
        (equip best items/gems) and post-extraction follow-up (poll + re-socket).
        """
        logger = get_main_logger()

        all_protected = keep_gem_attrs | {GemAttr.LEGENDARY, GemAttr.BLACK}
        precious_gems = {GemAttr.LEGENDARY, GemAttr.BLACK}
        potion_attrs_to_keep = {main_potion_attr, PotionAttributeType.CONSTITUTION}

        # --- 1. Dismantle equippable items, skip items with valuable gems ---
        logger.debug("Inventory: entering [1] dismantle")
        if smith and smith.can_dismantle:
            slot = self.get_item_to_dismantle(
                BLACK_GEM_ATTR_RATIO * average_single_attr_gem
            )
            if slot and slot.item:
                item = slot.item
                if await smith.dismantle_slot_async(
                    slot.wire,
                    item.item_type,
                    item.model,
                    item.cost.silver,
                    item.cost.mushrooms,
                ):
                    logger.info("Inventory: Dismantled item, stage [1]")
                    logger.info(f"  Item: {item.format()}")
                    return True
        logger.debug("Inventory: passed [1]")

        # --- 2. Sacrifice unprotected gems into toilet ---
        logger.debug("Inventory: entering [2] sacrifice")
        if toilet and toilet.can_sacrifice:
            slot = self.get_sellable_gem(keep_gem_attrs)
            if slot and slot.item:
                if await toilet.sacrifice_slot_async(slot.wire, slot.item.format()):
                    return True
        logger.debug("Inventory: passed [2]")

        # --- 3. Sell off-attr potions ---
        logger.debug("Inventory: entering [3] off-attr potion")
        slot = self.get_off_attr_potion(potion_attrs_to_keep)
        if slot and await self.sell_item_at_slot_async(slot, "[3]"):
            return True
        logger.debug("Inventory: passed [3]")

        # --- 4. Sell main/CON potions below max unlocked size ---
        logger.debug("Inventory: entering [4] sub-max potion")
        slot = self.get_sub_max_potion(potion_attrs_to_keep, max_potion_size)
        if slot and await self.sell_item_at_slot_async(slot, "[4]"):
            return True
        logger.debug("Inventory: passed [4]")

        # --- 5. Sell gems not in protected set (main/CON/legendary/black) ---
        logger.debug("Inventory: entering [5] unprotected gem")
        slot = self.get_sellable_gem(all_protected)
        if slot and await self.sell_item_at_slot_async(slot, "[5]"):
            return True
        logger.debug("Inventory: passed [5]")

        # --- 6. Sell normal items, skip items with any protected gem ---
        logger.debug("Inventory: entering [6] normal item")
        slot = self.get_sellable_item(Rarity.NORMAL, all_protected)
        if slot and await self.sell_item_at_slot_async(slot, "[6]"):
            return True
        logger.debug("Inventory: passed [6]")

        # --- 7. Extract main-attr/CON gem from item if it would be an upgrade ---
        logger.debug("Inventory: entering [7] rescue gem extraction")
        if smith:
            slot = self.get_item_with_rescuable_gem(keep_gem_attrs, profiles)
            if slot and slot.item:
                item = slot.item
                success = await smith.extract_gem_from_slot_async(
                    slot.wire,
                    item.item_type,
                    item.model,
                    item.cost.silver,
                    item.cost.mushrooms,
                )
                if success:
                    logger.info("Inventory: Extracted gem, stage [7]")
                    logger.info(f"  Item: {item.format()}")
                    logger.info(f"  Gem:  {item.inserted_gem.format()}")  # type: ignore
                    raise GemExtractedAlert()
                logger.warning(f"Inventory: [7] extract failed for {item.format()}")
        logger.debug("Inventory: passed [7]")

        # --- 8. Sell normal items, skip items with legendary/black gems only ---
        logger.debug("Inventory: entering [8] normal item (relaxed)")
        slot = self.get_sellable_item(Rarity.NORMAL, precious_gems)
        if slot and await self.sell_item_at_slot_async(slot, "[8]"):
            return True
        logger.debug("Inventory: passed [8]")

        # --- 9. Sell low-value main/CON gems below average threshold ---
        logger.debug("Inventory: entering [9] low-value attr gem")
        slot = self.get_low_value_gem(
            average_single_attr_gem, restrict_to_attrs=keep_gem_attrs
        )
        if slot and await self.sell_item_at_slot_async(slot, "[9]"):
            return True
        logger.debug("Inventory: passed [9]")

        # --- 10. Sell epic/legendary items, progressively relaxing gem protection ---
        logger.debug("Inventory: entering [10] epic/legendary items")
        for rarity in SELL_RARITY_ORDER:
            slot = self.get_sellable_item(rarity, all_protected)
            if slot and await self.sell_item_at_slot_async(slot, "[10]"):
                return True

            slot = self.get_sellable_item(rarity, precious_gems)
            if slot and await self.sell_item_at_slot_async(slot, "[10]"):
                return True
        logger.debug("Inventory: passed [10]")

        # --- 11. Sell gems keeping only legendary/black ---
        logger.debug("Inventory: entering [11] gem (relaxed)")
        slot = self.get_sellable_gem(precious_gems)
        if slot and await self.sell_item_at_slot_async(slot, "[11]"):
            return True
        logger.debug("Inventory: passed [11]")

        # --- 12. Dismantle or sell items with low-value black gems ---
        logger.debug("Inventory: entering [12] low-value gem item")
        slot = self.get_item_with_low_value_gem(average_single_attr_gem)
        if slot and slot.item:
            item = slot.item
            if smith and smith.can_dismantle:
                logger.debug("Inventory: [12] dismantling")
                if await smith.dismantle_slot_async(
                    slot.wire,
                    item.item_type,
                    item.model,
                    item.cost.silver,
                    item.cost.mushrooms,
                ):
                    logger.info("Inventory: Dismantled item, stage [12]")
                    logger.info(f"  Item: {item.format()}")
                    return True
            else:
                logger.debug("Inventory: [12] selling")
                if await self.sell_item_at_slot_async(slot, "[12]"):
                    return True
        logger.debug("Inventory: passed [12]")

        # --- 13. Sell low-value black gems directly ---
        logger.debug("Inventory: entering [13] low-value gem")
        slot = self.get_low_value_gem(average_single_attr_gem, set())
        if slot and await self.sell_item_at_slot_async(slot, "[13]"):
            return True
        logger.debug("Inventory: passed [13]")

        # --- 14. Extract legendary or valuable gem from item (triggers re-socket cycle) ---
        logger.debug("Inventory: entering [14] extract gem")
        if smith:
            slot = self.get_item_with_extractable_gem(
                average_single_attr_gem, keep_gem_attrs
            )
            if slot and slot.item:
                item = slot.item
                success = await smith.extract_gem_from_slot_async(
                    slot.wire,
                    item.item_type,
                    item.model,
                    item.cost.silver,
                    item.cost.mushrooms,
                )
                if success:
                    logger.info("Inventory: Extracted gem, stage [14]")
                    logger.info(f"  Item: {item.format()}")
                    logger.info(f"  Gem:  {item.inserted_gem.format()}")  # type: ignore
                    raise GemExtractedAlert()
        logger.debug(f"Inventory: passed [14] {self.session.player_name}")

        # --- 15. Force-socket or sell worst black gem ---
        logger.debug("Inventory: entering [15] worst black gem")
        slot = self.get_worst_gem_by_attr(GemAttr.BLACK)
        if slot:
            if await self.force_socket_gem_async(slot, profiles):
                return True
            if await self.sell_item_at_slot_async(slot, "[15]"):
                return True
        logger.debug("Inventory: passed [15]")

        # --- 16. Force-socket or sell worst legendary gem ---
        logger.debug("Inventory: entering [16] worst legendary gem")
        slot = self.get_worst_gem_by_attr(GemAttr.LEGENDARY)
        if slot:
            if await self.force_socket_gem_async(slot, profiles):
                return True
            if await self.sell_item_at_slot_async(slot, "[16]"):
                return True
        logger.debug("Inventory: passed [16]")

        # --- 17. Sell any remaining equippable item ---
        logger.debug("Inventory: entering [17] any equippable item")
        if items := self.get_equippable_items():
            if await self.sell_item_at_slot_async(items[0], "[17]"):
                return True
        logger.debug("Inventory: passed [17]")

        # --- 18. Last resort: drink a main/CON potion to free a slot ---
        logger.debug("Inventory: entering [18] drink potion")
        freed = await self.drink_potion_to_free_slot_async(character, main_potion_attr)
        if freed:
            return True
        logger.debug("Inventory: passed [18]")

        raise InventoryStuckError("could not free a backpack slot")

    async def drink_potion_to_free_slot_async(
        self,
        character: Character,
        main_potion_attr: PotionAttributeType,
    ) -> bool:
        """Try to drink a backpack potion to free a slot.

        Ensures a character potion slot is available (killing a useless one
        if needed), then drinks the first main/CON potion from backpack.
        """
        logger = get_main_logger()
        keep_attrs = {main_potion_attr, PotionAttributeType.CONSTITUTION}
        drinkable = [
            p
            for p in self.get_potions()
            if p.potion.attr in keep_attrs and p.item and p.item.model != WINGS_MODEL_ID
        ]
        if not drinkable:
            return False

        if not await character.ensure_potion_slot_async(main_potion_attr):
            return False

        potion = drinkable[0]
        try:
            await self.use_potion_async(potion.wire, potion.item)
            logger.info(f"Inventory: [18] drank {potion.item.format()}")
            return True
        except MoveError as exc:
            logger.warning(f"Inventory: [18] drink failed: {exc}")
            return False

    async def equip_best_item_async(
        self,
        level: int,
        profiles: list[ComparisonProfile],
        skip_wires: set[str] | None = None,
    ) -> str | None:
        """Scan the entire backpack for the single best equipment upgrade and equip it.

        How it works:
        1. Load currently equipped items for all profiles (main char + companions).
        2. Score every equippable backpack item against every profile.
           An item only counts as an upgrade if it beats the IMPROVEMENT_RATIO threshold.
        3. Track the item with the highest positive score across all profiles.
        4. If a winner is found, move it from backpack to the equipment slot.
           The previously equipped item is displaced back into the backpack.

        Args:
            skip_wires: Equipment wire positions to exclude from consideration.
                Used by the caller to prevent A↔B oscillation where two items
                of similar score endlessly swap the same slot.

        Returns the equip wire position if an item was equipped, None otherwise.

        This method equips ONE item per call. To equip all possible upgrades,
        call it in a loop until it returns None — each call re-reads the
        backpack so displaced items are scored in subsequent iterations.
        """

        logger = get_main_logger()
        equipped_data = load_equipped_data(self.session, profiles)

        # Collect candidates, skipping oscillating swaps.
        candidates: list[
            tuple[InventorySlot, ComparisonProfile, str, Item | None, float]
        ] = []

        for slot in self.get_equippable_items():
            item = slot.item
            if not item:
                continue

            winner, score = score_item_best(item, level, equipped_data)
            if winner is not None and score > 0:
                candidate_slot = ITEM_TYPE_TO_EQUIP_SLOT[item.item_type]
                candidate_wire = get_equip_wire_position(candidate_slot, winner)
                if skip_wires and candidate_wire in skip_wires:
                    continue
                entry = next(e for e in equipped_data if e.profile is winner)
                current_item = entry.items[candidate_slot]
                if _would_oscillate(item, current_item, level, entry):
                    logger.debug(
                        f"Equip: skipping oscillating swap {item.item_type.name} on "
                        f"{winner.companion.display_name if winner.companion else self.session.player_name}"
                    )
                    continue
                candidates.append((slot, winner, candidate_wire, current_item, score))

        if not candidates:
            return None

        # Pick the highest-scoring candidate.
        best_slot, best_profile, equip_wire, old_item, _ = max(
            candidates, key=lambda c: c[4]
        )
        item = best_slot.item
        if not item:
            return None

        try:
            await self.move_item_async(best_slot.wire, equip_wire, item)

            display_name = (
                best_profile.companion.display_name
                if best_profile.companion
                else self.session.player_name
            )
            item_class = (
                item.char_class.name.lower()
                if item.char_class is not None
                else "everyone"
            )
            logger.info(
                f"Equip: equipped {item.item_type.name} for {item_class}"
                f" to {display_name}"
            )
            logger.info(f"\told: {old_item.format() if old_item else None}")
            logger.info(f"\tnew: {item.format()}")

            return equip_wire
        except MoveError as exc:
            logger.warning(f"Equip: failed: {exc}")
            return None

    async def _socket_gem_async(
        self,
        slot: InventorySlot,
        profile: ComparisonProfile,
        equip_slot: EquipmentSlot,
    ) -> bool:
        """Move a gem from backpack into an equipment socket.

        Handles the wire move, old-gem lookup, and logging.
        Returns True if the gem was socketed, False on failure.
        """
        gem = slot.item
        if not gem:
            return False

        logger = get_main_logger()
        equip_wire = get_equip_wire_position(equip_slot, profile)
        equipped_item = profile_equipped_items(self.session, profile)[equip_slot]
        old_gem = equipped_item.inserted_gem if equipped_item else None

        try:
            await self.move_item_async(slot.wire, equip_wire, gem)
        except MoveError as exc:
            logger.warning(f"Gem: socket failed: {exc}")
            return False

        display_name = (
            profile.companion.display_name
            if profile.companion
            else self.session.player_name
        )
        logger.info(f"Gem: socketed in {equip_slot.name} for {display_name}")
        logger.info(f"\told: {old_gem.format() if old_gem else None}")
        logger.info(f"\tnew: {gem.format()}")
        return True

    async def socket_best_gem_async(
        self,
        profiles: list[ComparisonProfile],
    ) -> bool:
        """Scan backpack gems and socket the single best one into equipment.

        For each gem, finds the (profile, equipment slot) combination that
        benefits most. Empty sockets are pure gain; filled sockets require
        the new gem to be GEM_IMPROVEMENT_RATIO better than the existing one.

        Call in a loop until it returns False to socket all beneficial gems.
        """
        equipped_data = load_equipped_data(self.session, profiles)
        best_inv_slot: InventorySlot | None = None
        best_profile: ComparisonProfile | None = None
        best_equip_slot: EquipmentSlot | None = None
        best_score = 0.0

        for gem_slot in self.get_gems():
            gem = gem_slot.item
            if not gem or gem.gem_attr is None or gem.gem_value is None:
                continue

            profile, equip_slot, score = score_gem_best_placement(
                gem.gem_attr,
                gem.gem_value,
                equipped_data,
            )
            if profile and equip_slot and score > best_score:
                best_inv_slot = gem_slot
                best_profile = profile
                best_equip_slot = equip_slot
                best_score = score

        if best_inv_slot is None or best_profile is None or best_equip_slot is None:
            return False

        return await self._socket_gem_async(
            best_inv_slot, best_profile, best_equip_slot
        )

    async def force_socket_gem_async(
        self,
        slot: InventorySlot,
        profiles: list[ComparisonProfile],
    ) -> bool:
        """Try to force-socket the given gem into equipment.

        Bypasses GEM_IMPROVEMENT_RATIO — any positive score improvement counts.
        Socketing destroys the old gem, directly freeing the backpack slot.
        Returns True if the gem was socketed (slot freed), False otherwise.
        """
        gem = slot.item
        if not gem or gem.gem_attr is None or gem.gem_value is None:
            return False

        equipped_data = load_equipped_data(self.session, profiles)
        profile, equip_slot, score = score_gem_best_placement(
            gem.gem_attr,
            gem.gem_value,
            equipped_data,
            improvement_ratio=1.0,
        )
        if not profile or not equip_slot or score <= 0:
            return False

        return await self._socket_gem_async(slot, profile, equip_slot)

    # --- Display ---

    def show(self, detailed: bool = False) -> None:
        """Display inventory contents."""
        slots, total_slots = self.get_backpack()
        print(f"\n=== Inventory ({total_slots} slots) ===\n")

        for index, slot in enumerate(slots):
            if not slot.item:
                print(f"  Slot {index + 1:2d}: (empty)")
            i = slot.index
            if i < MAIN_BACKPACK_SLOT_COUNT:
                label = f"Main {i + 1} ({slot.wire})"
            else:
                label = f"Ext {i - MAIN_BACKPACK_SLOT_COUNT + 1} ({slot.wire})"

            if detailed:
                result = format_full_item(slot.item.raw, label)  # type: ignore
                if result:
                    print(result)
                    print()
            else:
                print(f"  Slot {i + 1:2d} ({slot.wire}): {slot.item.format()}")  # type: ignore

        print(f"\n--- {len([s for s in slots if s.item])}/{total_slots} slots used ---")
