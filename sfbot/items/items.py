from dataclasses import dataclass
from functools import total_ordering

from sfbot.constants import (
    ITEM_FIELD_ATTR_TYPE_0,
    ITEM_FIELD_ATTR_VALUE_0,
    ITEM_FIELD_COUNT,
    ITEM_FIELD_ENCHANTMENT,
    ITEM_FIELD_GEM_POWER,
    ITEM_FIELD_GEM_SLOT,
    ITEM_FIELD_MAX_DAMAGE,
    ITEM_FIELD_MIN_DAMAGE,
    ITEM_FIELD_MODEL,
    ITEM_FIELD_MUSHROOM_PRICE,
    ITEM_FIELD_PRICE,
    ITEM_FIELD_QUALITY,
    ITEM_FIELD_TYPE,
    ITEM_FIELD_UPGRADES,
    ITEM_FIELD_WASHED,
    MODEL_CLASS_DIVISOR,
    RARITY_EPIC_THRESHOLD,
    RARITY_LEGENDARY_THRESHOLD,
    RUNE_TYPE_THRESHOLD,
    WINGS_MODEL_ID,
    Attribute,
    CharClass,
    Cost,
    Enchantment,
    GemAttr,
    GemSlot,
    ItemAttributeType,
    ItemType,
    PotionAttributeType,
    PotionSize,
    Rarity,
    RuneType,
)

GEM_SLOTS = {0: GemSlot.NONE, 1: GemSlot.EMPTY}

# Item types that are class-restricted (armor + weapons).
# Accessories (amulet, ring, talisman) are always universal.
CLASS_ITEM_TYPES: frozenset[ItemType] = frozenset(
    {
        ItemType.WEAPON,
        ItemType.SHIELD,
        ItemType.BREASTPLATE,
        ItemType.FOOTWEAR,
        ItemType.GLOVES,
        ItemType.HAT,
        ItemType.BELT,
    }
)

ATTR_SLOT_COUNT = 3


def _item_rarity(model_id: int) -> Rarity:
    """Determine rarity from the model_id (model % MODEL_CLASS_DIVISOR)."""
    mid = model_id % MODEL_CLASS_DIVISOR
    if mid >= RARITY_LEGENDARY_THRESHOLD:
        return Rarity.LEGENDARY
    if mid >= RARITY_EPIC_THRESHOLD:
        return Rarity.EPIC
    return Rarity.NORMAL


@dataclass(slots=True)
class ItemAttribute:
    attribute_type: ItemAttributeType
    value: int


@dataclass(slots=True)
class ItemRune:
    rune_type: RuneType
    value: int


@dataclass(slots=True)
class InsertedGem:
    """A gem socketed in an item."""

    attr: GemAttr
    power: int

    def format(self) -> str:
        return f"{self.attr.name} {self.power}"


@total_ordering
@dataclass(slots=True)
class Item:
    """Parsed game item."""

    item_type: ItemType
    char_class: CharClass | None
    model: int  # full model_info (class_id * 1000 + model_id)
    model_id: int  # model_info % 1000
    rarity: Rarity
    enchantment: Enchantment | None
    attributes: list[ItemAttribute]
    runes: list[ItemRune]
    cost: Cost
    upgrades: int
    gem_slot: GemSlot
    quality: int
    washed: bool
    raw: list[int]

    # Type-specific optional fields
    potion_attr: PotionAttributeType | None = None
    potion_size: PotionSize | None = None
    min_dmg: int | None = None
    max_dmg: int | None = None
    block_chance: int | None = None
    armor: int | None = None

    # If the item contains a gem in socket.
    inserted_gem: InsertedGem | None = None

    # If the item is itself a GEM
    gem_attr: GemAttr | None = None
    gem_value: int | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Item):
            return NotImplemented
        return self.rarity == other.rarity and self.attr_power == other.attr_power

    def __gt__(self, other: "Item") -> bool:
        if self.rarity == other.rarity:
            return self.attr_power > other.attr_power
        if self.rarity == Rarity.LEGENDARY:
            return True
        if other.rarity == Rarity.LEGENDARY:
            return False
        if self.rarity == Rarity.EPIC:
            return True
        return False

    def __lt__(self, other: "Item") -> bool:
        if self.rarity == other.rarity:
            return self.attr_power < other.attr_power
        if self.rarity == Rarity.LEGENDARY:
            return False
        if other.rarity == Rarity.LEGENDARY:
            return True
        if self.rarity == Rarity.EPIC:
            return False
        return True

    @property
    def is_potion(self) -> bool:
        return self.item_type == ItemType.POTION

    @property
    def is_gem(self) -> bool:
        return self.item_type == ItemType.GEM

    @property
    def is_weapon(self) -> bool:
        return self.item_type == ItemType.WEAPON

    @property
    def is_shield(self) -> bool:
        return self.item_type == ItemType.SHIELD

    @property
    def has_legendary_gem(self) -> bool:
        return (
            self.inserted_gem is not None
            and self.inserted_gem.attr == GemAttr.LEGENDARY
        )

    @property
    def avg_dmg(self) -> float:
        if self.min_dmg is not None and self.max_dmg is not None:
            return (self.min_dmg + self.max_dmg) / 2
        raise ValueError("Item does not have damage values")

    @property
    def attr_power(self) -> int:
        return sum(a.value for a in self.attributes)

    def format(self) -> str:
        return format_item(self)


