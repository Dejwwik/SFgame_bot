from unittest.mock import MagicMock

import pytest

from sfbot.constants import (
    Attribute,
    CharClass,
    CompanionClass,
    Cost,
    GemAttr,
    GemSlot,
    ItemAttributeType,
    ItemType,
    Rarity,
)
from sfbot.constants.parsing import (
    ITEM_FIELD_ATTR_TYPE_0,
    ITEM_FIELD_ATTR_VALUE_0,
    ITEM_FIELD_GEM_POWER,
    ITEM_FIELD_GEM_SLOT,
    ITEM_FIELD_MAX_DAMAGE,
    ITEM_FIELD_MIN_DAMAGE,
    ITEM_FIELD_MODEL,
    ITEM_FIELD_TYPE,
    MODEL_CLASS_DIVISOR,
)
from sfbot.items import InsertedGem, Item, ItemAttribute
from sfbot.items.comparison import (
    ITEM_FIELD_COUNT,
    SOCKET_GATE_LEVEL,
    ComparisonProfile,
    item_attrs,
    load_equipped_data,
    score_gem,
    score_gem_best,
    score_item,
    score_item_best,
)

# --- Target ratios for a mage ---
MAGE_TARGETS: dict[Attribute, float] = {
    Attribute.INTELLIGENCE: 0.45,
    Attribute.CONSTITUTION: 0.30,
    Attribute.LUCK: 0.15,
    Attribute.STRENGTH: 0.05,
    Attribute.DEXTERITY: 0.05,
}

MAIN_ATTR = Attribute.INTELLIGENCE


def _item(
    item_type: ItemType = ItemType.BREASTPLATE,
    attrs: list[tuple[ItemAttributeType, int]] | None = None,
    gem_slot: GemSlot = GemSlot.EMPTY,
    rarity: Rarity = Rarity.NORMAL,
    min_dmg: int | None = None,
    max_dmg: int | None = None,
    block_chance: int | None = None,
    inserted_gem: InsertedGem | None = None,
    char_class: CharClass | None = None,
) -> Item:
    """Build a minimal Item for testing.

    Constructs a raw field array that round-trips through parse_item(),
    so items can be placed in mock session equipment data.
    """
    raw = [0] * ITEM_FIELD_COUNT
    raw[ITEM_FIELD_TYPE] = item_type.value
    # Gem slot: 0=NONE, 1=EMPTY, >1=FILLED (gem_attr encoded in value)
    if gem_slot == GemSlot.NONE:
        raw[ITEM_FIELD_GEM_SLOT] = 0
    elif gem_slot == GemSlot.EMPTY:
        raw[ITEM_FIELD_GEM_SLOT] = 1
    elif gem_slot == GemSlot.FILLED and inserted_gem is not None:
        raw[ITEM_FIELD_GEM_SLOT] = inserted_gem.attr.value + 10
        raw[ITEM_FIELD_GEM_POWER] = inserted_gem.power
    # Model encodes class and rarity
    class_id = char_class.value if char_class is not None else 0
    raw[ITEM_FIELD_MODEL] = class_id * MODEL_CLASS_DIVISOR + 1
    # Attributes (up to 3 slots)
    for i, (attr_type, attr_value) in enumerate(attrs or []):
        if i >= 3:
            break
        raw[ITEM_FIELD_ATTR_TYPE_0 + i] = attr_type.value
        raw[ITEM_FIELD_ATTR_VALUE_0 + i] = attr_value
    # Damage / block
    if min_dmg is not None:
        raw[ITEM_FIELD_MIN_DAMAGE] = min_dmg
    if max_dmg is not None:
        raw[ITEM_FIELD_MAX_DAMAGE] = max_dmg
    if block_chance is not None:
        raw[ITEM_FIELD_MIN_DAMAGE] = block_chance

    item_attribs = [ItemAttribute(t, v) for t, v in (attrs or [])]
    item = Item(
        item_type=item_type,
        char_class=char_class,
        model=raw[ITEM_FIELD_MODEL],
        model_id=1,
        rarity=rarity,
        enchantment=None,
        attributes=item_attribs,
        runes=[],
        cost=Cost(silver=0, mushrooms=0),
        upgrades=0,
        gem_slot=gem_slot,
        quality=0,
        washed=False,
        raw=raw,
        inserted_gem=inserted_gem,
    )
    if min_dmg is not None:
        item.min_dmg = min_dmg
    if max_dmg is not None:
        item.max_dmg = max_dmg
    if block_chance is not None:
        item.block_chance = block_chance
    return item


def _balanced_attrs() -> dict[Attribute, int]:
    """Character with attributes roughly matching mage targets."""
    return {
        Attribute.INTELLIGENCE: 4500,
        Attribute.CONSTITUTION: 3000,
        Attribute.LUCK: 1500,
        Attribute.STRENGTH: 500,
        Attribute.DEXTERITY: 500,
    }


