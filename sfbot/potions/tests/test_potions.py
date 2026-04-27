import pytest

from sfbot.constants import Attribute, PotionAttributeType, PotionSize
from sfbot.potions import ActivePotion, Potion


def _potion(attr: PotionAttributeType, size: PotionSize | None) -> Potion:
    """Create a Potion for testing should_drink."""
    return Potion(attr=attr, size=size)


class TestShouldDrink:
    """Potion.should_drink(main_attr) → True means drink immediately."""

    # ── Wings/HP is always kept ──

    def test_wings_never_drunk(self):
        p = _potion(PotionAttributeType.HP, None)
        for attr in Attribute:
            assert p.should_drink(attr) is False

    # ── Main attribute Large is kept ──

    def test_keep_main_attr_large_str(self):
        p = _potion(PotionAttributeType.STRENGTH, PotionSize.LARGE)
        assert p.should_drink(Attribute.STRENGTH) is False

    def test_keep_main_attr_large_int(self):
        p = _potion(PotionAttributeType.INTELLIGENCE, PotionSize.LARGE)
        assert p.should_drink(Attribute.INTELLIGENCE) is False

    def test_keep_main_attr_large_dex(self):
        p = _potion(PotionAttributeType.DEXTERITY, PotionSize.LARGE)
        assert p.should_drink(Attribute.DEXTERITY) is False

    # ── Main attribute Small/Medium are drunk ──

    def test_drink_main_attr_small(self):
        p = _potion(PotionAttributeType.STRENGTH, PotionSize.SMALL)
        assert p.should_drink(Attribute.STRENGTH) is True

    def test_drink_main_attr_medium(self):
        p = _potion(PotionAttributeType.STRENGTH, PotionSize.MEDIUM)
        assert p.should_drink(Attribute.STRENGTH) is True

    # ── Constitution Large is always kept ──

    def test_keep_constitution_large(self):
        p = _potion(PotionAttributeType.CONSTITUTION, PotionSize.LARGE)
        assert p.should_drink(Attribute.STRENGTH) is False
        assert p.should_drink(Attribute.DEXTERITY) is False
        assert p.should_drink(Attribute.INTELLIGENCE) is False

    # ── Constitution Small/Medium are drunk ──

    def test_drink_constitution_small(self):
        p = _potion(PotionAttributeType.CONSTITUTION, PotionSize.SMALL)
        assert p.should_drink(Attribute.STRENGTH) is True

    def test_drink_constitution_medium(self):
        p = _potion(PotionAttributeType.CONSTITUTION, PotionSize.MEDIUM)
        assert p.should_drink(Attribute.STRENGTH) is True

    # ── Off-attr potions are drunk ──

    def test_drink_off_attr_luck_for_warrior(self):
        p = _potion(PotionAttributeType.LUCK, PotionSize.SMALL)
        assert p.should_drink(Attribute.STRENGTH) is True

    def test_drink_off_attr_dex_for_mage(self):
        p = _potion(PotionAttributeType.DEXTERITY, PotionSize.MEDIUM)
        assert p.should_drink(Attribute.INTELLIGENCE) is True

    def test_drink_off_attr_str_large_for_scout(self):
        p = _potion(PotionAttributeType.STRENGTH, PotionSize.LARGE)
        assert p.should_drink(Attribute.DEXTERITY) is True

    # ── Parametric: all attr × size combos for off-attr ──

    @pytest.mark.parametrize("size", list(PotionSize))
    @pytest.mark.parametrize(
        "attr",
        [a for a in PotionAttributeType if a != PotionAttributeType.HP],
    )
    def test_off_attr_always_drunk_except_con_large(
        self, attr: PotionAttributeType, size: PotionSize
    ):
        p = _potion(attr, size)
        # Pick a main_attr that differs
        main = Attribute((attr.value + 1) % 5)
        if attr == PotionAttributeType.CONSTITUTION and size == PotionSize.LARGE:
            assert p.should_drink(main) is False
        else:
            assert p.should_drink(main) is True


