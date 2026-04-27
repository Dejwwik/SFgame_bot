from sfbot.legendary_dungeon.constants import (
    BOSS_DMG,
    BROKEN_ARMOR_MULTIPLIER,
    FIGHT_DMG,
)
from sfbot.legendary_dungeon.models import (
    DungeonEffectType,
    DungeonStage,
    EventTheme,
    GemEffect,
)
from sfbot.legendary_dungeon.tests.conftest import make_dungeon, make_effect, make_gem

# ═══════════════════════════════════════════════════════════════════════════
# Section / Floor Helpers
# ═══════════════════════════════════════════════════════════════════════════


class TestSectionIndex:
    def test_floor_1_is_section_0(self):
        assert make_dungeon(current_floor=1).section_index() == 0

    def test_floor_24_is_section_0(self):
        assert make_dungeon(current_floor=24).section_index() == 0

    def test_floor_25_is_section_1(self):
        assert make_dungeon(current_floor=25).section_index() == 1

    def test_floor_50_is_section_2(self):
        assert make_dungeon(current_floor=50).section_index() == 2

    def test_floor_75_is_section_3(self):
        assert make_dungeon(current_floor=75).section_index() == 3

    def test_floor_99_is_section_3(self):
        assert make_dungeon(current_floor=99).section_index() == 3

    def test_floor_100_capped_at_3(self):
        assert make_dungeon(current_floor=100).section_index() == 3

    def test_no_dungeon_returns_0(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.section_index() == 0


class TestNextBossFloor:
    def test_floor_1_next_boss_25(self):
        assert make_dungeon(current_floor=1).next_boss_floor() == 25

    def test_floor_24_next_boss_25(self):
        assert make_dungeon(current_floor=24).next_boss_floor() == 25

    def test_floor_25_next_boss_50(self):
        assert make_dungeon(current_floor=25).next_boss_floor() == 50

    def test_floor_49_next_boss_50(self):
        assert make_dungeon(current_floor=49).next_boss_floor() == 50

    def test_floor_74_next_boss_75(self):
        assert make_dungeon(current_floor=74).next_boss_floor() == 75

    def test_floor_75_next_boss_100(self):
        assert make_dungeon(current_floor=75).next_boss_floor() == 100

    def test_floor_99_next_boss_100(self):
        assert make_dungeon(current_floor=99).next_boss_floor() == 100

    def test_no_dungeon_returns_25(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.next_boss_floor() == 25


class TestFloorsToBoss:
    def test_floor_1_to_boss_24(self):
        assert make_dungeon(current_floor=1).floors_to_boss() == 24

    def test_floor_24_to_boss_1(self):
        assert make_dungeon(current_floor=24).floors_to_boss() == 1

    def test_floor_25_to_boss_25(self):
        assert make_dungeon(current_floor=25).floors_to_boss() == 25

    def test_floor_99_to_boss_1(self):
        assert make_dungeon(current_floor=99).floors_to_boss() == 1

    def test_no_dungeon_returns_25(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.floors_to_boss() == 25


# ═══════════════════════════════════════════════════════════════════════════
# Max Fight / Boss Damage
# ═══════════════════════════════════════════════════════════════════════════


class TestMaxDamage:
    def test_fight_dmg_section_0(self):
        assert make_dungeon(current_floor=1).max_fight_dmg_pct() == FIGHT_DMG[0]

    def test_fight_dmg_section_3(self):
        assert make_dungeon(current_floor=80).max_fight_dmg_pct() == FIGHT_DMG[3]

    def test_boss_dmg_floor_24(self):
        assert make_dungeon(current_floor=24).max_boss_dmg_pct() == BOSS_DMG[25]

    def test_boss_dmg_floor_99(self):
        assert make_dungeon(current_floor=99).max_boss_dmg_pct() == BOSS_DMG[100]


# ═══════════════════════════════════════════════════════════════════════════
# Blessings & Curses
# ═══════════════════════════════════════════════════════════════════════════


class TestHasBlessingCurse:
    def test_has_blessing_present(self):
        ld = make_dungeon(blessings=[make_effect(DungeonEffectType.RAIDER), None, None])
        assert ld.has_blessing(DungeonEffectType.RAIDER) is True

    def test_has_blessing_absent(self):
        ld = make_dungeon()
        assert ld.has_blessing(DungeonEffectType.RAIDER) is False

    def test_has_blessing_expired(self):
        ld = make_dungeon(
            blessings=[
                make_effect(DungeonEffectType.RAIDER, remaining_uses=0),
                None,
                None,
            ]
        )
        assert ld.has_blessing(DungeonEffectType.RAIDER) is False

    def test_has_blessing_in_second_slot(self):
        ld = make_dungeon(
            blessings=[None, make_effect(DungeonEffectType.ONE_HIT_WONDER), None]
        )
        assert ld.has_blessing(DungeonEffectType.ONE_HIT_WONDER) is True

    def test_has_curse_present(self):
        ld = make_dungeon(
            curses=[make_effect(DungeonEffectType.BROKEN_ARMOR), None, None]
        )
        assert ld.has_curse(DungeonEffectType.BROKEN_ARMOR) is True

    def test_has_curse_absent(self):
        ld = make_dungeon()
        assert ld.has_curse(DungeonEffectType.BROKEN_ARMOR) is False

    def test_has_curse_in_third_slot(self):
        ld = make_dungeon(curses=[None, None, make_effect(DungeonEffectType.POISONED)])
        assert ld.has_curse(DungeonEffectType.POISONED) is True

    def test_no_dungeon_returns_false(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.has_blessing(DungeonEffectType.RAIDER) is False
        assert ld.has_curse(DungeonEffectType.BROKEN_ARMOR) is False


# ═══════════════════════════════════════════════════════════════════════════
# Effective Fight Damage
# ═══════════════════════════════════════════════════════════════════════════


class TestEffectiveFightDmg:
    def test_normal_fight_dmg(self):
        ld = make_dungeon(current_floor=1)
        assert ld.effective_fight_dmg_pct() == FIGHT_DMG[0]

    def test_one_hit_wonder_zeroes_damage(self):
        ld = make_dungeon(
            blessings=[make_effect(DungeonEffectType.ONE_HIT_WONDER), None, None]
        )
        assert ld.effective_fight_dmg_pct() == 0.0

    def test_broken_armor_multiplies_damage(self):
        ld = make_dungeon(
            current_floor=1,
            curses=[make_effect(DungeonEffectType.BROKEN_ARMOR), None, None],
        )
        expected = FIGHT_DMG[0] * BROKEN_ARMOR_MULTIPLIER
        assert abs(ld.effective_fight_dmg_pct() - expected) < 0.01

    def test_one_hit_overrides_broken_armor(self):
        ld = make_dungeon(
            blessings=[make_effect(DungeonEffectType.ONE_HIT_WONDER), None, None],
            curses=[make_effect(DungeonEffectType.BROKEN_ARMOR), None, None],
        )
        assert ld.effective_fight_dmg_pct() == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Survival Checks
# ═══════════════════════════════════════════════════════════════════════════


class TestSurvival:
    def test_can_survive_boss_at_full_hp(self):
        assert make_dungeon(
            current_hp=1000, max_hp=1000, current_floor=1
        ).can_survive_boss()

    def test_cannot_survive_boss_at_low_hp(self):
        # Boss at floor 25 does 19.6% → need >19.6% HP → >196 HP of 1000
        assert not make_dungeon(
            current_hp=100, max_hp=1000, current_floor=1
        ).can_survive_boss()

    def test_can_survive_fight_at_full_hp(self):
        assert make_dungeon(current_hp=1000, max_hp=1000).can_survive_fight()

    def test_cannot_survive_fight_at_very_low_hp(self):
        assert not make_dungeon(current_hp=10, max_hp=1000).can_survive_fight()


# ═══════════════════════════════════════════════════════════════════════════
# HP Percentage
# ═══════════════════════════════════════════════════════════════════════════


class TestHpPct:
    def test_full_hp(self):
        assert make_dungeon(current_hp=1000, max_hp=1000).hp_pct == 100.0

    def test_half_hp(self):
        assert make_dungeon(current_hp=500, max_hp=1000).hp_pct == 50.0

    def test_zero_max_hp(self):
        assert make_dungeon(current_hp=0, max_hp=0).hp_pct == 0.0

    def test_no_dungeon(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.hp_pct == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# is_last_section / needs_more_keys
# ═══════════════════════════════════════════════════════════════════════════


class TestLastSectionKeys:
    def test_is_last_section_at_floor_75(self):
        assert make_dungeon(current_floor=75).is_last_section() is True

    def test_is_not_last_section_at_floor_74(self):
        assert make_dungeon(current_floor=74).is_last_section() is False

    def test_needs_keys_when_low(self):
        assert make_dungeon(current_floor=10, keys=2).needs_more_keys() is True

    def test_does_not_need_keys_at_target(self):
        assert make_dungeon(current_floor=10, keys=6).needs_more_keys() is False

    def test_does_not_need_keys_in_last_section(self):
        assert make_dungeon(current_floor=80, keys=0).needs_more_keys() is False

    def test_no_dungeon_not_last_section(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.is_last_section() is False

    def test_no_dungeon_no_keys_needed(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.needs_more_keys() is False


# ═══════════════════════════════════════════════════════════════════════════
# Gem Stat Aggregation
# ═══════════════════════════════════════════════════════════════════════════


class TestGemStatAggregation:
    def test_monster_dmg_reduction_single_gem(self):
        ld = make_dungeon(
            owned_gems=[
                make_gem(advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=20)
            ]
        )
        assert abs(ld.gem_monster_dmg_reduction() - 0.20) < 0.001

    def test_monster_dmg_reduction_stacks(self):
        ld = make_dungeon(
            owned_gems=[
                make_gem(advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=15),
                make_gem(advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=10),
            ]
        )
        assert abs(ld.gem_monster_dmg_reduction() - 0.25) < 0.001

    def test_monster_dmg_reduction_with_disadvantage(self):
        ld = make_dungeon(
            owned_gems=[
                make_gem(
                    advantage=GemEffect.DAMAGE_FROM_MONSTERS,
                    advantage_pwr=20,
                    disadvantage=GemEffect.DAMAGE_FROM_MONSTERS,
                    disadvantage_pwr=10,
                )
            ]
        )
        assert abs(ld.gem_monster_dmg_reduction() - 0.10) < 0.001

    def test_escape_chance_bonus(self):
        ld = make_dungeon(
            owned_gems=[make_gem(advantage=GemEffect.ESCAPE_CHANCE, advantage_pwr=30)]
        )
        assert abs(ld.gem_escape_chance_bonus() - 0.30) < 0.001

    def test_escape_chance_mixed(self):
        ld = make_dungeon(
            owned_gems=[
                make_gem(advantage=GemEffect.ESCAPE_CHANCE, advantage_pwr=20),
                make_gem(disadvantage=GemEffect.ESCAPE_CHANCE, disadvantage_pwr=5),
            ]
        )
        assert abs(ld.gem_escape_chance_bonus() - 0.15) < 0.001

    def test_no_gems_zero_reduction(self):
        ld = make_dungeon(owned_gems=[])
        assert ld.gem_monster_dmg_reduction() == 0.0
        assert ld.gem_escape_chance_bonus() == 0.0

    def test_irrelevant_gems_ignored(self):
        ld = make_dungeon(
            owned_gems=[make_gem(advantage=GemEffect.CHANCE_OF_KEYS, advantage_pwr=50)]
        )
        assert ld.gem_monster_dmg_reduction() == 0.0
        assert ld.gem_escape_chance_bonus() == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# should_start_run
# ═══════════════════════════════════════════════════════════════════════════


class TestShouldStartRun:
    def test_not_entered_always_starts(self):
        ld = make_dungeon(stage=DungeonStage.NOT_ENTERED)
        assert ld.should_start_run() is True

    def test_full_hp_starts(self):
        ld = make_dungeon(
            current_hp=1000,
            max_hp=1000,
            current_floor=50,
            stage=DungeonStage.DOOR_SELECT,
        )
        assert ld.should_start_run() is True

    def test_low_hp_mid_section_does_not_start(self):
        ld = make_dungeon(
            current_hp=500,
            max_hp=1000,
            current_floor=50,
            stage=DungeonStage.DOOR_SELECT,
        )
        # 50% < START_HP_THRESHOLD (90%)
        assert ld.should_start_run() is False

    def test_floor_99_needs_enough_hp_for_boss(self):
        # Final boss does ~52.5% → need >52.5%
        ld = make_dungeon(
            current_hp=600,
            max_hp=1000,
            current_floor=99,
            stage=DungeonStage.DOOR_SELECT,
        )
        assert ld.should_start_run() is True

    def test_floor_99_not_enough_hp(self):
        ld = make_dungeon(
            current_hp=400,
            max_hp=1000,
            current_floor=99,
            stage=DungeonStage.DOOR_SELECT,
        )
        assert ld.should_start_run() is False

    def test_floor_98_accounts_for_one_fight(self):
        # Boss dmg ~52.5% + one fight cost
        ld = make_dungeon(
            current_hp=999,
            max_hp=1000,
            current_floor=98,
            stage=DungeonStage.DOOR_SELECT,
        )
        assert ld.should_start_run() is True

    def test_no_dungeon(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.should_start_run() is False

    def test_gem_bonuses_affect_start_decision(self):
        # With monster dmg reduction, should be able to start with lower HP
        ld = make_dungeon(
            current_hp=450,
            max_hp=1000,
            current_floor=99,
            stage=DungeonStage.DOOR_SELECT,
            owned_gems=[
                make_gem(advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=30)
            ],
        )
        # Boss dmg reduced by 30%: 52.5 * 0.7 = 36.75% → 45% > 36.75%
        assert ld.should_start_run() is True


# ═══════════════════════════════════════════════════════════════════════════
# Urgent Time Guard — less than 1 hour remaining
# ═══════════════════════════════════════════════════════════════════════════


class TestUrgentTimeGuard:
    def test_enters_with_low_hp_when_time_running_out(self):
        # 20% HP, less than 1 hour remaining → should enter
        ld = make_dungeon(
            current_hp=200,
            max_hp=1000,
            current_floor=50,
            stage=DungeonStage.DOOR_SELECT,
            server_time=9500,
            end_ts=10_000,
        )
        # 10_000 - 9500 = 500 seconds < 3600 → urgent, 20% >= 20% → enter
        assert ld.should_start_run() is True

    def test_does_not_enter_below_urgent_hp_threshold(self):
        # 15% HP, less than 1 hour remaining → too low
        ld = make_dungeon(
            current_hp=150,
            max_hp=1000,
            current_floor=50,
            stage=DungeonStage.DOOR_SELECT,
            server_time=9500,
            end_ts=10_000,
        )
        assert ld.should_start_run() is False

    def test_normal_rules_when_plenty_of_time(self):
        # 50% HP with lots of time → normal rules apply (90% threshold)
        ld = make_dungeon(
            current_hp=500,
            max_hp=1000,
            current_floor=50,
            stage=DungeonStage.DOOR_SELECT,
            server_time=100,
            end_ts=10_000,
        )
        # 10_000 - 100 = 9900 > 3600 → not urgent, 50% < 90% → don't enter
        assert ld.should_start_run() is False

    def test_urgent_at_exactly_one_hour(self):
        # Exactly 7200 seconds remaining → not urgent (<= 7200 boundary)
        ld = make_dungeon(
            current_hp=250,
            max_hp=1000,
            current_floor=50,
            stage=DungeonStage.DOOR_SELECT,
            server_time=2800,
            end_ts=10_000,
        )
        # 10_000 - 2800 = 7200, not < 7200 → normal rules, 25% < 90% → don't enter
        assert ld.should_start_run() is False

    def test_urgent_at_one_second_before_hour(self):
        # 3599 seconds remaining → urgent
        ld = make_dungeon(
            current_hp=250,
            max_hp=1000,
            current_floor=50,
            stage=DungeonStage.DOOR_SELECT,
            server_time=6401,
            end_ts=10_000,
        )
        # 10_000 - 6401 = 3599 < 3600 → urgent, 25% >= 20% → enter
        assert ld.should_start_run() is True

    def test_urgent_does_not_override_floor_99_logic(self):
        # Floor 99 with urgent time but enough HP for boss → should enter
        ld = make_dungeon(
            current_hp=600,
            max_hp=1000,
            current_floor=99,
            stage=DungeonStage.DOOR_SELECT,
            server_time=9500,
            end_ts=10_000,
        )
        assert ld.should_start_run() is True

    def test_urgent_saves_run_that_normal_rules_would_skip(self):
        # Floor 50, 30% HP, 30 minutes left → urgent overrides normal 90% threshold
        ld = make_dungeon(
            current_hp=300,
            max_hp=1000,
            current_floor=50,
            stage=DungeonStage.DOOR_SELECT,
            server_time=8200,
            end_ts=10_000,
        )
        # 10_000 - 8200 = 1800 < 3600 → urgent, 30% >= 20% → enter
        assert ld.should_start_run() is True


# ═══════════════════════════════════════════════════════════════════════════
# Properties: is_active, is_enterable, is_entered
# ═══════════════════════════════════════════════════════════════════════════


class TestProperties:
    def test_is_active_when_in_window(self):
        ld = make_dungeon(start_ts=0, close_ts=200, server_time=100)
        ld.theme = EventTheme.ABYSS_OF_MADNESS
        assert ld.is_active is True

    def test_not_active_no_theme(self):
        ld = make_dungeon()
        ld.theme = None
        assert ld.is_active is False

    def test_not_active_before_start(self):
        ld = make_dungeon(start_ts=200, close_ts=400, server_time=100)
        ld.theme = EventTheme.ABYSS_OF_MADNESS
        assert ld.is_active is False

    def test_not_active_after_close(self):
        ld = make_dungeon(start_ts=0, close_ts=100, server_time=200)
        ld.theme = EventTheme.ABYSS_OF_MADNESS
        assert ld.is_active is False

    def test_is_enterable_before_end(self):
        ld = make_dungeon(start_ts=0, end_ts=200, server_time=100)
        ld.theme = EventTheme.LORD_OF_THE_THINGS
        assert ld.is_enterable is True

    def test_not_enterable_after_end(self):
        ld = make_dungeon(start_ts=0, end_ts=50, server_time=100)
        ld.theme = EventTheme.LORD_OF_THE_THINGS
        assert ld.is_enterable is False

    def test_is_entered_when_in_progress(self):
        ld = make_dungeon(stage=DungeonStage.DOOR_SELECT)
        assert ld.is_entered is True

    def test_not_entered_at_stage_zero(self):
        ld = make_dungeon(stage=DungeonStage.NOT_ENTERED)
        assert ld.is_entered is False

    def test_not_entered_no_dungeon(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.is_entered is False

    def test_current_floor_no_dungeon(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.current_floor == 0

    def test_max_floor_no_dungeon(self):
        ld = make_dungeon()
        ld.dungeon = None
        assert ld.max_floor == 0


# ═══════════════════════════════════════════════════════════════════════════
# DungeonState.is_alive / is_healing
# ═══════════════════════════════════════════════════════════════════════════


class TestDungeonStateAlive:
    def test_alive_normal(self):
        ld = make_dungeon(health_status=0, stage=DungeonStage.DOOR_SELECT)
        assert ld.dungeon is not None
        assert ld.dungeon.is_alive is True

    def test_dead_health_status_1(self):
        ld = make_dungeon(health_status=1)
        assert ld.dungeon is not None
        assert ld.dungeon.is_alive is False

    def test_healing_is_not_alive(self):
        ld = make_dungeon(stage=DungeonStage.HEALING)
        assert ld.dungeon is not None
        assert ld.dungeon.is_alive is False

    def test_is_healing(self):
        ld = make_dungeon(stage=DungeonStage.HEALING)
        assert ld.dungeon is not None
        assert ld.dungeon.is_healing is True

    def test_not_healing(self):
        ld = make_dungeon(stage=DungeonStage.DOOR_SELECT)
        assert ld.dungeon is not None
        assert ld.dungeon.is_healing is False


# ═══════════════════════════════════════════════════════════════════════════
# status_summary
# ═══════════════════════════════════════════════════════════════════════════


class TestStatusSummary:
    def test_not_active(self):
        ld = make_dungeon()
        ld.theme = None
        assert "not active" in ld.status_summary()

    def test_active_with_dungeon(self):
        ld = make_dungeon(
            current_hp=800,
            max_hp=1000,
            current_floor=42,
            keys=3,
            stage=DungeonStage.DOOR_SELECT,
            start_ts=0,
            close_ts=200,
            server_time=100,
        )
        ld.theme = EventTheme.ABYSS_OF_MADNESS
        summary = ld.status_summary()
        assert "ABYSS_OF_MADNESS" in summary
        assert "42" in summary
        assert "keys=3" in summary

    def test_active_not_entered(self):
        ld = make_dungeon(start_ts=0, close_ts=200, server_time=100)
        ld.theme = EventTheme.VILE_VACATION
        ld.dungeon = None
        summary = ld.status_summary()
        assert "not entered" in summary
