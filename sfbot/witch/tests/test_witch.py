from unittest.mock import MagicMock

from sfbot.constants import (
    ITEM_FIELD_COUNT,
    ITEM_FIELD_ENCHANTMENT,
    ITEM_FIELD_TYPE,
    CompanionClass,
    Enchantment,
    EquipmentSlot,
)
from sfbot.witch.witch import Witch

ALL_ENCHANT_IDS: list[int] = [e.value for e in Enchantment]
NUM_SLOTS = len(EquipmentSlot)
SLOTS_PER_COMPANION = ITEM_FIELD_COUNT * NUM_SLOTS
EQUIPPED = 1

HAT = 0
BREASTPLATE = 1
GLOVES = 2
FOOTWEAR = 3
AMULET = 4
BELT = 5
RING = 6
TALISMAN = 7
WEAPON = 8


def make_witchshop(enchant_ids: list[int], price: int = 50000) -> str:
    vals = [0] * 36
    vals[4] = len(enchant_ids)
    vals[35] = price
    for i, eid in enumerate(enchant_ids):
        vals[6 + 3 * i] = eid
    return "/".join(str(v) for v in vals)


def make_equipment(
    enchants: dict[int, int] | None = None,
    equipped: set[int] | None = None,
) -> str:
    if equipped is None:
        equipped = set(range(NUM_SLOTS))
    vals = [0] * (ITEM_FIELD_COUNT * NUM_SLOTS)
    for slot_idx in equipped:
        vals[slot_idx * ITEM_FIELD_COUNT + ITEM_FIELD_TYPE] = EQUIPPED
    for slot_idx, eid in (enchants or {}).items():
        vals[slot_idx * ITEM_FIELD_COUNT + ITEM_FIELD_ENCHANTMENT] = eid
    return "/".join(str(v) for v in vals)


def make_companion_equipment(
    companions: dict[CompanionClass, tuple[dict[int, int], set[int]]] | None = None,
) -> str:
    """companions: {CompanionClass: (enchant_map, equipped_slots)}"""
    vals = [0] * (SLOTS_PER_COMPANION * len(CompanionClass))
    for companion, (enchants, equipped) in (companions or {}).items():
        base = companion.value * SLOTS_PER_COMPANION
        for slot_idx in equipped:
            vals[base + slot_idx * ITEM_FIELD_COUNT + ITEM_FIELD_TYPE] = EQUIPPED
        for slot_idx, eid in enchants.items():
            vals[base + slot_idx * ITEM_FIELD_COUNT + ITEM_FIELD_ENCHANTMENT] = eid
    return "/".join(str(v) for v in vals)


def make_witch(
    available: list[int] | None = None,
    main_enchants: dict[int, int] | None = None,
    main_equipped: set[int] | None = None,
    companions: dict[CompanionClass, tuple[dict[int, int], set[int]]] | None = None,
) -> Witch:
    session = MagicMock()
    session.login_data = {
        "witchshop": make_witchshop(available or ALL_ENCHANT_IDS),
        "ownplayersaveequipment": make_equipment(main_enchants, main_equipped),
        "companionequipment": make_companion_equipment(companions),
    }
    return Witch(session)


ALL_ENCHANTED: dict[int, int] = {
    HAT: Enchantment.ARCHAEOLOGICAL_AURA,
    BREASTPLATE: Enchantment.MARIOS_BEARD,
    GLOVES: Enchantment.SHADOW_OF_COWBOY,
    FOOTWEAR: Enchantment.MANY_FEET_BOOTS,
    AMULET: Enchantment.UNHOLY_ACQUISITIVENESS,
    BELT: Enchantment.THIRSTY_WANDERER,
    RING: Enchantment.GRAVE_ROBBERS_PRAYER,
    TALISMAN: Enchantment.ROBBER_BARON_RITUAL,
    WEAPON: Enchantment.SWORD_OF_VENGEANCE,
}

ALL_BUT_SHIELD = set(range(NUM_SLOTS)) - {9}


