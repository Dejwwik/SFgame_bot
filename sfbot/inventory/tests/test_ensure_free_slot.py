import asyncio
from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sfbot.constants import GemAttr, PotionAttributeType, PotionSize, Rarity
from sfbot.exceptions import GemExtractedAlert, InventoryStuckError

from .conftest import make_gem, make_gemmed_item, make_inventory, make_item, make_potion


def _call_kwargs(
    *,
    main_potion_attr: PotionAttributeType = PotionAttributeType.INTELLIGENCE,
    max_potion_size: PotionSize = PotionSize.LARGE,
    smith: MagicMock | None = None,
    toilet: MagicMock | None = None,
    keep_gem_attrs: set[GemAttr] | None = None,
    average_single_attr_gem: float = 100.0,
    profiles: list | None = None,
    character: MagicMock | None = None,
) -> dict:
    if character is None:
        character = MagicMock()
        character.ensure_potion_slot_async = AsyncMock(return_value=False)
    return dict(
        main_potion_attr=main_potion_attr,
        max_potion_size=max_potion_size,
        smith=smith,
        toilet=toilet,
        keep_gem_attrs=keep_gem_attrs
        or {GemAttr.INTELLIGENCE, GemAttr.CONSTITUTION, GemAttr.BLACK},
        average_single_attr_gem=average_single_attr_gem,
        profiles=profiles or [],
        character=character,
    )


def _mock_smith(
    can_dismantle: bool = True, dismantle_ok: bool = True, extract_ok: bool = True
) -> MagicMock:
    smith = MagicMock()
    smith.can_dismantle = can_dismantle
    smith.dismantle_slot_async = AsyncMock(return_value=dismantle_ok)
    smith.extract_gem_from_slot_async = AsyncMock(return_value=extract_ok)
    return smith


def _mock_toilet(can_sacrifice: bool = True, sacrifice_ok: bool = True) -> MagicMock:
    toilet = MagicMock()
    toilet.can_sacrifice = can_sacrifice
    toilet.sacrifice_slot_async = AsyncMock(return_value=sacrifice_ok)
    return toilet


def _run(coro: Coroutine[Any, Any, bool]) -> bool:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestStage1Dismantle:
    def test_dismantles_item_when_smith_available(self):
        inv = make_inventory([make_item()])
        smith = _mock_smith()
        result = _run(inv.ensure_free_slot_async(**_call_kwargs(smith=smith)))
        assert result is True
        smith.dismantle_slot_async.assert_called_once()

    def test_skips_when_smith_cannot_dismantle(self):
        inv = make_inventory([make_item()])
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        smith = _mock_smith(can_dismantle=False)
        result = _run(inv.ensure_free_slot_async(**_call_kwargs(smith=smith)))
        assert result is True
        smith.dismantle_slot_async.assert_not_called()

    def test_skips_when_no_smith(self):
        inv = make_inventory([make_item()])
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(inv.ensure_free_slot_async(**_call_kwargs(smith=None)))
        assert result is True


class TestStage2ToiletSacrifice:
    def test_sacrifices_unprotected_gem(self):
        inv = make_inventory([make_gem(GemAttr.DEXTERITY)])
        toilet = _mock_toilet()
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(
                    toilet=toilet,
                    keep_gem_attrs={GemAttr.INTELLIGENCE, GemAttr.CONSTITUTION},
                )
            )
        )
        assert result is True
        toilet.sacrifice_slot_async.assert_called_once()

    def test_skips_protected_gem(self):
        inv = make_inventory([make_gem(GemAttr.INTELLIGENCE)])
        inv.sell_item_at_slot_async = AsyncMock(return_value=False)
        inv.force_socket_gem_async = AsyncMock(return_value=False)
        toilet = _mock_toilet()
        with pytest.raises(InventoryStuckError):
            _run(
                inv.ensure_free_slot_async(
                    **_call_kwargs(
                        toilet=toilet,
                        keep_gem_attrs={GemAttr.INTELLIGENCE, GemAttr.CONSTITUTION},
                    )
                )
            )
        toilet.sacrifice_slot_async.assert_not_called()


