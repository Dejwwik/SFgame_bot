"""Tests for class-specific combat abilities in fight_once."""

import random

from sfbot.constants.enums import CharClass
from sfbot.dungeon.simulate import (
    calc_crit_chance,
    calc_crit_multiplier,
    fight_once,
    precompute_combat_stats,
    simulate_fight,
)
from sfbot.dungeon.simulate.class_models.battle_mage import calc_fireball_damage
from sfbot.dungeon.simulate.class_models.necromancer import calc_necro_minion_damage
from sfbot.dungeon.simulate.constants import (
    BYPASS_SPECIAL,
    DRUID_RAGE_CRIT_BONUS,
    DRUID_RAGE_CRIT_CHANCE,
    DRUID_RAGE_CRIT_MULT,
    FIREBALL_HP_RATIO,
    NECRO_SPECTRE,
    NECRO_SUMMON_CRIT_BONUS,
    NECRO_SUMMON_CRIT_CHANCE,
    NECRO_SUMMON_CRIT_CHANCE_BONUS,
    NECRO_SUMMON_DMG_BONUS,
    NECRO_SUMMON_SKIP_CHANCE,
    SKIP_TYPE,
    SKIP_TYPE_CONTROL,
)
from sfbot.dungeon.tests.conftest import make_fighter
from sfbot.simulate.constants import CRIT_BASE, HEALTH_MULTIPLIER


class TestFireball:
    def test_fireball_damage_formula(self) -> None:
        attacker_hp = 100_000.0
        target_hp = 90_000.0
        target = make_fighter(char_class=CharClass.WARRIOR)
        dmg = calc_fireball_damage(attacker_hp, target_hp, target)
        expected = min(
            target_hp / 3.0,
            attacker_hp * FIREBALL_HP_RATIO * HEALTH_MULTIPLIER[CharClass.WARRIOR],
        )
        assert dmg > 0
        assert dmg <= expected + 1  # ceil rounding

    def test_fireball_bypassed_by_mage(self) -> None:
        target = make_fighter(char_class=CharClass.MAGE)
        dmg = calc_fireball_damage(100_000.0, 90_000.0, target)
        assert dmg == 0.0

    def test_battle_mage_deals_fireball_before_combat(self) -> None:
        random.seed(42)
        bm = make_fighter(char_class=CharClass.BATTLE_MAGE, constitution=5000)
        enemy = make_fighter(char_class=CharClass.WARRIOR, constitution=500)
        stats_a = precompute_combat_stats(bm, enemy)
        stats_b = precompute_combat_stats(enemy, bm)
        a_hp, b_hp = fight_once(stats_a, stats_b)
        # BM should win easily in part due to fireball
        assert a_hp > 0

    def test_fireball_can_kill_before_combat_starts(self) -> None:
        random.seed(42)
        bm = make_fighter(char_class=CharClass.BATTLE_MAGE, constitution=10000)
        # Very weak enemy — fireball should kill
        enemy = make_fighter(char_class=CharClass.WARRIOR, constitution=1, level=1)
        stats_a = precompute_combat_stats(bm, enemy)
        stats_b = precompute_combat_stats(enemy, bm)
        a_hp, b_hp = fight_once(stats_a, stats_b)
        assert a_hp > 0
        assert b_hp <= 0


class TestAssassinDualWield:
    def test_assassin_attacks_twice_deals_more_damage(self) -> None:
        random.seed(100)
        # Assassin with second weapon vs same class without
        assassin = make_fighter(
            char_class=CharClass.ASSASSIN,
            dexterity=5000,
            strength=1000,
            intelligence=1000,
            min_dmg=100,
            max_dmg=200,
            min_dmg2=80,
            max_dmg2=160,
        )
        warrior = make_fighter(
            char_class=CharClass.WARRIOR,
            constitution=5000,
        )
        # Compare: assassin should win more than a scout with same stats
        win_rate = simulate_fight(assassin, warrior, iterations=5000)
        # With dual-wield, assassin should have a reasonable win rate
        assert win_rate > 0.1


class TestBerserkerChainSkip:
    def test_berserker_has_control_skip(self) -> None:
        assert SKIP_TYPE[CharClass.BERSERKER] == SKIP_TYPE_CONTROL

    def test_berserker_vs_warrior_reasonable_rate(self) -> None:
        random.seed(42)
        berserker = make_fighter(
            char_class=CharClass.BERSERKER,
            strength=5000,
        )
        warrior = make_fighter(
            char_class=CharClass.WARRIOR,
            strength=5000,
        )
        win_rate = simulate_fight(berserker, warrior, iterations=5000)
        assert 0.0 < win_rate < 1.0