def _gem_attrs(overrides: dict[Attribute, int] | None = None) -> dict[Attribute, int]:
    """Build a gem attrs dict with all 5 Attribute keys (default 0)."""
    result = {attr: 0 for attr in Attribute}
    if overrides:
        result.update(overrides)
    return result


def _mock_session(
    equipped: dict[int, Item] | None = None,
    companion_equipped: dict[CompanionClass, dict[int, Item]] | None = None,
) -> MagicMock:
    """Build a mock GameSession with equipment data.

    equipped: {slot_value: Item} for main character (slot 1-10).
    companion_equipped: {CompanionClass: {slot_value: Item}} for companions.
    """
    session = MagicMock()

    # Main character equipment
    main_vals = [0] * (ITEM_FIELD_COUNT * 10)
    if equipped:
        for slot_val, item in equipped.items():
            offset = (slot_val - 1) * ITEM_FIELD_COUNT
            main_vals[offset : offset + ITEM_FIELD_COUNT] = item.raw
    session.login_data = {
        "ownplayersaveequipment": "/".join(str(v) for v in main_vals),
    }

    # Companion equipment
    comp_vals = [0] * (ITEM_FIELD_COUNT * 10 * 3)
    if companion_equipped:
        for comp, items in companion_equipped.items():
            base = comp.value * ITEM_FIELD_COUNT * 10
            for slot_val, item in items.items():
                offset = base + (slot_val - 1) * ITEM_FIELD_COUNT
                comp_vals[offset : offset + ITEM_FIELD_COUNT] = item.raw
    session.login_data["companionequipment"] = "/".join(str(v) for v in comp_vals)

    return session


# =====================================================================
# item_attrs
# =====================================================================


class TestItemAttrs:
    def test_none_returns_zeroes(self) -> None:
        result = item_attrs(None)
        for attr in Attribute:
            assert result[attr] == 0

    def test_single_attr(self) -> None:
        item = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 100)])
        result = item_attrs(item)
        assert result[Attribute.INTELLIGENCE] == 100
        assert result[Attribute.STRENGTH] == 0

    def test_all_attr(self) -> None:
        item = _item(attrs=[(ItemAttributeType.ALL, 50)])
        result = item_attrs(item)
        for attr in Attribute:
            assert result[attr] == 50

    def test_triple_attr(self) -> None:
        item = _item(attrs=[(ItemAttributeType.INT_CON_LUCK, 80)])
        result = item_attrs(item)
        assert result[Attribute.CONSTITUTION] == 80
        assert result[Attribute.INTELLIGENCE] == 80
        assert result[Attribute.LUCK] == 80
        assert result[Attribute.STRENGTH] == 0

    def test_inserted_gem_excluded(self) -> None:
        gem = InsertedGem(attr=GemAttr.INTELLIGENCE, power=200)
        item = _item(
            attrs=[(ItemAttributeType.INTELLIGENCE, 100)],
            gem_slot=GemSlot.FILLED,
            inserted_gem=gem,
        )
        result = item_attrs(item)
        # Gem is NOT included — only item attributes
        assert result[Attribute.INTELLIGENCE] == 100

    def test_all_attrs_present(self) -> None:
        """All 5 attributes are always present in the result, even if 0."""
        item = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 100)])
        result = item_attrs(item)
        for attr in Attribute:
            assert attr in result


# =====================================================================
# score_item — regular equipment
# =====================================================================


class TestScoreItemRegular:
    def test_better_attrs_positive(self) -> None:
        old = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 100)])
        new = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 200)])
        score = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), _balanced_attrs(), MAGE_TARGETS
        )
        assert score > 0

    def test_worse_attrs_negative(self) -> None:
        old = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 200)])
        new = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 100)])
        score = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), _balanced_attrs(), MAGE_TARGETS
        )
        assert score < 0

    def test_empty_slot_always_positive(self) -> None:
        new = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 50)])
        score = score_item(
            new, None, 10, MAIN_ATTR, _balanced_attrs(), _balanced_attrs(), MAGE_TARGETS
        )
        assert score > 0

    def test_off_attr_weighted_low(self) -> None:
        """Off-attr gain is valued much less than main attr gain when deficient."""
        old = _item(gem_slot=GemSlot.EMPTY)
        new_main = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.INTELLIGENCE, 100)]
        )
        new_off = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.STRENGTH, 100)]
        )
        # INT is deficient (20%) vs target 45%, STR is over-target (15% vs 5%)
        low_int_attrs = {
            Attribute.INTELLIGENCE: 2000,
            Attribute.CONSTITUTION: 3000,
            Attribute.LUCK: 1500,
            Attribute.STRENGTH: 1500,
            Attribute.DEXTERITY: 2000,
        }
        score_main = score_item(
            new_main, old, 30, MAIN_ATTR, low_int_attrs, _balanced_attrs(), MAGE_TARGETS
        )
        score_off = score_item(
            new_off, old, 30, MAIN_ATTR, low_int_attrs, _balanced_attrs(), MAGE_TARGETS
        )
        assert score_main > score_off * 3

    def test_deficient_attr_boosted(self) -> None:
        """An attr the build is deficient in gets higher correction."""
        # Intelligence at only 10% when target is 45%
        low_int_attrs = {
            Attribute.INTELLIGENCE: 1000,
            Attribute.CONSTITUTION: 5000,
            Attribute.LUCK: 2000,
            Attribute.STRENGTH: 1000,
            Attribute.DEXTERITY: 1000,
        }
        old = _item(gem_slot=GemSlot.EMPTY)
        new = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.INTELLIGENCE, 100)]
        )
        score = score_item(
            new, old, 30, MAIN_ATTR, low_int_attrs, _balanced_attrs(), MAGE_TARGETS
        )

        # Same item in a balanced build
        score_balanced = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), _balanced_attrs(), MAGE_TARGETS
        )
        assert score > score_balanced


