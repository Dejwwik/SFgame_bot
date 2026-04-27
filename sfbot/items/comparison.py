"""Item and gem comparison using dynamic attr correction.

Scoring system:
- Items are compared against currently equipped items using bias-corrected
  attribute weights that automatically prioritize attrs the build is deficient in.
- Weapons use a marginal damage gain formula: P_new - P_old.
- Shields include block chance scaled by total constitution.
- Socket Gate (Level >= 25): items without sockets are rejected when the
  current item has one (if it has main attr or constitution).
- Gems are scored using a self-rebalancing system that pushes gem attribute
  distribution toward a configurable target ratio.
"""

from dataclasses import dataclass

from sfbot.constants import (
    ITEM_FIELD_COUNT,
    SOCKET_GATE_LEVEL,
    VALUES_DELIMITER,
    WIRE_EQUIPMENT,
    Attribute,
    CharClass,
    CompanionClass,
    EquipmentSlot,
    GemAttr,
    GemSlot,
    ItemAttributeType,
    ItemType,
)
from sfbot.items import Item, parse_item
from sfbot.session import GameSession
from sfbot.utils import strip_upgrades

# --- Block chance value multiplier ---
BLOCK_VALUE_MULTIPLIER = 0.05

# --- Ratio floor for division-by-zero protection ---
# Prevents T²/A from dividing by zero when an attr has 0 current ratio.
# When an attr is missing, the correction spikes massively (e.g. T²/0.0000001),
# but self-rebalances: after one purchase the ratio rises above the floor
# and the real T²/A formula takes over, naturally converging toward target.
# Target ratio of 0 → T²=0 → correction=0 regardless of the floor.
RATIO_FLOOR = 0.05

# --- Minimum improvement ratio for buying shop items ---
# new_abs / old_abs must exceed this to justify a purchase.
ITEM_IMPROVEMENT_RATIO = 1.15

# --- Minimum improvement ratio for replacing socketed gems ---
GEM_IMPROVEMENT_RATIO = 1.15

# Avoid throwing all gems away
GEM_KEEP_RATIO = 0.9


@dataclass(slots=True)
class ComparisonProfile:
    """Character profile for multi-character item evaluation.

    companion=None means the main character.
    companion=CompanionClass.WARRIOR/MAGE/SCOUT for tower helpers.
    """

    char_class: CharClass
    main_attr: Attribute
    equipment_target_ratios: dict[Attribute, float]
    gem_target_ratios: dict[Attribute, float]
    base_attrs: dict[Attribute, int]
    companion: CompanionClass | None = None


# --- ItemType → EquipmentSlot mapping ---
ITEM_TYPE_TO_EQUIP_SLOT: dict[ItemType, EquipmentSlot] = {
    ItemType.HAT: EquipmentSlot.HAT,
    ItemType.BREASTPLATE: EquipmentSlot.BREASTPLATE,
    ItemType.GLOVES: EquipmentSlot.GLOVES,
    ItemType.FOOTWEAR: EquipmentSlot.FOOTWEAR,
    ItemType.AMULET: EquipmentSlot.AMULET,
    ItemType.BELT: EquipmentSlot.BELT,
    ItemType.RING: EquipmentSlot.RING,
    ItemType.TALISMAN: EquipmentSlot.TALISMAN,
    ItemType.WEAPON: EquipmentSlot.WEAPON,
    ItemType.SHIELD: EquipmentSlot.SHIELD,
}


def get_equip_wire_position(slot: EquipmentSlot, profile: ComparisonProfile) -> str:
    """Wire position for equipping to a character's equipment slot.

    Main character: '1/{slot}'
    Companion:      '{companion+101}/{slot}'
    """
    section = getattr(profile.companion, "wire_section", WIRE_EQUIPMENT)
    return f"{section}/{slot.value}"


# --- ItemAttributeType → Attribute(s) ---
_SINGLE_ATTR_MAP: dict[ItemAttributeType, Attribute] = {
    ItemAttributeType.STRENGTH: Attribute.STRENGTH,
    ItemAttributeType.DEXTERITY: Attribute.DEXTERITY,
    ItemAttributeType.INTELLIGENCE: Attribute.INTELLIGENCE,
    ItemAttributeType.CONSTITUTION: Attribute.CONSTITUTION,
    ItemAttributeType.LUCK: Attribute.LUCK,
}