class TestMissingEnchantments:
    def test_all_equipped_none_enchanted(self) -> None:
        witch = make_witch()
        missing = witch.missing_enchantments()
        # 9 main + 3 companion weapons = 12
        main = [(e, s, i, c) for e, s, i, c in missing if c is None]
        comp = [(e, s, i, c) for e, s, i, c in missing if c is not None]
        assert {m[0] for m in main} == set(Enchantment)
        assert len(comp) == 0  # no companions have items

    def test_all_enchanted(self) -> None:
        witch = make_witch(main_enchants=ALL_ENCHANTED)
        assert witch.missing_enchantments() == []

    def test_skips_unequipped_slot(self) -> None:
        equipped = set(range(NUM_SLOTS)) - {BREASTPLATE}
        witch = make_witch(main_equipped=equipped)
        enchants = {m[0] for m in witch.missing_enchantments() if m[3] is None}
        assert Enchantment.MARIOS_BEARD not in enchants
        assert Enchantment.SWORD_OF_VENGEANCE in enchants

    def test_companion_weapon_missing(self) -> None:
        companions = {
            CompanionClass.WARRIOR: ({}, {WEAPON}),
        }
        witch = make_witch(main_enchants=ALL_ENCHANTED, companions=companions)
        missing = witch.missing_enchantments()
        assert len(missing) == 1
        enchant, slot, ident, companion = missing[0]
        assert enchant == Enchantment.SWORD_OF_VENGEANCE
        assert slot == EquipmentSlot.WEAPON
        assert companion == CompanionClass.WARRIOR

    def test_companion_gloves_missing(self) -> None:
        companions = {
            CompanionClass.WARRIOR: ({}, {GLOVES}),
        }
        witch = make_witch(main_enchants=ALL_ENCHANTED, companions=companions)
        missing = witch.missing_enchantments()
        assert len(missing) == 1
        enchant, slot, ident, companion = missing[0]
        assert enchant == Enchantment.SHADOW_OF_COWBOY
        assert slot == EquipmentSlot.GLOVES
        assert companion == CompanionClass.WARRIOR

    def test_companion_weapon_and_gloves_missing(self) -> None:
        companions = {
            CompanionClass.WARRIOR: ({}, {WEAPON, GLOVES}),
        }
        witch = make_witch(main_enchants=ALL_ENCHANTED, companions=companions)
        missing = witch.missing_enchantments()
        assert len(missing) == 2
        enchants = {m[0] for m in missing}
        assert enchants == {
            Enchantment.SWORD_OF_VENGEANCE,
            Enchantment.SHADOW_OF_COWBOY,
        }

    def test_companion_weapon_already_enchanted(self) -> None:
        companions = {
            CompanionClass.SCOUT: (
                {
                    WEAPON: Enchantment.SWORD_OF_VENGEANCE,
                    GLOVES: Enchantment.SHADOW_OF_COWBOY,
                },
                {WEAPON, GLOVES},
            ),
        }
        witch = make_witch(main_enchants=ALL_ENCHANTED, companions=companions)
        assert witch.missing_enchantments() == []

    def test_companion_no_weapon_equipped(self) -> None:
        companions = {
            CompanionClass.MAGE: ({}, {HAT, BREASTPLATE}),
        }
        witch = make_witch(main_enchants=ALL_ENCHANTED, companions=companions)
        # No weapon or gloves equipped → nothing missing
        assert witch.missing_enchantments() == []

    def test_companion_not_in_data(self) -> None:
        """Companions without any equipment data are skipped."""
        witch = make_witch(main_enchants=ALL_ENCHANTED)
        assert witch.missing_enchantments() == []

    def test_all_three_companions_missing_weapon(self) -> None:
        companions = {
            CompanionClass.WARRIOR: ({}, ALL_BUT_SHIELD),
            CompanionClass.MAGE: ({}, ALL_BUT_SHIELD),
            CompanionClass.SCOUT: ({}, ALL_BUT_SHIELD),
        }
        witch = make_witch(main_enchants=ALL_ENCHANTED, companions=companions)
        missing = witch.missing_enchantments()
        # 2 per companion (weapon + gloves) × 3 companions = 6
        assert len(missing) == 6
        weapon_missing = [m for m in missing if m[0] == Enchantment.SWORD_OF_VENGEANCE]
        gloves_missing = [m for m in missing if m[0] == Enchantment.SHADOW_OF_COWBOY]
        assert len(weapon_missing) == 3
        assert len(gloves_missing) == 3
        assert {m[3] for m in missing} == set(CompanionClass)

    def test_weapon_not_in_shop(self) -> None:
        non_weapon = [
            e.value for e in Enchantment if e != Enchantment.SWORD_OF_VENGEANCE
        ]
        companions = {CompanionClass.WARRIOR: ({}, {WEAPON, GLOVES})}
        witch = make_witch(available=non_weapon, companions=companions)
        comp_missing = [m for m in witch.missing_enchantments() if m[3] is not None]
        # Only gloves (SHADOW_OF_COWBOY) since weapon enchant not in shop
        assert len(comp_missing) == 1
        assert comp_missing[0][0] == Enchantment.SHADOW_OF_COWBOY

    def test_mixed_main_and_companion(self) -> None:
        main_enchants = dict(ALL_ENCHANTED)
        del main_enchants[BELT]  # THIRSTY_WANDERER missing on main
        companions = {
            CompanionClass.SCOUT: ({}, {WEAPON, GLOVES}),
        }
        witch = make_witch(main_enchants=main_enchants, companions=companions)
        missing = witch.missing_enchantments()
        assert len(missing) == 3  # 1 main + 2 companion (weapon + gloves)
        main_missing = [m for m in missing if m[3] is None]
        comp_missing = [m for m in missing if m[3] is not None]
        assert main_missing[0][0] == Enchantment.THIRSTY_WANDERER
        assert comp_missing[0][3] == CompanionClass.SCOUT
        assert {m[0] for m in comp_missing} == {
            Enchantment.SWORD_OF_VENGEANCE,
            Enchantment.SHADOW_OF_COWBOY,
        }


class TestIsCompleted:
    def test_completed(self) -> None:
        witch = make_witch(main_enchants=ALL_ENCHANTED)
        assert witch.is_completed is True

    def test_not_completed(self) -> None:
        witch = make_witch()
        assert witch.is_completed is False

    def test_not_completed_companion_missing(self) -> None:
        companions = {CompanionClass.WARRIOR: ({}, {WEAPON})}
        witch = make_witch(main_enchants=ALL_ENCHANTED, companions=companions)
        assert witch.is_completed is False
