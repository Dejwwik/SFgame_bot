from unittest.mock import MagicMock

from sfbot.constants import VALUES_DELIMITER
from sfbot.constants.enums import CharClass
from sfbot.constants.parsing import CHARACTER_STATUS_DUNGEON_NEXT_FREE_FIGHT_INDEX
from sfbot.dungeon.constants import (
    CONTINUOUS_LOOP_FLOORS,
    FLOORS_PER_DUNGEON,
    LOCKED,
    MIRROR_WIN_CHANCE,
    PORTAL_FLOORS,
    SANDSTORM_FLOORS,
    TOWER_FLOORS,
    TWISTER_FLOORS,
)
from sfbot.dungeon.dungeon import (
    Dungeon,
    is_companion_dungeon,
    is_finished_light,
    is_finished_shadow,
    parse_progress,
    simulate_dungeon_fight,
)
from sfbot.dungeon.enums import DungeonKind, LightDungeon, ShadowDungeon
from sfbot.dungeon.tests.conftest import make_fighter


def make_dungeon_session(
    light_progress: dict[int, int] | None = None,
    shadow_progress: dict[int, int] | None = None,
    next_free_fight: int = 0,
    server_time: int = 9999,
) -> MagicMock:
    session = MagicMock()
    session.server_time.return_value = server_time

    # Build characterstatus with next_free_fight at index 21
    status_vals = ["0"] * (CHARACTER_STATUS_DUNGEON_NEXT_FREE_FIGHT_INDEX + 1)
    status_vals[CHARACTER_STATUS_DUNGEON_NEXT_FREE_FIGHT_INDEX] = str(next_free_fight)

    if light_progress:
        max_id = max(light_progress.keys())
        light_vals = [str(light_progress.get(i, 0)) for i in range(max_id + 1)]
        session.login_data = {
            "dungeonprogresslight(37)": VALUES_DELIMITER.join(light_vals),
            "dungeonprogressshadow(37)": "",
            "characterstatus": VALUES_DELIMITER.join(status_vals),
        }
    elif shadow_progress:
        max_id = max(shadow_progress.keys())
        shadow_vals = [str(shadow_progress.get(i, 0)) for i in range(max_id + 1)]
        session.login_data = {
            "dungeonprogresslight(37)": "",
            "dungeonprogressshadow(37)": VALUES_DELIMITER.join(shadow_vals),
            "characterstatus": VALUES_DELIMITER.join(status_vals),
        }
    else:
        session.login_data = {
            "dungeonprogresslight(37)": "",
            "dungeonprogressshadow(37)": "",
            "characterstatus": VALUES_DELIMITER.join(status_vals),
        }

    return session


# --- parse_progress ---


class TestParseProgress:
    def test_empty_list(self) -> None:
        assert parse_progress([]) == {}

    def test_single_value(self) -> None:
        assert parse_progress([5]) == {0: 5}

    def test_multiple_values(self) -> None:
        result = parse_progress([3, 7, 10])
        assert result == {0: 3, 1: 7, 2: 10}


# --- is_finished ---


class TestIsFinishedLight:
    def test_normal_dungeon_finished(self) -> None:
        assert (
            is_finished_light(LightDungeon.DESECRATED_CATACOMBS, FLOORS_PER_DUNGEON)
            is True
        )

    def test_normal_dungeon_not_finished(self) -> None:
        assert is_finished_light(LightDungeon.DESECRATED_CATACOMBS, 5) is False

    def test_tower_finished(self) -> None:
        assert is_finished_light(LightDungeon.TOWER, TOWER_FLOORS) is True

    def test_tower_not_finished(self) -> None:
        assert is_finished_light(LightDungeon.TOWER, 50) is False

    def test_sandstorm_finished(self) -> None:
        assert is_finished_light(LightDungeon.SANDSTORM, SANDSTORM_FLOORS) is True

    def test_sandstorm_not_finished(self) -> None:
        assert is_finished_light(LightDungeon.SANDSTORM, 500) is False


class TestIsFinishedShadow:
    def test_normal_shadow_finished(self) -> None:
        assert (
            is_finished_shadow(ShadowDungeon.DESECRATED_CATACOMBS, FLOORS_PER_DUNGEON)
            is True
        )

    def test_normal_shadow_not_finished(self) -> None:
        assert is_finished_shadow(ShadowDungeon.DESECRATED_CATACOMBS, 5) is False

    def test_twister_finished(self) -> None:
        assert is_finished_shadow(ShadowDungeon.TWISTER, TWISTER_FLOORS) is True

    def test_twister_not_finished(self) -> None:
        assert is_finished_shadow(ShadowDungeon.TWISTER, 500) is False

    def test_continuous_loop_finished(self) -> None:
        assert (
            is_finished_shadow(
                ShadowDungeon.CONTINUOUS_LOOP_OF_IDOLS, CONTINUOUS_LOOP_FLOORS
            )
            is True
        )

    def test_continuous_loop_not_finished(self) -> None:
        assert is_finished_shadow(ShadowDungeon.CONTINUOUS_LOOP_OF_IDOLS, 10) is False


