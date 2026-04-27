from dataclasses import dataclass

from sfbot.constants import (
    Attribute,
    PotionAttributeType,
    PotionSize,
)
from sfbot.items import Item

# --- Dungeon elixir duration constants ---
ELIXIR_DURATION = 72 * 3600  # 3 days per potion drink
CYCLE_DURATION = 144 * 3600  # 6 days = 1 full cycle (2 drinks)
POTIONS_PER_CYCLE = 2  # 2 same-type potions = 1 cycle


@dataclass
class Potion:
    attr: PotionAttributeType
    size: PotionSize | None = None

    def should_drink(self, main_attr: Attribute) -> bool:
        """Return True if this potion should be drunk immediately."""
        if self.attr == PotionAttributeType.HP:
            return False
        if self.attr == main_attr and self.size == PotionSize.LARGE:
            return False
        if (
            self.attr == PotionAttributeType.CONSTITUTION
            and self.size == PotionSize.LARGE
        ):
            return False
        return True

    def can_drink(self, active_size: PotionSize | None) -> bool:
        """True if this potion can replace the currently active one of the same attr.

        Can drink if the new potion's size is not smaller than the active size.
        HP potions have no size and can always be drunk.
        """
        if active_size is None:
            return True

        if self.attr == PotionAttributeType.HP:
            return True

        # size is always set for non-HP potions
        return not (self.size < active_size)  # type: ignore


@dataclass
class ActivePotion:
    potion: Potion
    expires: int
    slot: int


@dataclass
class InventoryPotion:
    potion: Potion
    wire: str
    item: Item


def _find_expires(potions: list[ActivePotion], attr: PotionAttributeType) -> int:
    """Find expiry timestamp for an active dungeon potion (large only, except wings)."""
    for p in potions:
        if p.potion.attr != attr:
            continue
        if attr != PotionAttributeType.HP and p.potion.size != PotionSize.LARGE:
            continue
        return p.expires
    return 0


def calc_dungeon_potion_credits(
    potions: list[ActivePotion],
    main_potion_attr: PotionAttributeType,
    is_dungeon_ready: bool,
    now: int,
) -> dict[PotionAttributeType, int]:
    """Return how many inventory potions each active dungeon potion covers.

    Each 72-hour block of remaining (or excess) time on a large CON / main potion
    counts as one credit (one fewer potion needed from inventory).
    Wings get credit 1 if they last >= 144 hours past the reference point.

    When dungeon-ready the reference is the common end of CON+main (the earliest
    point where dungeon-ready status would lapse).  Otherwise it is *now*.
    """
    con_expires = _find_expires(potions, PotionAttributeType.CONSTITUTION)
    main_expires = _find_expires(potions, main_potion_attr)
    wings_expires = _find_expires(potions, PotionAttributeType.HP)

    if is_dungeon_ready:
        base = min(con_expires, main_expires, wings_expires)
    else:
        base = now

    con_remaining = max(0, con_expires - base)
    main_remaining = max(0, main_expires - base)
    wings_remaining = max(0, wings_expires - base)

    return {
        PotionAttributeType.CONSTITUTION: con_remaining // ELIXIR_DURATION,
        main_potion_attr: main_remaining // ELIXIR_DURATION,
        PotionAttributeType.HP: 1 if wings_remaining >= CYCLE_DURATION else 0,
    }