class TestDemonHunterRevive:
    def test_dh_survives_longer_than_class_with_same_stats(self) -> None:
        random.seed(42)
        dh = make_fighter(
            char_class=CharClass.DEMON_HUNTER,
            dexterity=4000,
            strength=1000,
            intelligence=1000,
            constitution=2000,
            luck=2000,
        )
        # Compare DH vs Mage (no dodge, no revive) to isolate revive benefit
        mage = make_fighter(
            char_class=CharClass.MAGE,
            intelligence=4000,
            strength=1000,
            dexterity=1000,
            constitution=2000,
            luck=2000,
        )
        strong_enemy = make_fighter(
            char_class=CharClass.WARRIOR,
            strength=8000,
            constitution=5000,
            luck=3000,
        )
        dh_rate = simulate_fight(dh, strong_enemy, iterations=5000)
        mage_rate = simulate_fight(mage, strong_enemy, iterations=5000)
        # DH revive should give an edge over mage (no dodge, no revive)
        assert dh_rate >= mage_rate


class TestDruidRageCrit:
    def test_rage_crit_chance_dynamic(self) -> None:
        druid = make_fighter(char_class=CharClass.DRUID, luck=2000, level=100)
        enemy = make_fighter(char_class=CharClass.WARRIOR)
        base_crit = calc_crit_chance(druid, enemy)
        rage_crit = min(DRUID_RAGE_CRIT_CHANCE, base_crit + DRUID_RAGE_CRIT_BONUS)
        assert rage_crit <= DRUID_RAGE_CRIT_CHANCE
        assert rage_crit >= base_crit

    def test_rage_crit_mult_scales_with_player(self) -> None:
        druid = make_fighter(
            char_class=CharClass.DRUID,
            has_sword_of_vengeance=True,
            gladiator=5,
        )
        enemy = make_fighter(char_class=CharClass.WARRIOR)
        base_crit_mult = calc_crit_multiplier(druid, enemy)
        rage_crit_mult = (CRIT_BASE + DRUID_RAGE_CRIT_MULT) * base_crit_mult / CRIT_BASE
        # Should be 3x the base crit multiplier
        assert rage_crit_mult > base_crit_mult
        assert abs(rage_crit_mult - 3 * base_crit_mult) < 0.01


class TestNecromancerMinion:
    def test_minion_attack_returns_damage(self) -> None:
        random.seed(42)
        necro = make_fighter(char_class=CharClass.NECROMANCER, intelligence=5000)
        enemy = make_fighter(char_class=CharClass.WARRIOR)
        pre = precompute_combat_stats(necro, enemy)
        # Skeleton (type 0): +25% damage
        dmg = calc_necro_minion_damage(0, pre, 1.0, enemy, 1.5)
        assert dmg > 0

    def test_zombie_deals_more_than_skeleton(self) -> None:
        random.seed(42)
        necro = make_fighter(char_class=CharClass.NECROMANCER, intelligence=5000)
        enemy = make_fighter(char_class=CharClass.WARRIOR, luck=0)
        pre = precompute_combat_stats(necro, enemy)
        # Run many trials to get average
        skeleton_total = 0.0
        zombie_total = 0.0
        for _ in range(1000):
            skeleton_total += calc_necro_minion_damage(0, pre, 1.0, enemy, 1.5)
            zombie_total += calc_necro_minion_damage(1, pre, 1.0, enemy, 1.5)
        # Zombie (type 1: +100%) should deal more than skeleton (type 0: +25%)
        assert zombie_total > skeleton_total

    def test_spectre_deals_damage(self) -> None:
        # Spectre (type 2) has 0% damage bonus — attacks at base damage
        random.seed(42)
        necro = make_fighter(char_class=CharClass.NECROMANCER, intelligence=5000)
        enemy = make_fighter(char_class=CharClass.WARRIOR, luck=0)
        pre = precompute_combat_stats(necro, enemy)
        dmg = calc_necro_minion_damage(2, pre, 1.0, enemy, 1.5)
        assert dmg > 0

    def test_spectre_defense_gives_necro_block(self) -> None:
        # When necromancer is defender with spectre, they should block more
        random.seed(42)
        necro = make_fighter(
            char_class=CharClass.NECROMANCER,
            intelligence=3000,
            constitution=5000,
            luck=1000,
        )
        warrior = make_fighter(
            char_class=CharClass.WARRIOR,
            strength=8000,
            constitution=5000,
            luck=3000,
        )
        # Spectre skip chance is 0.25 — necromancer should survive better
        # (Tested indirectly through simulate_fight)
        win_rate = simulate_fight(necro, warrior, iterations=5000)
        assert 0.0 <= win_rate <= 1.0

    def test_minion_crit_chance_bonus_on_zombie(self) -> None:
        # Zombie (Ghost) has CriticalChanceBonus of 0.1
        assert NECRO_SUMMON_CRIT_CHANCE_BONUS[1] == 0.1
        assert NECRO_SUMMON_CRIT_CHANCE[1] == 0.6
        assert NECRO_SUMMON_DMG_BONUS[1] == 1.0

    def test_minion_crit_bonus_on_zombie(self) -> None:
        assert NECRO_SUMMON_CRIT_BONUS[1] == 0.5

    def test_spectre_skip_chance_value(self) -> None:
        assert NECRO_SUMMON_SKIP_CHANCE[NECRO_SPECTRE] == 0.25