# =====================================================================
# score_item — Socket Gate
# =====================================================================


class TestSocketGate:
    def test_no_socket_rejected_at_high_level(self) -> None:
        old = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.INTELLIGENCE, 50)]
        )
        new = _item(
            gem_slot=GemSlot.NONE, attrs=[(ItemAttributeType.INTELLIGENCE, 200)]
        )
        score = score_item(
            new,
            old,
            SOCKET_GATE_LEVEL,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        assert score == -float("inf")

    def test_gains_socket_auto_win(self) -> None:
        old = _item(
            gem_slot=GemSlot.NONE, attrs=[(ItemAttributeType.INTELLIGENCE, 200)]
        )
        new = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.INTELLIGENCE, 50)]
        )
        score = score_item(
            new,
            old,
            SOCKET_GATE_LEVEL,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        assert score == float("inf")

    def test_socket_irrelevant_below_level(self) -> None:
        old = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.INTELLIGENCE, 50)]
        )
        new = _item(
            gem_slot=GemSlot.NONE, attrs=[(ItemAttributeType.INTELLIGENCE, 200)]
        )
        score = score_item(
            new,
            old,
            SOCKET_GATE_LEVEL - 1,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        # Below gate level, the higher attr item should win despite no socket
        assert score > 0

    def test_socket_with_off_attrs_rejected(self) -> None:
        """At lv25+, socketed item with only off-attributes is rejected over non-socketed."""
        old = _item(
            gem_slot=GemSlot.NONE, attrs=[(ItemAttributeType.INTELLIGENCE, 200)]
        )
        new = _item(gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.STRENGTH, 50)])
        score = score_item(
            new,
            old,
            SOCKET_GATE_LEVEL,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        assert score == -float("inf")

    def test_socket_with_con_auto_wins(self) -> None:
        """Socketed item with constitution auto-wins over non-socketed."""
        old = _item(
            gem_slot=GemSlot.NONE, attrs=[(ItemAttributeType.INTELLIGENCE, 200)]
        )
        new = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.CONSTITUTION, 50)]
        )
        score = score_item(
            new,
            old,
            SOCKET_GATE_LEVEL,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        assert score == float("inf")

    def test_no_socket_always_rejected_even_vs_off_attrs(self) -> None:
        """At lv25+, non-socketed item is always rejected even if current has off-attributes."""
        old = _item(gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.STRENGTH, 50)])
        new = _item(
            gem_slot=GemSlot.NONE, attrs=[(ItemAttributeType.INTELLIGENCE, 200)]
        )
        score = score_item(
            new,
            old,
            SOCKET_GATE_LEVEL,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        assert score == -float("inf")

    def test_no_socket_rejected_even_vs_empty_slot(self) -> None:
        """At lv25+, non-socketed item is rejected even into an empty slot."""
        new = _item(gem_slot=GemSlot.NONE, attrs=[(ItemAttributeType.INTELLIGENCE, 50)])
        score = score_item(
            new,
            None,
            SOCKET_GATE_LEVEL,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        assert score == -float("inf")

    def test_socketed_item_vs_empty_slot_no_inf(self) -> None:
        """Socketed item into empty slot should NOT return inf — just normal positive."""
        new = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.INTELLIGENCE, 50)]
        )
        score = score_item(
            new,
            None,
            SOCKET_GATE_LEVEL,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        assert score > 0
        assert score != float("inf")


# =====================================================================
# score_item — Weapon
# =====================================================================


class TestScoreItemWeapon:
    def test_higher_damage_positive(self) -> None:
        old = _item(item_type=ItemType.WEAPON, min_dmg=400, max_dmg=600)
        new = _item(item_type=ItemType.WEAPON, min_dmg=450, max_dmg=650)
        score = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), _balanced_attrs(), MAGE_TARGETS
        )
        assert score > 0

    def test_lower_damage_negative(self) -> None:
        old = _item(item_type=ItemType.WEAPON, min_dmg=450, max_dmg=650)
        new = _item(item_type=ItemType.WEAPON, min_dmg=400, max_dmg=600)
        score = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), _balanced_attrs(), MAGE_TARGETS
        )
        assert score < 0

    def test_less_dmg_more_main_stat_trade_off(self) -> None:
        """Extra main attr on weapon boosts projected damage."""
        old = _item(
            item_type=ItemType.WEAPON,
            min_dmg=490,
            max_dmg=510,
            attrs=[(ItemAttributeType.INTELLIGENCE, 100)],
        )
        new = _item(
            item_type=ItemType.WEAPON,
            min_dmg=480,
            max_dmg=520,
            attrs=[(ItemAttributeType.INTELLIGENCE, 1000)],
        )
        score = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), _balanced_attrs(), MAGE_TARGETS
        )
        # +900 INT on 500 avg dmg weapon = large projected damage gain
        assert score > 0

    def test_con_weapon_rejected_when_overweight_con(self) -> None:
        """A weapon that drops damage for con is bad when con is already high."""
        heavy_con = {
            Attribute.INTELLIGENCE: 2000,
            Attribute.CONSTITUTION: 7000,
            Attribute.LUCK: 500,
            Attribute.STRENGTH: 250,
            Attribute.DEXTERITY: 250,
        }
        old = _item(
            item_type=ItemType.WEAPON,
            min_dmg=490,
            max_dmg=510,
            attrs=[(ItemAttributeType.INTELLIGENCE, 100)],
        )
        new = _item(
            item_type=ItemType.WEAPON,
            min_dmg=400,
            max_dmg=420,
            attrs=[(ItemAttributeType.CONSTITUTION, 500)],
        )
        score = score_item(
            new, old, 30, MAIN_ATTR, heavy_con, _balanced_attrs(), MAGE_TARGETS
        )
        assert score < 0