class TestActivePotion:
    def test_fields(self):
        pot = Potion(attr=PotionAttributeType.STRENGTH, size=PotionSize.LARGE)
        p = ActivePotion(potion=pot, expires=999, slot=1)
        assert p.potion.attr == PotionAttributeType.STRENGTH
        assert p.potion.size == PotionSize.LARGE
        assert p.expires == 999

    def test_wings_no_size(self):
        pot = Potion(attr=PotionAttributeType.HP, size=None)
        p = ActivePotion(potion=pot, expires=1000, slot=2)
        assert p.potion.attr == PotionAttributeType.HP
        assert p.potion.size is None

    def test_attr_is_enum(self):
        pot = Potion(attr=PotionAttributeType.DEXTERITY, size=PotionSize.SMALL)
        p = ActivePotion(potion=pot, expires=0, slot=1)
        assert isinstance(p.potion.attr, PotionAttributeType)
        assert p.potion.attr.name == "DEXTERITY"

    def test_size_is_enum(self):
        pot = Potion(attr=PotionAttributeType.LUCK, size=PotionSize.MEDIUM)
        p = ActivePotion(potion=pot, expires=0, slot=3)
        assert isinstance(p.potion.size, PotionSize)
        assert p.potion.size.name == "MEDIUM"


class TestCanDrink:
    """Potion.can_drink(active_size) — can drink if new size >= active size."""

    # ── HP/Wings: always drinkable (no size prerequisite) ──

    def test_hp_always(self):
        p = _potion(PotionAttributeType.HP, None)
        assert p.can_drink(PotionSize.SMALL) is True
        assert p.can_drink(PotionSize.LARGE) is True

    # ── SMALL: blocked by same or bigger active ──

    def test_small_blocked_by_same_size(self):
        p = _potion(PotionAttributeType.LUCK, PotionSize.SMALL)
        assert p.can_drink(PotionSize.SMALL) is True

    def test_small_blocked_by_bigger(self):
        p = _potion(PotionAttributeType.LUCK, PotionSize.SMALL)
        assert p.can_drink(PotionSize.MEDIUM) is False
        assert p.can_drink(PotionSize.LARGE) is False

    # ── MEDIUM: can drink over small or same ──

    def test_medium_with_small_active(self):
        p = _potion(PotionAttributeType.STRENGTH, PotionSize.MEDIUM)
        assert p.can_drink(PotionSize.SMALL) is True

    def test_medium_with_same_active(self):
        p = _potion(PotionAttributeType.STRENGTH, PotionSize.MEDIUM)
        assert p.can_drink(PotionSize.MEDIUM) is True

    def test_medium_blocked_by_large(self):
        p = _potion(PotionAttributeType.STRENGTH, PotionSize.MEDIUM)
        assert p.can_drink(PotionSize.LARGE) is False

    # ── LARGE: can always drink over any active ──

    def test_large_with_small_active(self):
        p = _potion(PotionAttributeType.DEXTERITY, PotionSize.LARGE)
        assert p.can_drink(PotionSize.SMALL) is True

    def test_large_with_medium_active(self):
        p = _potion(PotionAttributeType.DEXTERITY, PotionSize.LARGE)
        assert p.can_drink(PotionSize.MEDIUM) is True

    def test_large_with_same_active(self):
        p = _potion(PotionAttributeType.DEXTERITY, PotionSize.LARGE)
        assert p.can_drink(PotionSize.LARGE) is True

    # ── Parametric: all attr × size ──

    @pytest.mark.parametrize("size", list(PotionSize))
    @pytest.mark.parametrize("active", list(PotionSize))
    def test_with_active(self, size: PotionSize, active: PotionSize):
        p = _potion(PotionAttributeType.LUCK, size)
        assert p.can_drink(active) is (not (size < active))