def format_item(item: Item) -> str:
    """Format a parsed Item into a one-line display string."""
    if item.is_potion:
        if item.potion_attr is not None and item.potion_size is not None:
            parts = [
                f"{item.potion_attr.name} {item.potion_size.name.capitalize()} Potion"
            ]
        elif item.model == WINGS_MODEL_ID:
            parts = ["Eternal Life (Wings/HP)"]
        else:
            parts = [f"Potion(model={item.model})"]
    else:
        class_label = (
            item.gem_attr.name
            if item.gem_attr is not None
            else item.char_class.name
            if item.char_class is not None
            else ""
        )
        parts = [
            f"{item.item_type.name} ({class_label})"
            if class_label
            else item.item_type.name
        ]
    parts[0] += f" [{item.rarity}]"
    if item.min_dmg is not None:
        parts.append(f"Dmg {item.min_dmg}-{item.max_dmg}")
    elif item.block_chance is not None:
        parts.append(f"Block {item.block_chance}%")
    elif item.gem_value is not None:
        parts.append(f"Power {item.gem_value}")
    if item.attributes:
        attr_str = ", ".join(
            f"{a.attribute_type.name} {a.value}" for a in item.attributes
        )
        parts.append(f"[{attr_str}]")
        if item.upgrades > 0:
            from sfbot.utils import strip_upgrades

            base_str = ", ".join(
                f"{a.attribute_type.name} {strip_upgrades(a.value, item.upgrades)}"
                for a in item.attributes
            )
            parts.append(f"(base: [{base_str}] +{item.upgrades})")
    if item.inserted_gem:
        parts.append(f"Gem: {item.inserted_gem.format()}")
    elif item.gem_slot == GemSlot.EMPTY:
        parts.append("Gem: Empty")
    return " | ".join(parts)