# =====================================================================
# score_item — Shield
# =====================================================================


class TestScoreItemShield:
    def test_higher_block_positive(self) -> None:
        old = _item(
            item_type=ItemType.SHIELD,
            block_chance=20,
            attrs=[(ItemAttributeType.CONSTITUTION, 100)],
        )
        new = _item(
            item_type=ItemType.SHIELD,
            block_chance=30,
            attrs=[(ItemAttributeType.CONSTITUTION, 100)],
        )
        score = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), _balanced_attrs(), MAGE_TARGETS
        )
        assert score > 0

    def test_block_scales_with_con(self) -> None:
        """More total con makes block value higher."""
        old = _item(item_type=ItemType.SHIELD, block_chance=20)
        new = _item(item_type=ItemType.SHIELD, block_chance=30)
        low_con_char = dict(_balanced_attrs())
        low_con_char[Attribute.CONSTITUTION] = 1000
        high_con_char = dict(_balanced_attrs())
        high_con_char[Attribute.CONSTITUTION] = 5000
        score_low = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), low_con_char, MAGE_TARGETS
        )
        score_high = score_item(
            new, old, 30, MAIN_ATTR, _balanced_attrs(), high_con_char, MAGE_TARGETS
        )
        assert score_high > score_low


# =====================================================================
# score_gem
# =====================================================================