class TestStage3SellOffStatPotion:
    def test_sells_off_stat_potion(self):
        inv = make_inventory(
            [make_potion(PotionAttributeType.DEXTERITY, PotionSize.LARGE)]
        )
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(main_potion_attr=PotionAttributeType.INTELLIGENCE)
            )
        )
        assert result is True
        inv.sell_item_at_slot_async.assert_called_once()
        assert "[3]" in inv.sell_item_at_slot_async.call_args[0][1]

    def test_keeps_main_attr_potion(self):
        inv = make_inventory(
            [make_potion(PotionAttributeType.INTELLIGENCE, PotionSize.LARGE)]
        )
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        # Main attr large potion: not off-attr, not sub-max → falls through everything → raises
        with pytest.raises(InventoryStuckError):
            _run(
                inv.ensure_free_slot_async(
                    **_call_kwargs(main_potion_attr=PotionAttributeType.INTELLIGENCE)
                )
            )


class TestStage4SellSubMaxPotion:
    def test_sells_sub_max_main_potion(self):
        inv = make_inventory(
            [make_potion(PotionAttributeType.INTELLIGENCE, PotionSize.SMALL)]
        )
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(main_potion_attr=PotionAttributeType.INTELLIGENCE)
            )
        )
        assert result is True
        assert "[4]" in inv.sell_item_at_slot_async.call_args[0][1]


class TestStage5SellUnprotectedGem:
    def test_sells_unprotected_gem(self):
        inv = make_inventory([make_gem(GemAttr.DEXTERITY)])
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(
                    keep_gem_attrs={GemAttr.INTELLIGENCE, GemAttr.CONSTITUTION}
                )
            )
        )
        assert result is True
        assert "[5]" in inv.sell_item_at_slot_async.call_args[0][1]


class TestStage6And8SellNormalItems:
    def test_sells_normal_item(self):
        inv = make_inventory([make_item(rarity=Rarity.NORMAL)])
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(inv.ensure_free_slot_async(**_call_kwargs()))
        assert result is True
        label = inv.sell_item_at_slot_async.call_args[0][1]
        assert "[6]" in label or "[8]" in label

    def test_normal_item_with_protected_gem_falls_to_stage8(self):
        inv = make_inventory(
            [make_gemmed_item(GemAttr.INTELLIGENCE, power=100, rarity=Rarity.NORMAL)]
        )
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(
                    keep_gem_attrs={GemAttr.INTELLIGENCE, GemAttr.CONSTITUTION}
                )
            )
        )
        assert result is True
        # Stage 6 skips (INT in all_protected), stage 8 sells (INT not in precious_gems)
        assert "[8]" in inv.sell_item_at_slot_async.call_args[0][1]


class TestStage9SellLowValueStatGem:
    def test_sells_low_value_stat_gem(self):
        inv = make_inventory([make_gem(GemAttr.INTELLIGENCE, gem_value=5)])
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(
                    keep_gem_attrs={GemAttr.INTELLIGENCE, GemAttr.CONSTITUTION},
                    average_single_attr_gem=100.0,
                )
            )
        )
        assert result is True
        assert "[9]" in inv.sell_item_at_slot_async.call_args[0][1]


class TestStage10SellEpicLegendaryItems:
    def test_sells_epic_item(self):
        inv = make_inventory([make_item(rarity=Rarity.EPIC)])
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(inv.ensure_free_slot_async(**_call_kwargs()))
        assert result is True


class TestStage11SellGemsRelaxed:
    def test_sells_protected_attr_gem_at_relaxed_stage(self):
        inv = make_inventory([make_gem(GemAttr.CONSTITUTION, gem_value=500)])
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(
                    keep_gem_attrs={GemAttr.INTELLIGENCE, GemAttr.CONSTITUTION}
                )
            )
        )
        assert result is True
        assert "[11]" in inv.sell_item_at_slot_async.call_args[0][1]