# --- simulate_dungeon_fight ---


class TestSimulateDungeonFight:
    def test_mirror_monster_returns_mirror_win_chance(self) -> None:
        player = make_fighter()
        result = simulate_dungeon_fight(player, LightDungeon.PYRAMIDS_OF_MADNESS, 9, [])
        assert result == MIRROR_WIN_CHANCE

    def test_valid_floor_returns_float(self) -> None:
        player = make_fighter(
            level=200,
            strength=20_000,
            constitution=10_000,
            luck=5000,
            min_dmg=500.0,
            max_dmg=1000.0,
        )
        result = simulate_dungeon_fight(
            player, LightDungeon.DESECRATED_CATACOMBS, 0, []
        )
        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_out_of_range_returns_none(self) -> None:
        player = make_fighter()
        result = simulate_dungeon_fight(
            player, LightDungeon.DESECRATED_CATACOMBS, 999, []
        )
        assert result is None


# --- Dungeon class ---


class TestDungeonEnums:
    def test_dungeon_kind_values(self) -> None:
        assert DungeonKind.LIGHT == "light"
        assert DungeonKind.SHADOW == "shadow"
        assert DungeonKind.TOWER == "tower"
        assert DungeonKind.TWISTER == "twister"

    def test_light_dungeon_tower_index(self) -> None:
        assert LightDungeon.TOWER == 14

    def test_shadow_dungeon_twister_index(self) -> None:
        assert ShadowDungeon.TWISTER == 14

    def test_shadow_dungeon_continuous_loop_index(self) -> None:
        assert ShadowDungeon.CONTINUOUS_LOOP_OF_IDOLS == 17


class TestDungeonParse:
    def test_empty_login_data(self) -> None:
        session = make_dungeon_session()
        dungeon = Dungeon(session)
        assert dungeon.light_progress == {}
        assert dungeon.shadow_progress == {}
        assert dungeon.next_free_fight == 0

    def test_light_progress_parsed(self) -> None:
        session = make_dungeon_session(
            light_progress={0: 5, 1: 10, 2: 3},
        )
        dungeon = Dungeon(session)
        assert dungeon.light_progress[0] == 5
        assert dungeon.light_progress[1] == 10
        assert dungeon.light_progress[2] == 3

    def test_next_free_fight_parsed(self) -> None:
        session = make_dungeon_session(next_free_fight=12345)
        dungeon = Dungeon(session)
        assert dungeon.next_free_fight == 12345


class TestDungeonIsFree:
    def test_free_when_past_server_time(self) -> None:
        session = make_dungeon_session(next_free_fight=100, server_time=200)
        dungeon = Dungeon(session)
        assert dungeon.is_free is True

    def test_not_free_when_before_server_time(self) -> None:
        session = make_dungeon_session(next_free_fight=300, server_time=200)
        dungeon = Dungeon(session)
        assert dungeon.is_free is False


class TestDungeonFightableDungeons:
    def test_locked_dungeon_excluded(self) -> None:
        session = make_dungeon_session()
        dungeon = Dungeon(session)
        assert dungeon.get_fightable_light_dungeons() == []

    def test_finished_dungeon_excluded(self) -> None:
        session = make_dungeon_session(
            light_progress={LightDungeon.DESECRATED_CATACOMBS: FLOORS_PER_DUNGEON},
        )
        dungeon = Dungeon(session)
        fightable = dungeon.get_fightable_light_dungeons()
        assert LightDungeon.DESECRATED_CATACOMBS not in fightable

    def test_in_progress_dungeon_included(self) -> None:
        session = make_dungeon_session(
            light_progress={LightDungeon.DESECRATED_CATACOMBS: 5},
        )
        dungeon = Dungeon(session)
        fightable = dungeon.get_fightable_light_dungeons()
        assert LightDungeon.DESECRATED_CATACOMBS in fightable

    def test_tower_always_excluded_from_fightable_light(self) -> None:
        session = make_dungeon_session(
            light_progress={LightDungeon.TOWER: 50},
        )
        dungeon = Dungeon(session)
        fightable = dungeon.get_fightable_light_dungeons()
        assert LightDungeon.TOWER not in fightable

    def test_twister_excluded_from_fightable_shadow(self) -> None:
        session = make_dungeon_session(
            shadow_progress={ShadowDungeon.TWISTER: 500},
        )
        dungeon = Dungeon(session)
        fightable = dungeon.get_fightable_shadow_dungeons()
        assert ShadowDungeon.TWISTER not in fightable