class TestScoreGem:
    def test_main_attr_gem_valued_highest_when_balanced(self) -> None:
        """Main attr gem scores higher than con gem when gems are balanced."""
        gem_attrs = _gem_attrs(
            {Attribute.INTELLIGENCE: 600, Attribute.CONSTITUTION: 400}
        )
        score_main = score_gem(
            GemAttr.INTELLIGENCE, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        score_con = score_gem(
            GemAttr.CONSTITUTION, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        assert score_main > score_con

    def test_con_gem_boosted_when_all_main(self) -> None:
        """When all gems are main attr, con gem gets huge correction."""
        gem_attrs = _gem_attrs({Attribute.INTELLIGENCE: 1000})
        score_con = score_gem(
            GemAttr.CONSTITUTION, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        score_main = score_gem(
            GemAttr.INTELLIGENCE, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        assert score_con > score_main

    def test_no_gems_prefers_main(self) -> None:
        """With no gems equipped, main attr is still preferred."""
        gem_attrs = _gem_attrs()
        score_main = score_gem(
            GemAttr.INTELLIGENCE, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        score_con = score_gem(
            GemAttr.CONSTITUTION, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        assert score_main > score_con

    def test_legendary_scores_main_plus_con(self) -> None:
        """Legendary gem scores as main attr + constitution, not all attrs."""
        gem_attrs = _gem_attrs(
            {Attribute.INTELLIGENCE: 600, Attribute.CONSTITUTION: 400}
        )
        score_leg = score_gem(
            GemAttr.LEGENDARY, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        score_main = score_gem(
            GemAttr.INTELLIGENCE, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        score_con = score_gem(
            GemAttr.CONSTITUTION, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        # Legendary = main + con correction combined
        assert score_leg == pytest.approx(score_main + score_con, rel=1e-6)

    def test_legendary_does_not_include_off_attrs(self) -> None:
        """Legendary gem should NOT include off-attr corrections."""
        gem_attrs = _gem_attrs(
            {Attribute.INTELLIGENCE: 600, Attribute.CONSTITUTION: 400}
        )
        score_leg = score_gem(
            GemAttr.LEGENDARY, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        score_all = score_gem(GemAttr.BLACK, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs)
        # ALL (black gem) includes all 5 attributes, legendary only 2
        assert score_all > score_leg

    def test_off_stat_gem_low_value(self) -> None:
        """Strength gem on a mage has very low value once STR is represented."""
        # Give STR some existing gems so the floor doesn't dominate.
        # With 0 STR gems, the correction skyrockets (self-rebalancing),
        # which is correct — after one STR gem is socketed the ratio
        # rises and subsequent STR gems score much lower.
        gem_attrs = _gem_attrs(
            {
                Attribute.INTELLIGENCE: 600,
                Attribute.CONSTITUTION: 350,
                Attribute.STRENGTH: 50,
            }
        )
        score_off = score_gem(GemAttr.STRENGTH, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs)
        score_main = score_gem(
            GemAttr.INTELLIGENCE, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        assert score_off < score_main


# =====================================================================
# score_item_best — multi-profile
# =====================================================================


class TestScoreItemBest:
    def test_single_profile_upgrade_detected(self) -> None:
        old = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 100)])
        new = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 200)])
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            )
        ]
        session = _mock_session(equipped={2: old})  # slot 2 = BREASTPLATE
        winner, best_score = score_item_best(
            new, 30, load_equipped_data(session, profiles)
        )
        assert winner is not None
        assert best_score > 0

    def test_bad_for_main_good_for_helper(self) -> None:
        """Item bad for mage but good for warrior helper scores positive."""
        old_main = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 200)])
        old_warrior = _item(attrs=[(ItemAttributeType.STRENGTH, 50)])
        new = _item(attrs=[(ItemAttributeType.STRENGTH, 300)])
        warrior_targets: dict[Attribute, float] = {
            Attribute.STRENGTH: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.INTELLIGENCE: 0.05,
            Attribute.DEXTERITY: 0.05,
        }
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                warrior_targets,
                warrior_targets,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        session = _mock_session(
            equipped={2: old_main},
            companion_equipped={CompanionClass.WARRIOR: {2: old_warrior}},
        )
        # Bad for mage (loses INT, gains STR)
        score_mage = score_item(
            new,
            old_main,
            30,
            MAIN_ATTR,
            _balanced_attrs(),
            _balanced_attrs(),
            MAGE_TARGETS,
        )
        assert score_mage < 0
        # But best across profiles should be positive (good for warrior)
        winner, best_score = score_item_best(
            new, 30, load_equipped_data(session, profiles)
        )
        assert winner is not None
        assert winner.companion == CompanionClass.WARRIOR
        assert best_score > 0


# =====================================================================
# score_item_best — class filtering
# =====================================================================