class TestStage12DismantleLowValueGemItem:
    def test_dismantles_item_with_low_value_black_gem(self):
        # ALL gem power=50, avg=100: stage 1 skips (50 >= 0.66*100*0.66=43.56),
        # stage 12 finds (50 < 100*1.10*0.66=72.6)
        inv = make_inventory(
            [make_gemmed_item(GemAttr.BLACK, power=50, rarity=Rarity.EPIC)]
        )
        smith = _mock_smith()
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(smith=smith, average_single_attr_gem=100.0)
            )
        )
        assert result is True
        smith.dismantle_slot_async.assert_called_once()

    def test_sells_item_with_low_value_black_gem_no_smith(self):
        # EPIC item with low-value ALL gem, no smith → reaches stage 12 sell path
        inv = make_inventory(
            [make_gemmed_item(GemAttr.BLACK, power=5, rarity=Rarity.EPIC)]
        )
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(smith=None, average_single_attr_gem=100.0)
            )
        )
        assert result is True
        assert "[12]" in inv.sell_item_at_slot_async.call_args[0][1]


class TestStage13SellLowValueGem:
    def test_sells_low_value_black_gem(self):
        # ALL gem with value=5, avg=100: stages 2,5,9,11 skip (ALL in protected/precious),
        # stage 13 finds (5 < 100*1.10*0.66=72.6)
        inv = make_inventory([make_gem(GemAttr.BLACK, gem_value=5)])
        inv.sell_item_at_slot_async = AsyncMock(return_value=True)
        result = _run(
            inv.ensure_free_slot_async(
                **_call_kwargs(
                    keep_gem_attrs={
                        GemAttr.INTELLIGENCE,
                        GemAttr.CONSTITUTION,
                        GemAttr.BLACK,
                    },
                    average_single_attr_gem=100.0,
                )
            )
        )
        assert result is True
        assert "[13]" in inv.sell_item_at_slot_async.call_args[0][1]


class TestStage14ExtractGem:
    def test_extract_legendary_raises_gem_extracted_alert(self):
        inv = make_inventory([make_gemmed_item(GemAttr.LEGENDARY, power=100)])
        smith = _mock_smith(can_dismantle=False)
        with pytest.raises(GemExtractedAlert):
            _run(inv.ensure_free_slot_async(**_call_kwargs(smith=smith)))

    def test_extract_black_gem_raises_gem_extracted_alert(self):
        inv = make_inventory([make_gemmed_item(GemAttr.BLACK, power=500)])
        smith = _mock_smith(can_dismantle=False)
        with pytest.raises(GemExtractedAlert):
            _run(inv.ensure_free_slot_async(**_call_kwargs(smith=smith)))

    def test_no_extract_when_smith_absent(self):
        inv = make_inventory([make_gemmed_item(GemAttr.LEGENDARY, power=500)])
        inv.sell_item_at_slot_async = AsyncMock(return_value=False)
        inv.force_socket_gem_async = AsyncMock(return_value=False)
        with pytest.raises(InventoryStuckError):
            _run(inv.ensure_free_slot_async(**_call_kwargs(smith=None)))


class TestNothingToFree:
    def test_empty_inventory_raises(self):
        inv = make_inventory([None])
        with pytest.raises(InventoryStuckError):
            _run(inv.ensure_free_slot_async(**_call_kwargs()))

    def test_only_max_main_potion_raises(self):
        inv = make_inventory(
            [make_potion(PotionAttributeType.INTELLIGENCE, PotionSize.LARGE)]
        )
        inv.sell_item_at_slot_async = AsyncMock(return_value=False)
        with pytest.raises(InventoryStuckError):
            _run(
                inv.ensure_free_slot_async(
                    **_call_kwargs(main_potion_attr=PotionAttributeType.INTELLIGENCE)
                )
            )
