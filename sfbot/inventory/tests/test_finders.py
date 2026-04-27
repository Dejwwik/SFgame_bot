from sfbot.constants import (
    GemAttr,
    ItemType,
    PotionAttributeType,
    PotionSize,
    Rarity,
)
from sfbot.inventory.inventory import get_max_potion_size

from .conftest import make_gem, make_gemmed_item, make_inventory, make_item, make_potion

_KEEP_POTIONS = {PotionAttributeType.STRENGTH, PotionAttributeType.CONSTITUTION}
_KEEP_GEMS = {GemAttr.STRENGTH, GemAttr.CONSTITUTION}

# ── get_max_potion_size ──


class TestMaxPotionSize:
    def test_low_level_returns_small(self):
        assert get_max_potion_size(1) == PotionSize.SMALL
        assert get_max_potion_size(9) == PotionSize.SMALL

    def test_medium_level(self):
        assert get_max_potion_size(10) == PotionSize.MEDIUM
        assert get_max_potion_size(14) == PotionSize.MEDIUM

    def test_high_level_returns_large(self):
        assert get_max_potion_size(15) == PotionSize.LARGE
        assert get_max_potion_size(100) == PotionSize.LARGE


# ── get_free_slot ──


class TestFindFreeSlot:
    def test_empty_backpack_returns_first(self):
        inv = make_inventory([None, None])
        slot = inv.get_free_slot()
        assert slot is not None
        assert slot.index == 0

    def test_full_backpack_returns_none(self):
        inv = make_inventory([make_item(), make_item()])
        assert inv.get_free_slot() is None

    def test_mixed_returns_first_empty(self):
        inv = make_inventory([make_item(), None, make_item()])
        slot = inv.get_free_slot()
        assert slot is not None
        assert slot.index == 1

    def test_has_free_slot_true(self):
        inv = make_inventory([None])
        assert inv.has_free_slot() is True

    def test_has_free_slot_false(self):
        inv = make_inventory([make_item()])
        assert inv.has_free_slot() is False


# ── get_gems ──


class TestFindGems:
    def test_no_gems(self):
        inv = make_inventory([make_item(), None])
        assert inv.get_gems() == []

    def test_finds_gems_only(self):
        inv = make_inventory(
            [make_gem(GemAttr.STRENGTH), make_item(), make_gem(GemAttr.LUCK)]
        )
        gems = inv.get_gems()
        assert len(gems) == 2
        assert gems[0].item is not None
        assert gems[0].item.gem_attr == GemAttr.STRENGTH
        assert gems[1].item is not None
        assert gems[1].item.gem_attr == GemAttr.LUCK

    def test_skips_empty_slots(self):
        inv = make_inventory([None, make_gem()])
        gems = inv.get_gems()
        assert len(gems) == 1


# ── get_washable_items ──


class TestGetWashableItems:
    def test_unwashed_equippable_returned(self):
        inv = make_inventory([make_item(washed=False)])
        assert len(inv.get_washable_items()) == 1

    def test_washed_items_skipped(self):
        inv = make_inventory([make_item(washed=True)])
        assert len(inv.get_washable_items()) == 0

    def test_non_equippable_skipped(self):
        inv = make_inventory([make_item(item_type=ItemType.POTION, washed=False)])
        assert len(inv.get_washable_items()) == 0

    def test_gems_skipped(self):
        inv = make_inventory([make_gem()])
        assert len(inv.get_washable_items()) == 0

    def test_empty_slots_skipped(self):
        inv = make_inventory([None])
        assert len(inv.get_washable_items()) == 0


# ── get_off_attr_potion / get_sub_max_potion ──


class TestGetOffAttrPotion:
    def test_off_attr_potion_found(self):
        inv = make_inventory([make_potion(PotionAttributeType.DEXTERITY)])
        assert inv.get_off_attr_potion(_KEEP_POTIONS) is not None

    def test_main_attr_not_returned(self):
        inv = make_inventory([make_potion(PotionAttributeType.STRENGTH)])
        assert inv.get_off_attr_potion(_KEEP_POTIONS) is None

    def test_constitution_not_returned(self):
        inv = make_inventory([make_potion(PotionAttributeType.CONSTITUTION)])
        assert inv.get_off_attr_potion(_KEEP_POTIONS) is None

    def test_empty_inventory_returns_none(self):
        inv = make_inventory([None])
        assert inv.get_off_attr_potion(_KEEP_POTIONS) is None


class TestGetSubMaxPotion:
    def test_sub_max_main_potion_found(self):
        inv = make_inventory(
            [make_potion(PotionAttributeType.STRENGTH, PotionSize.SMALL)]
        )
        assert inv.get_sub_max_potion(_KEEP_POTIONS, PotionSize.LARGE) is not None

    def test_max_size_main_potion_not_returned(self):
        inv = make_inventory(
            [make_potion(PotionAttributeType.STRENGTH, PotionSize.LARGE)]
        )
        assert inv.get_sub_max_potion(_KEEP_POTIONS, PotionSize.LARGE) is None

    def test_empty_inventory_returns_none(self):
        inv = make_inventory([None])
        assert inv.get_sub_max_potion(_KEEP_POTIONS, PotionSize.LARGE) is None