class TestScoreItemBestClassFilter:
    def test_mage_weapon_rejected_for_warrior(self) -> None:
        """A mage weapon cannot be equipped by a warrior profile."""
        old = _item(item_type=ItemType.WEAPON, min_dmg=400, max_dmg=600)
        new = _item(
            item_type=ItemType.WEAPON,
            min_dmg=500,
            max_dmg=700,
            char_class=CharClass.MAGE,
        )
        warrior_targets: dict[Attribute, float] = {
            Attribute.STRENGTH: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.INTELLIGENCE: 0.05,
            Attribute.DEXTERITY: 0.05,
        }
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                warrior_targets,
                warrior_targets,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        session = _mock_session(
            companion_equipped={CompanionClass.WARRIOR: {9: old}},
        )
        winner, best_score = score_item_best(
            new, 30, load_equipped_data(session, profiles)
        )
        assert winner is None
        assert best_score == -float("inf")

    def test_mage_weapon_accepted_for_mage(self) -> None:
        """A mage weapon can be equipped by a mage profile."""
        old = _item(item_type=ItemType.WEAPON, min_dmg=400, max_dmg=600)
        new = _item(
            item_type=ItemType.WEAPON,
            min_dmg=500,
            max_dmg=700,
            char_class=CharClass.MAGE,
        )
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
        ]
        session = _mock_session(equipped={9: old})  # slot 9 = WEAPON
        winner, best_score = score_item_best(
            new, 30, load_equipped_data(session, profiles)
        )
        assert winner is not None
        assert best_score > 0

    def test_mage_weapon_found_by_helper(self) -> None:
        """Mage weapon bad for warrior but found by mage helper."""
        old_warrior = _item(item_type=ItemType.WEAPON, min_dmg=400, max_dmg=600)
        old_mage = _item(item_type=ItemType.WEAPON, min_dmg=400, max_dmg=600)
        new = _item(
            item_type=ItemType.WEAPON,
            min_dmg=500,
            max_dmg=700,
            char_class=CharClass.MAGE,
        )
        warrior_targets: dict[Attribute, float] = {
            Attribute.STRENGTH: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.INTELLIGENCE: 0.05,
            Attribute.DEXTERITY: 0.05,
        }
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                warrior_targets,
                warrior_targets,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.MAGE,
            ),
        ]
        session = _mock_session(
            equipped={9: old_warrior},
            companion_equipped={CompanionClass.MAGE: {9: old_mage}},
        )
        winner, best_score = score_item_best(
            new, 30, load_equipped_data(session, profiles)
        )
        assert winner is not None
        assert winner.companion == CompanionClass.MAGE
        assert best_score > 0

    def test_universal_item_available_to_all(self) -> None:
        """Items with char_class=None can be equipped by any profile."""
        old = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 100)])
        new = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 200)])
        warrior_targets: dict[Attribute, float] = {
            Attribute.STRENGTH: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.INTELLIGENCE: 0.05,
            Attribute.DEXTERITY: 0.05,
        }
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                warrior_targets,
                warrior_targets,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
        ]
        session = _mock_session(
            equipped={2: old},
            companion_equipped={CompanionClass.WARRIOR: {2: old}},
        )
        winner, best_score = score_item_best(
            new, 30, load_equipped_data(session, profiles)
        )
        assert winner is not None
        assert best_score > 0

    def test_companion_cannot_equip_shield(self) -> None:
        """Companions cannot equip shields."""
        new = _item(
            item_type=ItemType.SHIELD,
            block_chance=30,
            attrs=[(ItemAttributeType.CONSTITUTION, 200)],
        )
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                {a: 0.2 for a in Attribute},
                {a: 0.2 for a in Attribute},
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        session = _mock_session()
        winner, best_score = score_item_best(
            new, 30, load_equipped_data(session, profiles)
        )
        assert winner is None
        assert best_score == -float("inf")


# =====================================================================
# score_gem_best — multi-profile gem comparison
# =====================================================================