_TRIPLE_ATTR_MAP: dict[ItemAttributeType, tuple[Attribute, ...]] = {
    ItemAttributeType.STR_CON_LUCK: (
        Attribute.STRENGTH,
        Attribute.CONSTITUTION,
        Attribute.LUCK,
    ),
    ItemAttributeType.DEX_CON_LUCK: (
        Attribute.DEXTERITY,
        Attribute.CONSTITUTION,
        Attribute.LUCK,
    ),
    ItemAttributeType.INT_CON_LUCK: (
        Attribute.INTELLIGENCE,
        Attribute.CONSTITUTION,
        Attribute.LUCK,
    ),
}

_GEM_ATTR_TO_ATTRIBUTE: dict[GemAttr, Attribute] = {
    GemAttr.STRENGTH: Attribute.STRENGTH,
    GemAttr.DEXTERITY: Attribute.DEXTERITY,
    GemAttr.INTELLIGENCE: Attribute.INTELLIGENCE,
    GemAttr.CONSTITUTION: Attribute.CONSTITUTION,
    GemAttr.LUCK: Attribute.LUCK,
}


# ---------------------------------------------------------------------------
# Data collection from equipped items
# ---------------------------------------------------------------------------


def equipped_items(session: GameSession) -> dict[EquipmentSlot, Item | None]:
    """Parse all 10 equipment slots from server data."""
    raw = session.login_data.get("ownplayersaveequipment", "").split(VALUES_DELIMITER)
    vals = [int(x) for x in raw if x]
    result: dict[EquipmentSlot, Item | None] = {}
    for slot in EquipmentSlot:
        offset = (slot.value - 1) * ITEM_FIELD_COUNT
        if offset + ITEM_FIELD_COUNT > len(vals):
            result[slot] = None
            continue
        chunk = vals[offset : offset + ITEM_FIELD_COUNT]
        result[slot] = parse_item(chunk)
    return result


def companion_equipped_items(
    session: GameSession, companion: CompanionClass
) -> dict[EquipmentSlot, Item | None]:
    """Parse equipment for a specific tower companion."""
    raw = session.login_data.get("companionequipment", "").split(VALUES_DELIMITER)
    vals = [int(x) for x in raw if x]
    slots_per_companion = ITEM_FIELD_COUNT * len(EquipmentSlot)
    base = companion.value * slots_per_companion
    result: dict[EquipmentSlot, Item | None] = {}
    for slot in EquipmentSlot:
        offset = base + (slot.value - 1) * ITEM_FIELD_COUNT
        if offset + ITEM_FIELD_COUNT > len(vals):
            result[slot] = None
            continue
        chunk = vals[offset : offset + ITEM_FIELD_COUNT]
        result[slot] = parse_item(chunk)
    return result


def profile_equipped_items(
    session: GameSession, profile: ComparisonProfile
) -> dict[EquipmentSlot, Item | None]:
    """Get equipped items for the character a profile represents."""
    if profile.companion is None:
        return equipped_items(session)
    return companion_equipped_items(session, profile.companion)


def item_attrs(item: Item | None) -> dict[Attribute, int]:
    """Per-attribute attribute contribution of an item (excluding inserted gem)."""
    result: dict[Attribute, int] = {attr: 0 for attr in Attribute}
    if item is None:
        return result
    for attr in item.attributes:
        if attr.attribute_type in _SINGLE_ATTR_MAP:
            result[_SINGLE_ATTR_MAP[attr.attribute_type]] += attr.value
        elif attr.attribute_type == ItemAttributeType.ALL:
            for a in Attribute:
                result[a] += attr.value
        elif attr.attribute_type in _TRIPLE_ATTR_MAP:
            for a in _TRIPLE_ATTR_MAP[attr.attribute_type]:
                result[a] += attr.value
    return result


def raw_item_attrs(item: Item | None) -> dict[Attribute, int]:
    """Per-attribute contribution of an item with smith upgrades stripped.

    Smith upgrades boost every attribute by 3% per upgrade (compound,
    rounded each step). We reverse all non-zero attribute values.
    """
    if item is None or item.upgrades == 0:
        return item_attrs(item)

    result: dict[Attribute, int] = {attr: 0 for attr in Attribute}
    for attr in item.attributes:
        value = strip_upgrades(attr.value, item.upgrades)
        if attr.attribute_type in _SINGLE_ATTR_MAP:
            result[_SINGLE_ATTR_MAP[attr.attribute_type]] += value
        elif attr.attribute_type == ItemAttributeType.ALL:
            for a in Attribute:
                result[a] += value
        elif attr.attribute_type in _TRIPLE_ATTR_MAP:
            for a in _TRIPLE_ATTR_MAP[attr.attribute_type]:
                result[a] += value
    return result


