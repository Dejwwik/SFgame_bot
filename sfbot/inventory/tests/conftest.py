from unittest.mock import MagicMock

from sfbot.constants import (
    Cost,
    GemAttr,
    GemSlot,
    ItemType,
    PotionAttributeType,
    PotionSize,
    Rarity,
)
from sfbot.inventory.inventory import (
    Inventory,
    InventorySlot,
    inventory_index_to_wire,
)
from sfbot.items import InsertedGem, Item


def make_item(
    item_type: ItemType = ItemType.BREASTPLATE,
    rarity: Rarity = Rarity.NORMAL,
    washed: bool = True,
    gem_slot: GemSlot = GemSlot.NONE,
    inserted_gem: InsertedGem | None = None,
    silver: int = 100,
    mushrooms: int = 0,
) -> Item:
    return Item(
        item_type=item_type,
        char_class=None,
        model=1,
        model_id=1,
        rarity=rarity,
        enchantment=None,
        attributes=[],
        runes=[],
        cost=Cost(silver=silver, mushrooms=mushrooms),
        upgrades=0,
        gem_slot=gem_slot,
        quality=0,
        washed=washed,
        raw=[0] * 19,
        inserted_gem=inserted_gem,
    )


def make_gem(
    gem_attr: GemAttr = GemAttr.STRENGTH,
    gem_value: int = 100,
) -> Item:
    item = Item(
        item_type=ItemType.GEM,
        char_class=None,
        model=10 + gem_attr.value,
        model_id=10 + gem_attr.value,
        rarity=Rarity.NORMAL,
        enchantment=None,
        attributes=[],
        runes=[],
        cost=Cost(silver=0, mushrooms=0),
        upgrades=0,
        gem_slot=GemSlot.NONE,
        quality=0,
        washed=False,
        raw=[0] * 19,
    )
    item.gem_attr = gem_attr
    item.gem_value = gem_value
    return item


def make_potion(
    attr: PotionAttributeType = PotionAttributeType.STRENGTH,
    size: PotionSize = PotionSize.SMALL,
) -> Item:
    model = (size.value - 1) * 5 + attr.value + 1
    item = Item(
        item_type=ItemType.POTION,
        char_class=None,
        model=model,
        model_id=model,
        rarity=Rarity.NORMAL,
        enchantment=None,
        attributes=[],
        runes=[],
        cost=Cost(silver=0, mushrooms=0),
        upgrades=0,
        gem_slot=GemSlot.NONE,
        quality=0,
        washed=False,
        raw=[0] * 19,
    )
    item.potion_attr = attr
    item.potion_size = size
    return item


def make_gemmed_item(
    attr: GemAttr = GemAttr.STRENGTH,
    power: int = 100,
    rarity: Rarity = Rarity.NORMAL,
) -> Item:
    return make_item(
        rarity=rarity,
        inserted_gem=InsertedGem(attr=attr, power=power),
        gem_slot=GemSlot.FILLED,
    )


def slot(index: int, item: Item | None) -> InventorySlot:
    return InventorySlot(index=index, wire=inventory_index_to_wire(index), item=item)


def make_inventory(items: list[Item | None]) -> Inventory:
    """Create an Inventory backed by a mock session with the given items."""
    session = MagicMock()
    inv = Inventory(session)
    slots = [slot(i, item) for i, item in enumerate(items)]
    total = len(items)
    inv.get_backpack = MagicMock(return_value=(slots, total))  # type: ignore
    return inv