class TestScoreGemBest:
    def test_int_gem_scored_by_mage_not_warrior(self) -> None:
        """INT gem valued much higher by mage profile than warrior."""
        warrior_targets: dict[Attribute, float] = {
            Attribute.STRENGTH: 0.45,
            Attribute.CONSTITUTION: 0.30,
            Attribute.LUCK: 0.15,
            Attribute.INTELLIGENCE: 0.05,
            Attribute.DEXTERITY: 0.05,
        }
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                warrior_targets,
                warrior_targets,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
        ]
        gem_attrs = _gem_attrs({Attribute.STRENGTH: 500})
        best = score_gem_best(GemAttr.INTELLIGENCE, 100, profiles, gem_attrs)
        # The mage profile should dominate
        mage_only = score_gem(
            GemAttr.INTELLIGENCE, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        assert best == mage_only

    def test_warrior_zero_int_gems_does_not_hijack(self) -> None:
        """Warrior with 0 INT gems should NOT outscore mage for INT gem."""
        warrior_targets: dict[Attribute, float] = {
            Attribute.STRENGTH: 0.53,
            Attribute.CONSTITUTION: 0.38,
            Attribute.LUCK: 0.05,
            Attribute.INTELLIGENCE: 0.02,
            Attribute.DEXTERITY: 0.02,
        }
        gem_attrs = _gem_attrs({Attribute.STRENGTH: 1000})  # warrior has STR gems only
        warrior_score = score_gem(
            GemAttr.INTELLIGENCE, 100, Attribute.STRENGTH, warrior_targets, gem_attrs
        )
        mage_score = score_gem(
            GemAttr.INTELLIGENCE, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        # Mage values INT gem far more despite warrior having 0 INT gems
        assert mage_score > warrior_score

    def test_empty_profiles_returns_zero(self) -> None:
        assert score_gem_best(GemAttr.INTELLIGENCE, 100, [], _gem_attrs()) == 0.0


# =====================================================================
# Companion-specific scenarios
# =====================================================================

WARRIOR_TARGETS: dict[Attribute, float] = {
    Attribute.STRENGTH: 0.45,
    Attribute.CONSTITUTION: 0.30,
    Attribute.LUCK: 0.15,
    Attribute.INTELLIGENCE: 0.05,
    Attribute.DEXTERITY: 0.05,
}

SCOUT_TARGETS: dict[Attribute, float] = {
    Attribute.DEXTERITY: 0.45,
    Attribute.CONSTITUTION: 0.30,
    Attribute.LUCK: 0.15,
    Attribute.STRENGTH: 0.05,
    Attribute.INTELLIGENCE: 0.05,
}


class TestCompanionEquipment:
    """Tests for companion equipment parsing and scoring."""

    def test_companion_equipment_isolated(self) -> None:
        """Each companion scores against its own equipped items, not main."""
        old_main = _item(attrs=[(ItemAttributeType.INTELLIGENCE, 500)])
        old_companion = _item(attrs=[(ItemAttributeType.STRENGTH, 50)])
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        session = _mock_session(
            equipped={2: old_main},
            companion_equipped={CompanionClass.WARRIOR: {2: old_companion}},
        )
        equipped_data = load_equipped_data(session, profiles)
        # Main profile uses main's equipped (INT=500)
        assert equipped_data[0].item_attrs[Attribute.INTELLIGENCE] == 500
        # Warrior profile uses companion's equipped (STR=50)
        assert equipped_data[1].item_attrs[Attribute.STRENGTH] == 50

    def test_companion_only_profile_works(self) -> None:
        """Scoring works with only companion profiles (no main)."""
        old = _item(attrs=[(ItemAttributeType.STRENGTH, 100)])
        new = _item(attrs=[(ItemAttributeType.STRENGTH, 300)])
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        session = _mock_session(
            companion_equipped={CompanionClass.WARRIOR: {2: old}},
        )
        winner, score = score_item_best(new, 30, load_equipped_data(session, profiles))
        assert winner is not None
        assert winner.companion == CompanionClass.WARRIOR
        assert score > 0

    def test_multiple_companions_best_wins(self) -> None:
        """When multiple companions benefit, the one with highest score wins."""
        old_warrior = _item(attrs=[(ItemAttributeType.STRENGTH, 200)])
        old_scout = _item(attrs=[(ItemAttributeType.DEXTERITY, 50)])
        # New item has DEX — useless for warrior, great for scout
        new = _item(attrs=[(ItemAttributeType.DEXTERITY, 300)])
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
            ComparisonProfile(
                CharClass.SCOUT,
                Attribute.DEXTERITY,
                SCOUT_TARGETS,
                SCOUT_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.SCOUT,
            ),
        ]
        session = _mock_session(
            companion_equipped={
                CompanionClass.WARRIOR: {2: old_warrior},
                CompanionClass.SCOUT: {2: old_scout},
            },
        )
        winner, score = score_item_best(new, 30, load_equipped_data(session, profiles))
        assert winner is not None
        assert winner.companion == CompanionClass.SCOUT
        assert score > 0

    def test_companion_empty_slot_scores_positive(self) -> None:
        """Item into an empty companion slot is always an upgrade."""
        new = _item(attrs=[(ItemAttributeType.STRENGTH, 100)])
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        # No companion equipment at all
        session = _mock_session()
        winner, score = score_item_best(new, 10, load_equipped_data(session, profiles))
        assert winner is not None
        assert score > 0

    def test_weapon_class_mismatch_across_companions(self) -> None:
        """A warrior weapon is accepted by warrior companion but rejected by scout."""
        old = _item(item_type=ItemType.WEAPON, min_dmg=400, max_dmg=600)
        new = _item(
            item_type=ItemType.WEAPON,
            min_dmg=500,
            max_dmg=700,
            char_class=CharClass.WARRIOR,
        )
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
            ComparisonProfile(
                CharClass.SCOUT,
                Attribute.DEXTERITY,
                SCOUT_TARGETS,
                SCOUT_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.SCOUT,
            ),
        ]
        session = _mock_session(
            companion_equipped={
                CompanionClass.WARRIOR: {9: old},
                CompanionClass.SCOUT: {9: old},
            },
        )
        winner, score = score_item_best(new, 30, load_equipped_data(session, profiles))
        assert winner is not None
        assert winner.companion == CompanionClass.WARRIOR

    def test_shield_rejected_for_all_companions(self) -> None:
        """Shields cannot be equipped by any companion."""
        new = _item(
            item_type=ItemType.SHIELD,
            block_chance=30,
            attrs=[(ItemAttributeType.CONSTITUTION, 500)],
        )
        profiles = [
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.MAGE,
            ),
            ComparisonProfile(
                CharClass.SCOUT,
                Attribute.DEXTERITY,
                SCOUT_TARGETS,
                SCOUT_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.SCOUT,
            ),
        ]
        session = _mock_session()
        winner, score = score_item_best(new, 30, load_equipped_data(session, profiles))
        assert winner is None
        assert score == -float("inf")

    def test_shield_accepted_for_main_rejected_for_companion(self) -> None:
        """Shield is valid for main character but not companion."""
        new = _item(
            item_type=ItemType.SHIELD,
            block_chance=30,
            attrs=[(ItemAttributeType.CONSTITUTION, 200)],
        )
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        session = _mock_session()
        winner, score = score_item_best(new, 10, load_equipped_data(session, profiles))
        assert winner is not None
        assert winner.companion is None  # main character

    def test_main_and_companion_both_benefit_main_wins_if_higher(self) -> None:
        """When both main and companion benefit, the higher score wins."""
        old_main = _item(attrs=[(ItemAttributeType.CONSTITUTION, 100)])
        old_companion = _item(attrs=[(ItemAttributeType.CONSTITUTION, 200)])
        # +300 CON item — bigger upgrade for main (gains 200) than companion (gains 100)
        new = _item(attrs=[(ItemAttributeType.CONSTITUTION, 300)])
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        session = _mock_session(
            equipped={2: old_main},
            companion_equipped={CompanionClass.WARRIOR: {2: old_companion}},
        )
        winner, score = score_item_best(new, 10, load_equipped_data(session, profiles))
        assert winner is not None
        assert winner.companion is None  # main gets more benefit

    def test_socket_gate_applies_per_companion(self) -> None:
        """Socket gate is evaluated per companion's equipped item."""
        # Main has socketed item, companion has no-socket item
        old_main_socketed = _item(
            gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.INTELLIGENCE, 100)]
        )
        old_companion_no_socket = _item(
            gem_slot=GemSlot.NONE, attrs=[(ItemAttributeType.STRENGTH, 100)]
        )
        # New socketed item with main attr
        new = _item(gem_slot=GemSlot.EMPTY, attrs=[(ItemAttributeType.STRENGTH, 50)])
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        session = _mock_session(
            equipped={2: old_main_socketed},
            companion_equipped={CompanionClass.WARRIOR: {2: old_companion_no_socket}},
        )
        winner, score = score_item_best(
            new,
            SOCKET_GATE_LEVEL,
            load_equipped_data(session, profiles),
        )
        # Companion with no-socket item gets +inf for gaining a socket
        assert winner is not None
        assert winner.companion == CompanionClass.WARRIOR
        assert score == float("inf")