# ── get_sellable_gem ──


class TestFindSellableGem:
    def test_unprotected_gem_found(self):
        inv = make_inventory([make_gem(GemAttr.DEXTERITY)])
        result = inv.get_sellable_gem({GemAttr.STRENGTH, GemAttr.CONSTITUTION})
        assert result is not None
        assert result.item is not None
        assert result.item.gem_attr == GemAttr.DEXTERITY

    def test_protected_gem_skipped(self):
        inv = make_inventory([make_gem(GemAttr.STRENGTH)])
        assert inv.get_sellable_gem({GemAttr.STRENGTH}) is None

    def test_all_protected_returns_none(self):
        inv = make_inventory([make_gem(GemAttr.STRENGTH), make_gem(GemAttr.DEXTERITY)])
        assert inv.get_sellable_gem({GemAttr.STRENGTH, GemAttr.DEXTERITY}) is None

    def test_legendary_gem_always_skipped(self):
        inv = make_inventory([make_gem(GemAttr.LEGENDARY)])
        assert inv.get_sellable_gem(set()) is None

    def test_no_gems_returns_none(self):
        inv = make_inventory([make_item()])
        assert inv.get_sellable_gem(set()) is None


# ── get_sellable_item ──


class TestFindSellableItem:
    def test_matching_rarity_found(self):
        inv = make_inventory([make_item(rarity=Rarity.NORMAL)])
        assert inv.get_sellable_item(Rarity.NORMAL, set()) is not None

    def test_wrong_rarity_skipped(self):
        inv = make_inventory([make_item(rarity=Rarity.EPIC)])
        assert inv.get_sellable_item(Rarity.NORMAL, set()) is None

    def test_item_with_protected_gem_skipped(self):
        inv = make_inventory([make_gemmed_item(GemAttr.STRENGTH)])
        assert inv.get_sellable_item(Rarity.NORMAL, {GemAttr.STRENGTH}) is None

    def test_item_with_unprotected_gem_found(self):
        inv = make_inventory([make_gemmed_item(GemAttr.DEXTERITY)])
        assert inv.get_sellable_item(Rarity.NORMAL, {GemAttr.STRENGTH}) is not None

    def test_non_equippable_skipped(self):
        inv = make_inventory([make_potion()])
        assert inv.get_sellable_item(Rarity.NORMAL, set()) is None


# ── get_item_to_dismantle ──


class TestFindItemToDismantle:
    def test_normal_item_found(self):
        inv = make_inventory([make_item()])
        assert inv.get_item_to_dismantle(100.0) is not None

    def test_legendary_gem_item_skipped(self):
        inv = make_inventory([make_gemmed_item(GemAttr.LEGENDARY, power=500)])
        assert inv.get_item_to_dismantle(100.0) is None

    def test_good_black_gem_item_skipped(self):
        inv = make_inventory([make_gemmed_item(GemAttr.BLACK, power=200)])
        # threshold = 100, ratio = 0.66, so keep if power >= 100 * 0.66 = 66
        assert inv.get_item_to_dismantle(100.0) is None

    def test_weak_black_gem_item_dismantled(self):
        inv = make_inventory([make_gemmed_item(GemAttr.BLACK, power=10)])
        # threshold = 100, ratio = 0.66, keep if power >= 66. 10 < 66.
        assert inv.get_item_to_dismantle(100.0) is not None

    def test_returns_first_when_multiple(self):
        inv = make_inventory(
            [
                make_item(rarity=Rarity.NORMAL),
                make_item(rarity=Rarity.NORMAL),
            ]
        )
        result = inv.get_item_to_dismantle(100.0)
        assert result is not None

    def test_non_equippable_skipped(self):
        inv = make_inventory([make_potion()])
        assert inv.get_item_to_dismantle(100.0) is None


# ── get_item_to_sacrifice ──


class TestFindItemToSacrifice:
    def test_prefers_gem_over_item(self):
        inv = make_inventory([make_item(), make_gem(GemAttr.DEXTERITY)])
        result = inv.get_item_to_sacrifice({GemAttr.STRENGTH})
        assert result is not None
        assert result.item is not None
        assert result.item.is_gem

    def test_falls_back_to_equippable_item(self):
        inv = make_inventory([make_item(), make_gem(GemAttr.STRENGTH)])
        result = inv.get_item_to_sacrifice({GemAttr.STRENGTH, GemAttr.DEXTERITY})
        assert result is not None
        assert result.item is not None
        assert not result.item.is_gem

    def test_skips_legendary_gem_items(self):
        inv = make_inventory([make_gemmed_item(GemAttr.LEGENDARY, power=500)])
        assert inv.get_item_to_sacrifice({GemAttr.STRENGTH}) is None

    def test_empty_inventory(self):
        inv = make_inventory([None])
        assert inv.get_item_to_sacrifice(set()) is None


# ── get_low_value_gem (restricted) ──