def total_equipped_item_attrs(
    equipped_items: dict[EquipmentSlot, Item | None],
) -> dict[Attribute, int]:
    """Sum attribute contributions from all equipped items (excluding gems).

    If profile is None, uses the main character's equipment.
    """

    totals: dict[Attribute, int] = {attr: 0 for attr in Attribute}
    for item in equipped_items.values():
        for attr, val in item_attrs(item).items():
            totals[attr] += val
    return totals


def gem_attrs(
    gem_attr: GemAttr, gem_value: int, main_attr: Attribute
) -> dict[Attribute, int]:
    """Per-attribute contribution of a single gem."""
    result: dict[Attribute, int] = {attr: 0 for attr in Attribute}
    if gem_attr == GemAttr.LEGENDARY:
        result[main_attr] += gem_value
        result[Attribute.CONSTITUTION] += gem_value
    elif gem_attr == GemAttr.BLACK:
        for a in Attribute:
            result[a] += gem_value
    elif gem_attr in _GEM_ATTR_TO_ATTRIBUTE:
        result[_GEM_ATTR_TO_ATTRIBUTE[gem_attr]] += gem_value
    return result


def equipped_gem_attrs(
    items: dict[EquipmentSlot, Item | None], main_attr: Attribute
) -> dict[Attribute, int]:
    """Sum of all inserted-gem contributions from the given equipment set."""
    totals: dict[Attribute, int] = {attr: 0 for attr in Attribute}
    for item in items.values():
        if item is None or item.inserted_gem is None:
            continue
        for attr, val in gem_attrs(
            item.inserted_gem.attr, item.inserted_gem.power, main_attr
        ).items():
            totals[attr] += val
    return totals


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _attr_ratios(attrs: dict[Attribute, int]) -> dict[Attribute, float]:
    """Current attribute ratios (each / total), with zero-guard."""
    total = sum(attrs.values())
    if total == 0:
        return {attr: RATIO_FLOOR for attr in Attribute}
    return {attr: max(attrs[attr] / total, RATIO_FLOOR) for attr in Attribute}


def _attr_corrections(
    current_ratios: dict[Attribute, float],
    target_ratios: dict[Attribute, float],
) -> dict[Attribute, float]:
    """C_attr = T_attr² / max(A_attr, RATIO_FLOOR).

    T² in the numerator encodes inherent attribute importance (main > con > luck >
    off) even when the build is perfectly balanced, while dividing by A
    penalises over-represented attributes and boosts deficient ones.
    """
    corrections: dict[Attribute, float] = {}
    for attr in Attribute:
        a_val = current_ratios[attr]
        t_val = target_ratios[attr]
        corrections[attr] = (t_val * t_val) / max(a_val, RATIO_FLOOR)
    return corrections


def _can_be_used_by(item: Item, char_class: CharClass) -> bool:
    """True if the given character class can equip this item.

    Items with char_class=None are universal (amulet, ring, talisman).
    Class-restricted items have char_class in {Warrior, Mage, Scout} — the
    three base classes. Hybrid classes map to base classes for weapon/armor:
      Warrior weapons: Warrior, Paladin, Berserker, Assassin, BattleMage, PlagueDoctor
      Warrior armor:   Warrior, Paladin, DemonHunter (no shield for Berserker)
      Scout weapons:   Scout, DemonHunter
      Scout armor:     Scout, Assassin, Bard, Druid
      Mage weapons:    Mage, Necromancer, Bard, Druid
      Mage armor:      Mage, Necromancer, BattleMage, PlagueDoctor
    """
    req = item.char_class
    if req is None:
        return True

    match char_class:
        case CharClass.WARRIOR | CharClass.PALADIN:
            return req == CharClass.WARRIOR
        case CharClass.BERSERKER:
            return req == CharClass.WARRIOR and not item.is_shield
        case CharClass.SCOUT:
            return req == CharClass.SCOUT
        case CharClass.MAGE | CharClass.NECROMANCER:
            return req == CharClass.MAGE
        case CharClass.ASSASSIN:
            return (req == CharClass.WARRIOR and item.is_weapon) or (
                req == CharClass.SCOUT and not item.is_weapon
            )
        case CharClass.BARD | CharClass.DRUID:
            return (req == CharClass.MAGE and item.is_weapon) or (
                req == CharClass.SCOUT and not item.is_weapon
            )
        case CharClass.BATTLE_MAGE | CharClass.PLAGUE_DOCTOR:
            return (req == CharClass.WARRIOR and item.is_weapon) or (
                req == CharClass.MAGE and not item.is_weapon
            )
        case CharClass.DEMON_HUNTER:
            return (req == CharClass.SCOUT and item.is_weapon) or (
                req == CharClass.WARRIOR and not item.is_weapon and not item.is_shield
            )
    return False