def parse_item(fields: list[int]) -> Item | None:
    """Parse 19 item fields into an Item dataclass. Returns None if empty."""
    # type_id == 0 means the slot is empty (no item)
    if fields[ITEM_FIELD_TYPE] == 0:
        return None

    raw_id = fields[ITEM_FIELD_TYPE] & 0xFF
    model_info = fields[ITEM_FIELD_MODEL] & 0xFFFF
    class_id = model_info // MODEL_CLASS_DIVISOR
    model_id = model_info % MODEL_CLASS_DIVISOR

    # Potions and gems use the attribute fields for type-specific data, not attrs
    attrs = []
    runes = []
    item_type = ItemType(raw_id)

    # All items which have states(weapon, shield, armor, accessories)
    if ItemType.WEAPON <= item_type <= ItemType.TALISMAN:
        for i in range(ATTR_SLOT_COUNT):
            attr_type = fields[ITEM_FIELD_ATTR_TYPE_0 + i]
            attr_value = fields[ITEM_FIELD_ATTR_VALUE_0 + i]
            if not attr_type and not attr_value:
                continue
            if attr_type >= RUNE_TYPE_THRESHOLD:
                runes.append(ItemRune(RuneType(attr_type), attr_value))
            else:
                attrs.append(ItemAttribute(ItemAttributeType(attr_type), attr_value))

    enchant_id = fields[ITEM_FIELD_ENCHANTMENT]
    sell_raw = fields[ITEM_FIELD_PRICE]

    # Gem socket: 0 = no socket, 1 = empty socket, >1 = gem inserted
    gem_slot_raw = fields[ITEM_FIELD_GEM_SLOT]
    gem_slot = GEM_SLOTS.get(gem_slot_raw, GemSlot.FILLED)
    inserted_gem: InsertedGem | None = None
    if gem_slot == GemSlot.FILLED and ItemType.WEAPON <= item_type <= ItemType.TALISMAN:
        inserted_gem = InsertedGem(
            attr=GemAttr(gem_slot_raw % 10), power=fields[ITEM_FIELD_GEM_POWER]
        )

    # Class is derived from model_info // 1000:
    #   0 = Warrior, 1 = Mage, 2 = Scout, ...
    # Only armor/weapons are class-restricted. Accessories (amulet, ring,
    # talisman) are always universal (char_class=None).
    # IMPORTANT: Warrior = 0, which is falsy in Python. Using `if class_id`
    # would incorrectly treat all Warrior items as classless. Instead we
    # check whether the item type is class-restricted.
    char_class = CharClass(class_id) if item_type in CLASS_ITEM_TYPES else None

    item = Item(
        item_type=item_type,
        char_class=char_class,
        model=model_info,
        model_id=model_id,
        rarity=_item_rarity(model_info),
        enchantment=Enchantment(enchant_id) if enchant_id else None,
        attributes=attrs,
        runes=runes,
        cost=Cost(silver=sell_raw, mushrooms=fields[ITEM_FIELD_MUSHROOM_PRICE]),
        upgrades=fields[ITEM_FIELD_UPGRADES],
        gem_slot=gem_slot,
        quality=fields[ITEM_FIELD_QUALITY],
        washed=fields[ITEM_FIELD_WASHED] != 0,
        raw=list(fields[:ITEM_FIELD_COUNT]),
        inserted_gem=inserted_gem,
    )

    match item.item_type:
        case ItemType.POTION:
            if model_info != WINGS_MODEL_ID:
                item.potion_attr = PotionAttributeType(model_info % 5)
                item.potion_size = PotionSize((model_info - 1) // 5 + 1)
            else:
                item.potion_attr = PotionAttributeType.HP
                item.potion_size = None
            item.char_class = None
        case ItemType.GEM:
            item.gem_attr = GemAttr(model_info % 10)
            item.gem_value = fields[ITEM_FIELD_GEM_POWER]
            item.char_class = None
        case ItemType.WEAPON:
            item.min_dmg = fields[ITEM_FIELD_MIN_DAMAGE]
            item.max_dmg = fields[ITEM_FIELD_MAX_DAMAGE]
        case ItemType.SHIELD:
            item.block_chance = fields[ITEM_FIELD_MIN_DAMAGE]
        case (
            ItemType.BREASTPLATE
            | ItemType.FOOTWEAR
            | ItemType.GLOVES
            | ItemType.HAT
            | ItemType.BELT
            | ItemType.AMULET
            | ItemType.RING
            | ItemType.TALISMAN
        ):
            item.armor = fields[ITEM_FIELD_MIN_DAMAGE]

    return item


def format_full_item(fields: list[int], slot_label: str) -> str | None:
    """Format an item with full details including dismantle values."""
    raw_id = fields[ITEM_FIELD_TYPE] & 0xFF
    if raw_id == 0:
        return None

    tp = ItemType(raw_id).name
    model_info = fields[ITEM_FIELD_MODEL] & 0xFFFF
    class_id = model_info // MODEL_CLASS_DIVISOR
    model_id = model_info % MODEL_CLASS_DIVISOR

    cls = CharClass(class_id).name if ItemType(raw_id) in CLASS_ITEM_TYPES else ""
    enchant_id = fields[ITEM_FIELD_ENCHANTMENT]
    enchant = Enchantment(enchant_id).name if enchant_id else ""
    gem_slot = fields[ITEM_FIELD_GEM_SLOT]
    gem_str = GEM_SLOTS.get(
        gem_slot, f"Gem(id={gem_slot}, pwr={fields[ITEM_FIELD_GEM_POWER]})"
    )
    silver = fields[ITEM_FIELD_PRICE]
    mush = fields[ITEM_FIELD_MUSHROOM_PRICE]
    upgrades = fields[ITEM_FIELD_UPGRADES]
    quality = fields[ITEM_FIELD_QUALITY]
    washed = "Yes" if fields[ITEM_FIELD_WASHED] else "No"

    rarity = Rarity.NORMAL
    if model_id >= RARITY_LEGENDARY_THRESHOLD:
        rarity = Rarity.LEGENDARY
    elif model_id >= RARITY_EPIC_THRESHOLD:
        rarity = Rarity.EPIC

    attrs = []
    runes = []
    for i in range(3):
        attr_type = fields[ITEM_FIELD_ATTR_TYPE_0 + i]
        attr_value = fields[ITEM_FIELD_ATTR_VALUE_0 + i]
        if not attr_type or not attr_value:
            continue
        if attr_type >= RUNE_TYPE_THRESHOLD:
            runes.append(f"{RuneType(attr_type).name} +{attr_value}%")
        else:
            attrs.append(f"{Attribute(attr_type).name} +{attr_value}")

    type_val = ""
    if raw_id == ItemType.WEAPON:
        type_val = (
            f"Dmg {fields[ITEM_FIELD_MIN_DAMAGE]}-{fields[ITEM_FIELD_MAX_DAMAGE]}"
        )
    elif raw_id == ItemType.SHIELD:
        type_val = f"Block {fields[ITEM_FIELD_MIN_DAMAGE]}%"
    elif raw_id in (
        ItemType.BREASTPLATE,
        ItemType.FOOTWEAR,
        ItemType.GLOVES,
        ItemType.HAT,
        ItemType.BELT,
        ItemType.AMULET,
        ItemType.RING,
        ItemType.TALISMAN,
    ):
        type_val = f"Armor {fields[ITEM_FIELD_MIN_DAMAGE]}"

    gold = silver // 100
    sil = silver % 100

    lines = [f"  [{slot_label}] {tp} ({cls}) - {rarity}"]
    if type_val:
        lines.append(f"    {type_val}")
    if attrs:
        lines.append(f"    Attrs: {', '.join(attrs)}")
    if runes:
        lines.append(f"    Runes: {', '.join(runes)}")
    if enchant:
        lines.append(f"    Enchant: {enchant}")
    lines.append(
        f"    Gem: {gem_str} | Upgrades: {upgrades} | Quality: {quality} | Washed: {washed}"
    )
    lines.append(f"    Sell: {gold:,}g {sil}s | Mush: {mush}")
    return "\n".join(lines)