class TestFindLowValueStatGem:
    def test_low_value_gem_found(self):
        inv = make_inventory([make_gem(GemAttr.STRENGTH, gem_value=50)])
        assert inv.get_low_value_gem(100.0, restrict_to_attrs=_KEEP_GEMS) is not None

    def test_high_value_gem_skipped(self):
        inv = make_inventory([make_gem(GemAttr.STRENGTH, gem_value=200)])
        assert inv.get_low_value_gem(100.0, restrict_to_attrs=_KEEP_GEMS) is None

    def test_legendary_gem_excluded(self):
        inv = make_inventory([make_gem(GemAttr.LEGENDARY, gem_value=10)])
        assert (
            inv.get_low_value_gem(
                100.0, restrict_to_attrs={GemAttr.STRENGTH, GemAttr.LEGENDARY}
            )
            is None
        )

    def test_black_gem_excluded(self):
        inv = make_inventory([make_gem(GemAttr.BLACK, gem_value=10)])
        assert (
            inv.get_low_value_gem(
                100.0, restrict_to_attrs={GemAttr.STRENGTH, GemAttr.BLACK}
            )
            is None
        )

    def test_non_keep_gem_skipped(self):
        inv = make_inventory([make_gem(GemAttr.DEXTERITY, gem_value=10)])
        assert (
            inv.get_low_value_gem(100.0, restrict_to_attrs={GemAttr.STRENGTH}) is None
        )


# ── get_item_with_low_value_gem ──


class TestFindLowValueGemItem:
    def test_legendary_gem_item_skipped(self):
        inv = make_inventory([make_gemmed_item(GemAttr.LEGENDARY, power=10)])
        assert inv.get_item_with_low_value_gem(100.0) is None

    def test_non_all_gem_item_returned(self):
        inv = make_inventory([make_gemmed_item(GemAttr.STRENGTH, power=10)])
        assert inv.get_item_with_low_value_gem(100.0) is not None

    def test_low_value_black_gem_item_found(self):
        inv = make_inventory([make_gemmed_item(GemAttr.BLACK, power=10)])
        assert inv.get_item_with_low_value_gem(100.0) is not None

    def test_high_value_black_gem_item_skipped(self):
        inv = make_inventory([make_gemmed_item(GemAttr.BLACK, power=500)])
        assert inv.get_item_with_low_value_gem(100.0) is None

    def test_item_without_gem_skipped(self):
        inv = make_inventory([make_item()])
        assert inv.get_item_with_low_value_gem(100.0) is None


# ── get_low_value_gem ──


class TestFindLowValueGem:
    def test_legendary_gem_skipped(self):
        inv = make_inventory([make_gem(GemAttr.LEGENDARY, gem_value=10)])
        assert inv.get_low_value_gem(100.0, set()) is None

    def test_non_all_gem_returned(self):
        inv = make_inventory([make_gem(GemAttr.STRENGTH, gem_value=10)])
        assert inv.get_low_value_gem(100.0, set()) is not None

    def test_low_value_black_gem_found(self):
        inv = make_inventory([make_gem(GemAttr.BLACK, gem_value=10)])
        assert inv.get_low_value_gem(100.0, set()) is not None

    def test_high_value_black_gem_skipped(self):
        inv = make_inventory([make_gem(GemAttr.BLACK, gem_value=500)])
        assert inv.get_low_value_gem(100.0, set()) is None


# ── get_item_with_extractable_gem ──


class TestFindItemWithExtractableGem:
    KEEP: set[GemAttr] = {GemAttr.STRENGTH, GemAttr.CONSTITUTION, GemAttr.BLACK}

    def test_legendary_gem_extracted_above_threshold(self):
        # avg=100, threshold=100*0.65=65, power=100 >= 65 → extract
        inv = make_inventory([make_gemmed_item(GemAttr.LEGENDARY, power=100)])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is not None

    def test_weak_legendary_gem_skipped(self):
        # avg=100, threshold=100*0.65=65, power=1 < 65 → skip
        inv = make_inventory([make_gemmed_item(GemAttr.LEGENDARY, power=1)])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is None

    def test_valuable_black_gem_extracted(self):
        inv = make_inventory([make_gemmed_item(GemAttr.BLACK, power=500)])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is not None

    def test_weak_black_gem_skipped(self):
        inv = make_inventory([make_gemmed_item(GemAttr.BLACK, power=5)])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is None

    def test_valuable_main_attr_gem_extracted(self):
        inv = make_inventory([make_gemmed_item(GemAttr.STRENGTH, power=500)])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is not None

    def test_weak_main_attr_gem_skipped(self):
        inv = make_inventory([make_gemmed_item(GemAttr.STRENGTH, power=5)])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is None

    def test_off_attr_gem_skipped(self):
        inv = make_inventory([make_gemmed_item(GemAttr.LUCK, power=500)])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is None

    def test_item_without_gem_skipped(self):
        inv = make_inventory([make_item()])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is None

    def test_non_equippable_skipped(self):
        inv = make_inventory([make_potion()])
        assert inv.get_item_with_extractable_gem(100.0, self.KEEP) is None