def _is_equippable_by(item: Item, profile: ComparisonProfile) -> bool:
    """True if the profile's character can equip this item.

    Companions cannot equip shields.
    """
    if profile.companion is not None and item.item_type == ItemType.SHIELD:
        return False
    return _can_be_used_by(item, profile.char_class)


@dataclass(slots=True)
class ProfileEquipment:
    """Pre-loaded equipment snapshot for one character profile.

    Built once per scoring round by load_equipped_data() so that
    score_item_best() does not re-parse session data for every
    candidate item.
    """

    profile: ComparisonProfile
    items: dict[EquipmentSlot, Item | None]
    item_attrs: dict[Attribute, int]
    gem_attrs: dict[Attribute, int]


def load_equipped_data(
    session: GameSession,
    profiles: list[ComparisonProfile],
) -> list[ProfileEquipment]:
    """Pre-load equipped items and attributes for all profiles.

    Called once per scoring round so score_item_best does not
    re-parse session data for every candidate item.
    """

    profile_data: list[ProfileEquipment] = []
    for profile in profiles:
        items = profile_equipped_items(session, profile)
        profile_data.append(
            ProfileEquipment(
                profile=profile,
                items=items,
                item_attrs=total_equipped_item_attrs(items),
                gem_attrs=equipped_gem_attrs(items, profile.main_attr),
            )
        )
    return profile_data


# ---------------------------------------------------------------------------
# Item scoring
# ---------------------------------------------------------------------------


def score_item(
    new_item: Item,
    current_item: Item | None,
    character_level: int,
    main_attr: Attribute,
    equipped_item_attrs: dict[Attribute, int],
    character_base_attrs: dict[Attribute, int],
    target_ratios: dict[Attribute, float],
) -> float:
    """Score a candidate item vs the currently equipped item.

    Returns positive if *new_item* is an upgrade, negative if worse.

    Args:
        equipped_item_attrs: Sum of all equipped item attributes (for correction ratios).
        character_base_attrs: Character base attributes (without equipment bonuses).
            Combined with equipped_item_attrs in weapon/shield formulas.
    """
    ratios = _attr_ratios(equipped_item_attrs)
    corrections = _attr_corrections(ratios, target_ratios)

    new_item_attrs = raw_item_attrs(new_item)
    old_item_attrs = raw_item_attrs(current_item)

    # --- Socket Gate (level >= 25) ---
    # After level 25 gems become a major power source, so a socket is
    # mandatory.  Three rules apply in order:
    #
    # 1. New item has NO socket → always reject (-inf).
    # 2. New item has a socket AND current item has no socket:
    #    a) New item carries main-attribute or constitution → auto-accept (+inf),
    #       the socket alone justifies the swap.
    #    b) New item has only off-attributes → reject (-inf), a useless socket
    #       is not worth losing real attributes.
    # 3. Both items have sockets (or slot is empty) → fall through to
    #    normal attr-based scoring below.
    if character_level >= SOCKET_GATE_LEVEL:
        new_has_socket = new_item.gem_slot != GemSlot.NONE

        if not new_has_socket:
            return -float("inf")

        if current_item is not None and current_item.gem_slot == GemSlot.NONE:
            has_main = new_item_attrs[main_attr] > 0
            has_con = new_item_attrs[Attribute.CONSTITUTION] > 0
            if has_main or has_con:
                return float("inf")
            return -float("inf")

    old_abs = 0.0
    new_abs = 0.0

    if new_item.item_type == ItemType.WEAPON:
        # --- Weapon: marginal damage gain + corrected secondary attributes ---
        old_avg_dmg = current_item.avg_dmg if current_item else 0.0
        new_avg_dmg = new_item.avg_dmg

        total_main = character_base_attrs[main_attr] + equipped_item_attrs[main_attr]

        old_power = old_avg_dmg * (1 + total_main / 10)
        projected_main = (
            total_main - old_item_attrs[main_attr] + new_item_attrs[main_attr]
        )
        new_power = new_avg_dmg * (1 + projected_main / 10)

        old_abs += old_power
        new_abs += new_power

        for attr in Attribute:
            old_abs += old_item_attrs[attr] * corrections[attr]
            new_abs += new_item_attrs[attr] * corrections[attr]

    elif new_item.item_type == ItemType.SHIELD:
        # --- Shield: corrected attributes + block value ---
        old_block = (current_item.block_chance or 0) if current_item else 0
        new_block = new_item.block_chance or 0
        total_con = (
            character_base_attrs[Attribute.CONSTITUTION]
            + equipped_item_attrs[Attribute.CONSTITUTION]
        )

        old_abs += old_block * total_con * BLOCK_VALUE_MULTIPLIER
        new_abs += new_block * total_con * BLOCK_VALUE_MULTIPLIER

        for attr in Attribute:
            old_abs += old_item_attrs[attr] * corrections[attr]
            new_abs += new_item_attrs[attr] * corrections[attr]

    else:
        # --- Regular equipment: corrected attribute scores ---
        for attr in Attribute:
            old_abs += old_item_attrs[attr] * corrections[attr]
            new_abs += new_item_attrs[attr] * corrections[attr]

    score = new_abs - old_abs

    # Reject marginal upgrades that don't meet the improvement threshold.
    # Only applies to positive deltas on non-weapon items — weapons use
    # projected-damage scoring where the main-attr multiplier inflates
    # absolute values, making ratio comparison meaningless.
    if (
        score > 0
        and old_abs > 0
        and new_item.item_type != ItemType.WEAPON
        and new_abs / old_abs < ITEM_IMPROVEMENT_RATIO
    ):
        return 0.0

    return score


