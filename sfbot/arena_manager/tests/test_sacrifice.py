from sfbot.arena_manager.constants import NO_RUNES_SACRIFICE_THRESHOLD
from sfbot.arena_manager.tests.conftest import _build_idle_data, make_arena_manager


class TestShouldSacrificeNoRunes:
    """Scenario 1: current_runes == 0"""

    def test_no_sacrifice_runes_available(self) -> None:
        data = _build_idle_data(current_runes=0, sacrifice_runes=0)
        am = make_arena_manager(idle_data=data)
        assert not am.should_sacrifice()

    def test_below_threshold(self) -> None:
        data = _build_idle_data(
            current_runes=0,
            sacrifice_runes=NO_RUNES_SACRIFICE_THRESHOLD - 1,
        )
        am = make_arena_manager(idle_data=data)
        assert not am.should_sacrifice()

    def test_at_threshold(self) -> None:
        data = _build_idle_data(
            current_runes=0,
            sacrifice_runes=NO_RUNES_SACRIFICE_THRESHOLD,
        )
        am = make_arena_manager(idle_data=data)
        assert am.should_sacrifice()

    def test_above_threshold(self) -> None:
        data = _build_idle_data(
            current_runes=0,
            sacrifice_runes=NO_RUNES_SACRIFICE_THRESHOLD + 100,
        )
        am = make_arena_manager(idle_data=data)
        assert am.should_sacrifice()


class TestShouldSacrificeNoToilet:
    """Scenario 2: has runes but no toilet"""

    def test_gain_less_than_current(self) -> None:
        data = _build_idle_data(current_runes=100, sacrifice_runes=50)
        am = make_arena_manager(idle_data=data)
        assert not am.should_sacrifice()

    def test_gain_equals_current(self) -> None:
        data = _build_idle_data(current_runes=100, sacrifice_runes=100)
        am = make_arena_manager(idle_data=data)
        assert am.should_sacrifice()

    def test_gain_exceeds_current(self) -> None:
        data = _build_idle_data(current_runes=100, sacrifice_runes=200)
        am = make_arena_manager(idle_data=data)
        assert am.should_sacrifice()


class TestShouldSacrificeHasToilet:
    """Scenario 3: has toilet (level > 0), uses _next_sacrifice_after"""

    def test_cycle_not_elapsed(self) -> None:
        """server_time < _next_sacrifice_after → don't sacrifice."""
        levels = [0] * 9 + [5]
        data = _build_idle_data(
            levels=levels,
            current_runes=100,
            sacrifice_runes=50,
        )
        am = make_arena_manager(idle_data=data, server_time=3000)
        am._next_sacrifice_after = 5000
        assert not am.should_sacrifice()

    def test_cycle_elapsed(self) -> None:
        """server_time > _next_sacrifice_after → sacrifice."""
        levels = [0] * 9 + [5]
        data = _build_idle_data(
            levels=levels,
            current_runes=100,
            sacrifice_runes=50,
        )
        am = make_arena_manager(idle_data=data, server_time=3000)
        am._next_sacrifice_after = 2000
        assert am.should_sacrifice()

    def test_cycle_exactly_at_end(self) -> None:
        """server_time == _next_sacrifice_after → don't sacrifice (must be >)."""
        levels = [0] * 9 + [5]
        data = _build_idle_data(
            levels=levels,
            current_runes=100,
            sacrifice_runes=50,
        )
        am = make_arena_manager(idle_data=data, server_time=2000)
        am._next_sacrifice_after = 2000
        assert not am.should_sacrifice()

    def test_no_stored_value_always_sacrifices(self) -> None:
        """_next_sacrifice_after defaults to 0 → sacrifice now."""
        levels = [0] * 9 + [5]
        data = _build_idle_data(
            levels=levels,
            current_runes=100,
            sacrifice_runes=50,
        )
        am = make_arena_manager(idle_data=data, server_time=2000)
        assert am.should_sacrifice()