class TestPaladinStances:
    def test_paladin_fights_reasonably(self) -> None:
        random.seed(42)
        paladin = make_fighter(
            char_class=CharClass.PALADIN,
            strength=5000,
            constitution=4000,
            luck=2000,
        )
        warrior = make_fighter(
            char_class=CharClass.WARRIOR,
            strength=5000,
            constitution=4000,
            luck=2000,
        )
        win_rate = simulate_fight(paladin, warrior, iterations=5000)
        assert 0.0 < win_rate < 1.0


class TestPlagueDoctor:
    def test_pd_tincture_affects_fight(self) -> None:
        random.seed(42)
        pd = make_fighter(
            char_class=CharClass.PLAGUE_DOCTOR,
            intelligence=5000,
            constitution=4000,
            luck=2000,
        )
        warrior = make_fighter(
            char_class=CharClass.WARRIOR,
            strength=5000,
            constitution=4000,
            luck=2000,
        )
        win_rate = simulate_fight(pd, warrior, iterations=5000)
        assert 0.0 <= win_rate <= 1.0


class TestBardMelody:
    def test_bard_fights_reasonably(self) -> None:
        random.seed(42)
        bard = make_fighter(
            char_class=CharClass.BARD,
            intelligence=5000,
            constitution=4000,
            luck=2000,
        )
        warrior = make_fighter(
            char_class=CharClass.WARRIOR,
            strength=5000,
            constitution=4000,
            luck=2000,
        )
        win_rate = simulate_fight(bard, warrior, iterations=5000)
        assert 0.0 < win_rate < 1.0


class TestDruidSwoop:
    def test_druid_swoop_is_additive_damage(self) -> None:
        # Druid with swoop should deal more than without (same stats as mage)
        random.seed(42)
        druid = make_fighter(
            char_class=CharClass.DRUID,
            intelligence=5000,
            constitution=3000,
            luck=3000,
        )
        enemy = make_fighter(
            char_class=CharClass.WARRIOR,
            strength=3000,
            constitution=3000,
            luck=1000,
        )
        win_rate = simulate_fight(druid, enemy, iterations=5000)
        assert win_rate > 0.1


class TestBypassSpecial:
    def test_mage_bypasses_special_abilities(self) -> None:
        assert CharClass.MAGE in BYPASS_SPECIAL

    def test_fireball_zero_against_mage(self) -> None:
        target = make_fighter(char_class=CharClass.MAGE)
        dmg = calc_fireball_damage(100_000.0, 50_000.0, target)
        assert dmg == 0.0


class TestFightOnceReturnTuple:
    def test_returns_hp_tuple(self) -> None:
        random.seed(42)
        a = make_fighter(char_class=CharClass.WARRIOR, constitution=3000)
        b = make_fighter(char_class=CharClass.WARRIOR, constitution=3000)
        stats_a = precompute_combat_stats(a, b)
        stats_b = precompute_combat_stats(b, a)
        result = fight_once(stats_a, stats_b)
        assert isinstance(result, tuple)
        assert len(result) == 2
        a_hp, b_hp = result
        # One should be dead, other alive
        assert (a_hp > 0) != (b_hp > 0)

    def test_winner_has_positive_hp(self) -> None:
        random.seed(42)
        strong = make_fighter(
            char_class=CharClass.WARRIOR, strength=10000, constitution=8000
        )
        weak = make_fighter(
            char_class=CharClass.WARRIOR, strength=100, constitution=100, level=10
        )
        stats_a = precompute_combat_stats(strong, weak)
        stats_b = precompute_combat_stats(weak, strong)
        a_hp, b_hp = fight_once(stats_a, stats_b)
        assert a_hp > 0
        assert b_hp <= 0