def _would_oscillate(
    new_item: Item,
    current_item: Item | None,
    level: int,
    entry: ProfileEquipment,
) -> bool:
    """Check if equipping new_item would cause the displaced item to immediately score higher.

    Simulates the post-swap equipped attrs and scores the displaced item
    against the newly equipped one. If it would win, the swap is unstable.
    """
    if current_item is None:
        return False

    old_attrs = item_attrs(current_item)
    new_attrs = item_attrs(new_item)

    # Simulate post-swap equipped_item_attrs
    swapped_attrs: dict[Attribute, int] = {}
    for attr in Attribute:
        swapped_attrs[attr] = entry.item_attrs[attr] - old_attrs[attr] + new_attrs[attr]

    reverse_score = score_item(
        current_item,
        new_item,
        level,
        entry.profile.main_attr,
        swapped_attrs,
        entry.profile.base_attrs,
        entry.profile.equipment_target_ratios,
    )
    return reverse_score > 0


def score_item_best(
    new_item: Item,
    level: int,
    equipped_data: list[ProfileEquipment],
) -> tuple[ComparisonProfile | None, float]:
    """Score a candidate item against multiple character profiles.

    Each profile is evaluated against its own pre-loaded equipped items.
    Returns the profile with the highest positive score, or (None, -inf)
    if no profile benefits from the item.

    Args:
        equipped_data: Pre-loaded ProfileEquipment per profile.
            Built once per scoring round via load_equipped_data().
    """

    # Comparison profiles which can use this item.
    eligible = [
        entry for entry in equipped_data if _is_equippable_by(new_item, entry.profile)
    ]
    if not eligible:
        return None, -float("inf")

    best_profile: ComparisonProfile | None = None
    best_score = -float("inf")

    for entry in eligible:
        current_item = entry.items[ITEM_TYPE_TO_EQUIP_SLOT[new_item.item_type]]

        item_score = score_item(
            new_item,
            current_item,
            level,
            entry.profile.main_attr,
            entry.item_attrs,
            entry.profile.base_attrs,
            entry.profile.equipment_target_ratios,
        )
        if item_score > best_score:
            best_score = item_score
            best_profile = entry.profile

    if best_score <= 0:
        return None, best_score
    return best_profile, best_score


# ---------------------------------------------------------------------------
# Gem scoring
# ---------------------------------------------------------------------------