class TestDungeonTowerAndTwister:
    def test_tower_progress(self) -> None:
        session = make_dungeon_session(
            light_progress={LightDungeon.TOWER: 42},
        )
        dungeon = Dungeon(session)
        assert dungeon.tower_progress == 42

    def test_tower_locked_returns_locked(self) -> None:
        session = make_dungeon_session()
        dungeon = Dungeon(session)
        assert dungeon.tower_progress == LOCKED

    def test_tower_fightable(self) -> None:
        session = make_dungeon_session(
            light_progress={LightDungeon.TOWER: 50},
        )
        dungeon = Dungeon(session)
        assert dungeon.is_tower_fightable is True

    def test_tower_not_fightable_when_complete(self) -> None:
        session = make_dungeon_session(
            light_progress={LightDungeon.TOWER: TOWER_FLOORS},
        )
        dungeon = Dungeon(session)
        assert dungeon.is_tower_fightable is False

    def test_twister_fightable(self) -> None:
        session = make_dungeon_session(
            shadow_progress={ShadowDungeon.TWISTER: 500},
        )
        dungeon = Dungeon(session)
        assert dungeon.is_twister_fightable is True

    def test_twister_not_fightable_when_complete(self) -> None:
        session = make_dungeon_session(
            shadow_progress={ShadowDungeon.TWISTER: TWISTER_FLOORS},
        )
        dungeon = Dungeon(session)
        assert dungeon.is_twister_fightable is False


class TestDungeonConstants:
    def test_floors_per_dungeon(self) -> None:
        assert FLOORS_PER_DUNGEON == 10

    def test_tower_floors(self) -> None:
        assert TOWER_FLOORS == 100

    def test_twister_floors(self) -> None:
        assert TWISTER_FLOORS == 1000

    def test_continuous_loop_floors(self) -> None:
        assert CONTINUOUS_LOOP_FLOORS == 21

    def test_sandstorm_floors(self) -> None:
        assert SANDSTORM_FLOORS == 1000

    def test_portal_floors(self) -> None:
        assert PORTAL_FLOORS == 50

    def test_mirror_win_chance(self) -> None:
        assert MIRROR_WIN_CHANCE == 0.5

    def test_locked_sentinel(self) -> None:
        assert LOCKED == -1


class TestCompanionDungeons:
    def test_tower_is_companion_dungeon(self) -> None:
        assert is_companion_dungeon(LightDungeon.TOWER) is True

    def test_twister_is_solo(self) -> None:
        assert is_companion_dungeon(ShadowDungeon.TWISTER) is False

    def test_shadow_dungeons_use_companions(self) -> None:
        assert is_companion_dungeon(ShadowDungeon.DESECRATED_CATACOMBS) is True
        assert is_companion_dungeon(ShadowDungeon.HELL) is True
        assert is_companion_dungeon(ShadowDungeon.NORDIC_GODS) is True
        assert is_companion_dungeon(ShadowDungeon.CONTINUOUS_LOOP_OF_IDOLS) is True

    def test_light_dungeons_are_solo(self) -> None:
        assert is_companion_dungeon(LightDungeon.DESECRATED_CATACOMBS) is False
        assert is_companion_dungeon(LightDungeon.HELL) is False
        assert is_companion_dungeon(LightDungeon.SANDSTORM) is False


class TestSimulateDungeonFightWithCompanions:
    def test_tower_with_companions_returns_float(self) -> None:
        player = make_fighter(
            level=200,
            strength=20_000,
            constitution=10_000,
            luck=5000,
            min_dmg=500.0,
            max_dmg=1000.0,
        )
        companions = [
            make_fighter(
                char_class=CharClass.WARRIOR,
                level=200,
                strength=15_000,
                constitution=8_000,
                luck=4000,
                min_dmg=400.0,
                max_dmg=800.0,
                is_companion=True,
            ),
            make_fighter(
                char_class=CharClass.MAGE,
                level=200,
                intelligence=15_000,
                constitution=6_000,
                luck=4000,
                min_dmg=300.0,
                max_dmg=600.0,
                is_companion=True,
            ),
            make_fighter(
                char_class=CharClass.SCOUT,
                level=200,
                dexterity=15_000,
                constitution=7_000,
                luck=4000,
                min_dmg=350.0,
                max_dmg=700.0,
                is_companion=True,
            ),
        ]
        result = simulate_dungeon_fight(
            player,
            LightDungeon.TOWER,
            0,
            companions,
        )
        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_tower_without_companions_uses_solo(self) -> None:
        player = make_fighter(
            level=200,
            strength=20_000,
            constitution=10_000,
            luck=5000,
            min_dmg=500.0,
            max_dmg=1000.0,
        )
        result = simulate_dungeon_fight(player, LightDungeon.TOWER, 0, [])
        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_regular_dungeon_ignores_companions(self) -> None:
        """Passing companions to a non-companion dungeon uses solo sim."""
        player = make_fighter(
            level=200,
            strength=20_000,
            constitution=10_000,
            luck=5000,
            min_dmg=500.0,
            max_dmg=1000.0,
        )
        companions = [
            make_fighter(is_companion=True),
        ]
        result_with = simulate_dungeon_fight(
            player,
            LightDungeon.DESECRATED_CATACOMBS,
            0,
            companions,
        )
        result_without = simulate_dungeon_fight(
            player,
            LightDungeon.DESECRATED_CATACOMBS,
            0,
            [],
        )
        # Both should return valid results (companion param ignored)
        assert result_with is not None
        assert result_without is not None
