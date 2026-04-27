from sfbot.arena_manager.constants import IdleBuildingType, IdleUpgradeAmount
from sfbot.arena_manager.tests.conftest import _build_idle_data, make_arena_manager


class TestGetNextUpgrade:
    def test_no_money_returns_none(self) -> None:
        data = _build_idle_data(
            levels=[0] * 10,
            current_money=0,
            upgrade_costs_1x=[100] * 10,
        )
        am = make_arena_manager(idle_data=data)
        assert am.get_next_upgrade() is None

    def test_first_building_gets_upgraded(self) -> None:
        data = _build_idle_data(
            levels=[0] * 10,
            current_money=100,
            upgrade_costs_1x=[100] * 10,
        )
        am = make_arena_manager(idle_data=data)
        result = am.get_next_upgrade()
        assert result is not None
        bt, amount, _ = result
        assert bt == IdleBuildingType.SEAT
        assert amount == IdleUpgradeAmount.ONE

    def test_picks_bulk_10x(self) -> None:
        data = _build_idle_data(
            levels=[0] * 10,
            current_money=900,
            upgrade_costs_1x=[100] * 10,
            upgrade_costs_10x=[900] * 10,
        )
        am = make_arena_manager(idle_data=data)
        result = am.get_next_upgrade()
        assert result is not None
        _, amount, _ = result
        assert amount == IdleUpgradeAmount.TEN

    def test_picks_bulk_25x(self) -> None:
        data = _build_idle_data(
            levels=[0] * 10,
            current_money=2000,
            upgrade_costs_1x=[100] * 10,
            upgrade_costs_10x=[900] * 10,
            upgrade_costs_25x=[2000] * 10,
        )
        am = make_arena_manager(idle_data=data)
        result = am.get_next_upgrade()
        assert result is not None
        _, amount, _ = result
        assert amount == IdleUpgradeAmount.TWENTY_FIVE

    def test_picks_bulk_100x_when_remaining_allows(self) -> None:
        """All at 250 → next is SEAT→500, remaining=250."""
        data = _build_idle_data(
            levels=[250] * 10,
            current_money=7000,
            upgrade_costs_1x=[100] * 10,
            upgrade_costs_10x=[900] * 10,
            upgrade_costs_25x=[2000] * 10,
            upgrade_costs_100x=[7000] * 10,
        )
        am = make_arena_manager(idle_data=data)
        result = am.get_next_upgrade()
        assert result is not None
        _, amount, _ = result
        assert amount == IdleUpgradeAmount.HUNDRED

    def test_respects_breakpoint_limit(self) -> None:
        """SEAT at level 24, only 1 remains to reach bp 25 — cannot do 10x."""
        data = _build_idle_data(
            levels=[24] + [0] * 9,
            current_money=900,
            upgrade_costs_1x=[100] * 10,
            upgrade_costs_10x=[900] * 10,
        )
        am = make_arena_manager(idle_data=data)
        result = am.get_next_upgrade()
        assert result is not None
        bt, amount, _ = result
        assert bt == IdleBuildingType.SEAT
        assert amount == IdleUpgradeAmount.ONE

    def test_seat_at_25_upgrades_to_50(self) -> None:
        """SEAT at 25 → next order entry is SEAT→50, pick 25x."""
        data = _build_idle_data(
            levels=[25] + [0] * 9,
            current_money=2000,
            upgrade_costs_1x=[100] * 10,
            upgrade_costs_10x=[900] * 10,
            upgrade_costs_25x=[2000] * 10,
        )
        am = make_arena_manager(idle_data=data)
        result = am.get_next_upgrade()
        assert result is not None
        bt, amount, _ = result
        assert bt == IdleBuildingType.SEAT
        assert amount == IdleUpgradeAmount.TWENTY_FIVE

    def test_all_at_max_returns_none(self) -> None:
        data = _build_idle_data(
            levels=[10000] * 10,
            current_money=999999,
        )
        am = make_arena_manager(idle_data=data)
        assert am.get_next_upgrade() is None

    def test_follows_predefined_order(self) -> None:
        """SEAT at 100, POPCORN at 0 → next is POPCORN→25 (before SEAT→250)."""
        data = _build_idle_data(
            levels=[100, 0] + [0] * 8,
            current_money=100,
            upgrade_costs_1x=[100] * 10,
        )
        am = make_arena_manager(idle_data=data)
        result = am.get_next_upgrade()
        assert result is not None
        bt, _, _ = result
        assert bt == IdleBuildingType.POPCORN_STAND

    def test_skips_if_too_expensive(self) -> None:
        """All buildings cost 200, money is 100 → nothing affordable."""
        data = _build_idle_data(
            levels=[0] * 10,
            current_money=100,
            upgrade_costs_1x=[200] * 10,
        )
        am = make_arena_manager(idle_data=data)
        assert am.get_next_upgrade() is None

    def test_remaining_15_picks_10x(self) -> None:
        """SEAT at level 35, target bp 50, remaining=15 → can do 10x."""
        data = _build_idle_data(
            levels=[35] + [0] * 9,
            current_money=900,
            upgrade_costs_1x=[100] * 10,
            upgrade_costs_10x=[900] * 10,
            upgrade_costs_25x=[2000] * 10,
        )
        am = make_arena_manager(idle_data=data)
        result = am.get_next_upgrade()
        assert result is not None
        _, amount, _ = result
        assert amount == IdleUpgradeAmount.TEN