class TestCompanionGemScoring:
    """Tests for gem scoring across companion profiles."""

    def test_str_gem_valued_by_warrior_not_mage(self) -> None:
        """STR gem scores highest for warrior companion, not mage."""
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        gem_attrs = _gem_attrs({Attribute.INTELLIGENCE: 500, Attribute.STRENGTH: 500})
        best = score_gem_best(GemAttr.STRENGTH, 100, profiles, gem_attrs)
        warrior_only = score_gem(
            GemAttr.STRENGTH, 100, Attribute.STRENGTH, WARRIOR_TARGETS, gem_attrs
        )
        assert best == warrior_only

    def test_con_gem_benefits_multiple_profiles(self) -> None:
        """CON gem is valued by both mage and warrior — best score used."""
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        gem_attrs = _gem_attrs({Attribute.INTELLIGENCE: 800, Attribute.STRENGTH: 200})
        score_both = score_gem_best(GemAttr.CONSTITUTION, 100, profiles, gem_attrs)
        score_mage = score_gem(
            GemAttr.CONSTITUTION, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs
        )
        score_warrior = score_gem(
            GemAttr.CONSTITUTION, 100, Attribute.STRENGTH, WARRIOR_TARGETS, gem_attrs
        )
        assert score_both == max(score_mage, score_warrior)

    def test_legendary_gem_per_profile_main_attr(self) -> None:
        """Legendary gem uses each profile's own main_attr for scoring."""
        profiles = [
            ComparisonProfile(
                CharClass.MAGE,
                MAIN_ATTR,
                MAGE_TARGETS,
                MAGE_TARGETS,
                base_attrs=_balanced_attrs(),
            ),
            ComparisonProfile(
                CharClass.WARRIOR,
                Attribute.STRENGTH,
                WARRIOR_TARGETS,
                WARRIOR_TARGETS,
                base_attrs=_balanced_attrs(),
                companion=CompanionClass.WARRIOR,
            ),
        ]
        gem_attrs = _gem_attrs({Attribute.INTELLIGENCE: 500, Attribute.STRENGTH: 500})
        mage_leg = score_gem(GemAttr.LEGENDARY, 100, MAIN_ATTR, MAGE_TARGETS, gem_attrs)
        warrior_leg = score_gem(
            GemAttr.LEGENDARY, 100, Attribute.STRENGTH, WARRIOR_TARGETS, gem_attrs
        )
        best = score_gem_best(GemAttr.LEGENDARY, 100, profiles, gem_attrs)
        assert best == max(mage_leg, warrior_leg)