def score_gem(
    gem_attr: GemAttr,
    gem_value: int,
    main_attr: Attribute,
    target_ratios: dict[Attribute, float],
    current_gem_attrs: dict[Attribute, int],
) -> float:
    """Score a gem for socketing / keeping.

    Uses the same T²/A correction as item scoring. Gems that bring the
    current gem distribution closer to the target are scored higher.
    """
    total = sum(current_gem_attrs.values())

    corrections: dict[Attribute, float] = {}
    if total == 0:
        for attr in Attribute:
            corrections[attr] = target_ratios[attr]
    else:
        for attr in Attribute:
            current_ratio = current_gem_attrs[attr] / total
            target = target_ratios[attr]
            corrections[attr] = (target * target) / max(current_ratio, RATIO_FLOOR)

    if gem_attr in _GEM_ATTR_TO_ATTRIBUTE:
        mapped_attr = _GEM_ATTR_TO_ATTRIBUTE[gem_attr]
        return gem_value * corrections[mapped_attr]

    if gem_attr == GemAttr.LEGENDARY:
        return gem_value * (
            corrections[main_attr] + corrections[Attribute.CONSTITUTION]
        )

    if gem_attr == GemAttr.BLACK:
        return gem_value * sum(corrections[a] for a in Attribute)

    return 0.0


def score_gem_best(
    gem_attr: GemAttr,
    gem_value: int,
    profiles: list[ComparisonProfile],
    current_gem_attrs: dict[Attribute, int],
) -> float:
    """Score a gem across multiple character profiles.

    Uses absolute scores (not ratios) so that a profile with 0 of the gem
    attr does not produce an inflated improvement. The T² formula naturally
    weights each profile by how much that attribute matters to the character.
    """
    if not profiles:
        return 0.0
    return max(
        score_gem(
            gem_attr, gem_value, p.main_attr, p.gem_target_ratios, current_gem_attrs
        )
        for p in profiles
    )


# ---------------------------------------------------------------------------
# Gem placement scoring (for socketing gems into equipment)
# ---------------------------------------------------------------------------


def score_gem_placement(
    gem_attr: GemAttr,
    gem_value: int,
    profile_equipment: ProfileEquipment,
    slot: EquipmentSlot,
    *,
    improvement_ratio: float,
) -> float:
    """Score placing a backpack gem into a specific equipment slot.

    Returns positive if the gem improves the setup, 0.0 if not enough improvement.
    For empty sockets the full gem score is returned.
    For filled sockets the improvement must exceed improvement_ratio.
    """
    item = profile_equipment.items[slot]
    if item is None or item.gem_slot == GemSlot.NONE:
        return 0.0

    profile = profile_equipment.profile
    current_gem_attrs = profile_equipment.gem_attrs

    # Empty socket: score against current baseline (no old gem to remove)
    if item.inserted_gem is None:
        return score_gem(
            gem_attr,
            gem_value,
            profile.main_attr,
            profile.gem_target_ratios,
            current_gem_attrs,
        )

    # Filled socket: subtract old gem from baseline so both gems are scored
    # against the same "without either gem" state
    old_gem = item.inserted_gem
    old_contribution = gem_attrs(old_gem.attr, old_gem.power, profile.main_attr)
    baseline = {
        attr: max(current_gem_attrs[attr] - old_contribution[attr], 0)
        for attr in Attribute
    }

    new_score = score_gem(
        gem_attr, gem_value, profile.main_attr, profile.gem_target_ratios, baseline
    )
    old_score = score_gem(
        old_gem.attr,
        old_gem.power,
        profile.main_attr,
        profile.gem_target_ratios,
        baseline,
    )

    # Too small improvement
    if old_score > 0 and new_score / old_score < improvement_ratio:
        return 0.0

    return new_score - old_score


def score_gem_best_placement(
    gem_attr: GemAttr,
    gem_value: int,
    equipped_data: list[ProfileEquipment],
    *,
    improvement_ratio: float = GEM_IMPROVEMENT_RATIO,
) -> tuple[ComparisonProfile | None, EquipmentSlot | None, float]:
    """Find the best profile and equipment slot to place a gem.

    Scans all profiles and equipment slots, returning the combination
    that gives the highest positive score. Returns (None, None, 0.0) if
    the gem does not improve any slot.
    """
    best_profile: ComparisonProfile | None = None
    best_slot: EquipmentSlot | None = None
    best_score = 0.0

    for entry in equipped_data:
        for slot in EquipmentSlot:
            # Skip shield for the BERT in tower.
            if entry.profile.companion and slot == EquipmentSlot.SHIELD:
                continue
            score = score_gem_placement(gem_attr, gem_value, entry, slot, improvement_ratio=improvement_ratio)
            if score > best_score:
                best_score = score
                best_profile = entry.profile
                best_slot = slot

    return best_profile, best_slot, best_score
