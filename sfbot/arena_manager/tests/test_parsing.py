from sfbot.arena_manager.constants import IdleBuildingType
from sfbot.arena_manager.tests.conftest import _build_idle_data, make_arena_manager


class TestParsing:
    def test_empty_data_not_unlocked(self) -> None:
        am = make_arena_manager(idle_data="")
        assert not am.is_unlocked

    def test_short_data_not_unlocked(self) -> None:
        am = make_arena_manager(idle_data="0/1/2")
        assert not am.is_unlocked

    def test_parse_levels(self) -> None:
        levels = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        data = _build_idle_data(levels=levels)
        am = make_arena_manager(idle_data=data)
        assert am.is_unlocked
        for i, bt in enumerate(IdleBuildingType):
            assert am.buildings[bt].level == levels[i]

    def test_parse_resets(self) -> None:
        data = _build_idle_data(resets=42)
        am = make_arena_manager(idle_data=data)
        assert am.resets == 42

    def test_parse_runes(self) -> None:
        data = _build_idle_data(
            current_runes=500, sacrifice_runes=100, current_money=999
        )
        am = make_arena_manager(idle_data=data)
        assert am.current_runes == 500
        assert am.sacrifice_runes == 100
        assert am.current_money == 999

    def test_parse_merchant_offers(self) -> None:
        data = _build_idle_data(offer_types=[10, 20, 22], offer_costs=[100, 100, 20])
        am = make_arena_manager(idle_data=data)
        assert len(am.merchant_offers) == 3
        assert am.merchant_offers[0].offer_type == 10
        assert am.merchant_offers[0].cost == 100
        assert am.merchant_offers[1].offer_type == 20
        assert am.merchant_offers[2].offer_type == 22
        assert am.merchant_offers[2].cost == 20

    def test_parse_merchant_offers_skip_zeros(self) -> None:
        data = _build_idle_data(offer_types=[0, 10, 0], offer_costs=[0, 100, 0])
        am = make_arena_manager(idle_data=data)
        assert len(am.merchant_offers) == 1
        assert am.merchant_offers[0].index == 2

    def test_has_toilet_false_when_level_zero(self) -> None:
        levels = [10, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        data = _build_idle_data(levels=levels)
        am = make_arena_manager(idle_data=data)
        assert not am.has_toilet

    def test_has_toilet_true_when_level_positive(self) -> None:
        levels = [0, 0, 0, 0, 0, 0, 0, 0, 0, 5]
        data = _build_idle_data(levels=levels)
        am = make_arena_manager(idle_data=data)
        assert am.has_toilet

    def test_parse_cycle_timestamps(self) -> None:
        starts = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        ends = [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000]
        data = _build_idle_data(cycle_starts=starts, cycle_ends=ends)
        am = make_arena_manager(idle_data=data)
        assert am.toilet.cycle_start == 1000
        assert am.toilet.cycle_end == 2000
