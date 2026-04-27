from math import ceil

import pytest

from sfbot.constants.enums import CharClass
from sfbot.dungeon.enums import RuneType
from sfbot.dungeon.simulate import (
    calc_armor_reduction,
    calc_attribute_bonus,
    calc_class_multiplier,
    calc_crit_chance,
    calc_crit_multiplier,
    calc_damage_range,
    calc_rune_bonus,
    estimate_hand_damage,
    estimate_weapon_damage,
    fighter_from_character,
    fighter_from_monster,
    simulate_fight,
    simulate_sequential_fight,
)
from sfbot.dungeon.simulate.combat import will_skip
from sfbot.dungeon.simulate.constants import (
    CLASS_DAMAGE_BONUS,
    CRIT_ENCHANTMENT_BONUS,
    HAND_DAMAGE_MAX_RATIO,
    HAND_DAMAGE_MIN_RATIO,
    HAND_DAMAGE_MULTIPLIER,
    MAX_RUNE_DAMAGE,
    MAX_RUNE_RESISTANCE,
    NECROMANCER_DH_BONUS,
)
from sfbot.dungeon.tests.conftest import make_attrs, make_fighter, make_monster
from sfbot.simulate.combat import MAX_CRIT_CHANCE
from sfbot.simulate.constants import (
    ARMOR_MULTIPLIER,
    COMPANION_HEALTH_MULTIPLIER,
    CRIT_BASE,
    CRIT_GLADIATOR_BONUS,
    DAMAGE_MULTIPLIER,
    HEALTH_MULTIPLIER,
    MAX_DAMAGE_REDUCTION,
    SKIP_CHANCE,
    WEAPON_MULTIPLIER,
    WINGS_HP_MULTIPLIER,
)

# --- Configuration tables ---


class TestConfigTables:
    def test_all_classes_have_health_multiplier(self) -> None:
        for cls in CharClass:
            assert cls in HEALTH_MULTIPLIER

    def test_all_classes_have_weapon_multiplier(self) -> None:
        for cls in CharClass:
            assert cls in WEAPON_MULTIPLIER

    def test_all_classes_have_damage_multiplier(self) -> None:
        for cls in CharClass:
            assert cls in DAMAGE_MULTIPLIER

    def test_all_classes_have_armor_multiplier(self) -> None:
        for cls in CharClass:
            assert cls in ARMOR_MULTIPLIER

    def test_all_classes_have_max_damage_reduction(self) -> None:
        for cls in CharClass:
            assert cls in MAX_DAMAGE_REDUCTION

    def test_all_classes_have_skip_chance(self) -> None:
        for cls in CharClass:
            assert cls in SKIP_CHANCE


# --- Fighter ---


class TestFighter:
    def test_get_main_attr_warrior(self) -> None:
        fighter = make_fighter(char_class=CharClass.WARRIOR, strength=5000)
        assert fighter.get_main_attr() == 5000

    def test_get_main_attr_mage(self) -> None:
        fighter = make_fighter(char_class=CharClass.MAGE, intelligence=7000)
        assert fighter.get_main_attr() == 7000

    def test_get_main_attr_scout(self) -> None:
        fighter = make_fighter(char_class=CharClass.SCOUT, dexterity=6000)
        assert fighter.get_main_attr() == 6000

    def test_total_health_uses_constitution_and_level(self) -> None:
        fighter = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            constitution=1000,
        )
        expected = 1000 * HEALTH_MULTIPLIER[CharClass.WARRIOR] * (100 + 1)
        assert fighter.get_total_health() == expected

    def test_total_health_with_life_potion(self) -> None:
        fighter = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            constitution=1000,
            has_life_potion=True,
        )
        base = 1000 * HEALTH_MULTIPLIER[CharClass.WARRIOR] * (100 + 1)
        expected = ceil(base * WINGS_HP_MULTIPLIER)
        assert fighter.get_total_health() >= expected

    def test_total_health_with_portal_bonus(self) -> None:
        fighter = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            constitution=1000,
            portal_hp_bonus=50,
        )
        base = 1000 * HEALTH_MULTIPLIER[CharClass.WARRIOR] * (100 + 1)
        # Portal adds 50%
        assert fighter.get_total_health() > base

    def test_total_health_uses_fixed_health_when_set(self) -> None:
        """Monsters have pre-computed health from JSON."""
        fighter = make_fighter(health=9999)
        assert fighter.get_total_health() == 9999.0

    def test_rune_health_bonus_increases_hp(self) -> None:
        base_fighter = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            constitution=1000,
        )
        rune_fighter = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            constitution=1000,
            rune_health=15,
        )
        assert rune_fighter.get_total_health() > base_fighter.get_total_health()


# --- Fighter factories ---


class TestFighterFromMonster:
    def test_basic_conversion(self) -> None:
        monster = make_monster(
            char_class=CharClass.MAGE,
            level=50,
            strength=100,
            intelligence=500,
            health=5000,
            min_dmg=20,
            max_dmg=40,
        )
        fighter = fighter_from_monster(monster)
        assert fighter.char_class == CharClass.MAGE
        assert fighter.level == 50
        assert fighter.strength == 100
        assert fighter.intelligence == 500
        assert fighter.health == 5000
        assert fighter.min_dmg == 20.0
        assert fighter.max_dmg == 40.0

    def test_null_damage_uses_weapon_estimate(self) -> None:
        """Null damage monsters (Twister) get estimated weapon damage from dungeon data."""
        monster = make_monster(min_dmg=None, max_dmg=None)
        fighter = fighter_from_monster(monster)
        expected_min, expected_max = estimate_weapon_damage(
            monster.level, monster.char_class
        )
        assert fighter.min_dmg == expected_min
        assert fighter.max_dmg == expected_max

    def test_rune_type_converted(self) -> None:
        monster = make_monster(rune_type=40, rune_damage=25)
        fighter = fighter_from_monster(monster)
        assert fighter.rune_type == RuneType.FIRE
        assert fighter.rune_value == 25

    def test_no_rune_type_becomes_none(self) -> None:
        monster = make_monster(rune_type=0)
        fighter = fighter_from_monster(monster)
        assert fighter.rune_type == RuneType.NONE

    def test_resistances_carried_over(self) -> None:
        monster = make_monster(
            fire_resistance=25,
            cold_resistance=50,
            lightning_resistance=75,
        )
        fighter = fighter_from_monster(monster)
        assert fighter.fire_resistance == 25
        assert fighter.cold_resistance == 50
        assert fighter.lightning_resistance == 75


class TestFighterFromCharacter:
    def test_basic_construction(self) -> None:
        attrs = make_attrs(strength=5000, dexterity=1000, intelligence=1000)
        fighter = fighter_from_character(
            char_class=CharClass.WARRIOR,
            level=100,
            total_attrs=attrs,
            armor=500,
            min_dmg=100,
            max_dmg=200,
        )
        assert fighter.char_class == CharClass.WARRIOR
        assert fighter.level == 100
        assert fighter.strength == 5000
        assert fighter.min_dmg == 100.0
        assert fighter.max_dmg == 200.0

    def test_all_optional_params(self) -> None:
        attrs = make_attrs()
        fighter = fighter_from_character(
            char_class=CharClass.MAGE,
            level=200,
            total_attrs=attrs,
            armor=300,
            min_dmg=50,
            max_dmg=100,
            portal_hp_bonus=25,
            portal_dmg_bonus=30,
            rune_type=RuneType.COLD,
            rune_value=40,
            fire_resistance=15,
            cold_resistance=20,
            lightning_resistance=10,
            rune_health=10,
            gladiator=12,
            has_sword_of_vengeance=True,
            has_life_potion=True,
        )
        assert fighter.portal_hp_bonus == 25
        assert fighter.portal_dmg_bonus == 30
        assert fighter.rune_type == RuneType.COLD
        assert fighter.gladiator == 12
        assert fighter.has_sword_of_vengeance is True
        assert fighter.has_life_potion is True


# --- Combat calculations ---


class TestCalcAttributeBonus:
    def test_same_main_attr_class(self) -> None:
        """Two warriors: target's STR partially cancels attacker's."""
        attacker = make_fighter(char_class=CharClass.WARRIOR, strength=2000)
        target = make_fighter(char_class=CharClass.WARRIOR, strength=1000)
        bonus = calc_attribute_bonus(attacker, target)
        effective = max(2000 // 2, 2000 - 1000 // 2)
        expected = 1.0 + effective / 10.0
        assert bonus == pytest.approx(expected)

    def test_different_main_attr_class(self) -> None:
        """Warrior vs Mage: uses target's STR (attacker's main attr type)."""
        attacker = make_fighter(char_class=CharClass.WARRIOR, strength=2000)
        # target.strength defaults to 5000 in make_fighter
        target = make_fighter(char_class=CharClass.MAGE, intelligence=5000)
        bonus = calc_attribute_bonus(attacker, target)
        # target_main = target.STR = 5000
        effective = max(2000 // 2, 2000 - 5000 // 2)
        expected = 1.0 + effective / 10.0
        assert bonus == pytest.approx(expected)

    def test_zero_main_attr(self) -> None:
        attacker = make_fighter(char_class=CharClass.WARRIOR, strength=0)
        target = make_fighter(char_class=CharClass.MAGE)
        bonus = calc_attribute_bonus(attacker, target)
        assert bonus == 1.0


class TestCalcArmorReduction:
    def test_mage_bypasses_armor(self) -> None:
        attacker = make_fighter(char_class=CharClass.MAGE)
        target = make_fighter(armor=9999)
        assert calc_armor_reduction(attacker, target) == 0.0

    def test_zero_armor_returns_zero(self) -> None:
        attacker = make_fighter(char_class=CharClass.WARRIOR)
        target = make_fighter(armor=0)
        assert calc_armor_reduction(attacker, target) == 0.0

    def test_reduction_capped_at_max(self) -> None:
        attacker = make_fighter(char_class=CharClass.WARRIOR, level=1)
        target = make_fighter(char_class=CharClass.WARRIOR, armor=999_999)
        reduction = calc_armor_reduction(attacker, target)
        assert reduction == MAX_DAMAGE_REDUCTION[CharClass.WARRIOR]

    def test_normal_armor_calculation(self) -> None:
        attacker = make_fighter(char_class=CharClass.WARRIOR, level=100)
        target = make_fighter(char_class=CharClass.WARRIOR, armor=500)
        reduction = calc_armor_reduction(attacker, target)
        expected = ARMOR_MULTIPLIER[CharClass.WARRIOR] * 500 / 100
        assert reduction == pytest.approx(
            min(expected, MAX_DAMAGE_REDUCTION[CharClass.WARRIOR])
        )


class TestCalcRuneBonus:
    def test_no_rune_returns_zero(self) -> None:
        attacker = make_fighter(rune_type=RuneType.NONE)
        target = make_fighter()
        assert calc_rune_bonus(attacker, target) == 0.0

    def test_zero_rune_value_returns_zero(self) -> None:
        attacker = make_fighter(rune_type=RuneType.FIRE, rune_value=0)
        target = make_fighter()
        assert calc_rune_bonus(attacker, target) == 0.0

    def test_fire_rune_vs_no_resistance(self) -> None:
        attacker = make_fighter(rune_type=RuneType.FIRE, rune_value=30)
        target = make_fighter(fire_resistance=0)
        bonus = calc_rune_bonus(attacker, target)
        assert bonus == pytest.approx(30.0 / 100.0)

    def test_fire_rune_vs_full_resistance(self) -> None:
        attacker = make_fighter(rune_type=RuneType.FIRE, rune_value=30)
        target = make_fighter(fire_resistance=75)
        bonus = calc_rune_bonus(attacker, target)
        assert bonus == pytest.approx((1.0 - 75 / 100.0) * (30 / 100.0))

    def test_rune_damage_capped_at_max(self) -> None:
        attacker = make_fighter(rune_type=RuneType.FIRE, rune_value=999)
        target = make_fighter(fire_resistance=0)
        bonus = calc_rune_bonus(attacker, target)
        assert bonus == pytest.approx(MAX_RUNE_DAMAGE / 100.0)

    def test_resistance_capped_at_max(self) -> None:
        attacker = make_fighter(rune_type=RuneType.COLD, rune_value=30)
        target = make_fighter(cold_resistance=999)
        bonus = calc_rune_bonus(attacker, target)
        expected = (1.0 - MAX_RUNE_RESISTANCE / 100.0) * (30 / 100.0)
        assert bonus == pytest.approx(expected)

    def test_cold_rune_uses_cold_resistance(self) -> None:
        attacker = make_fighter(rune_type=RuneType.COLD, rune_value=20)
        target = make_fighter(cold_resistance=40, fire_resistance=75)
        bonus = calc_rune_bonus(attacker, target)
        expected = (1.0 - 40 / 100.0) * (20 / 100.0)
        assert bonus == pytest.approx(expected)

    def test_lightning_rune_uses_lightning_resistance(self) -> None:
        attacker = make_fighter(rune_type=RuneType.LIGHTNING, rune_value=20)
        target = make_fighter(lightning_resistance=30, fire_resistance=75)
        bonus = calc_rune_bonus(attacker, target)
        expected = (1.0 - 30 / 100.0) * (20 / 100.0)
        assert bonus == pytest.approx(expected)


class TestCalcClassMultiplier:
    def test_base_multiplier_used(self) -> None:
        attacker = make_fighter(char_class=CharClass.WARRIOR)
        target = make_fighter(char_class=CharClass.SCOUT)
        multiplier = calc_class_multiplier(attacker, target)
        assert multiplier == pytest.approx(DAMAGE_MULTIPLIER[CharClass.WARRIOR])

    def test_necromancer_vs_demon_hunter_additive(self) -> None:
        attacker = make_fighter(char_class=CharClass.NECROMANCER)
        target = make_fighter(char_class=CharClass.DEMON_HUNTER)
        multiplier = calc_class_multiplier(attacker, target)
        expected = DAMAGE_MULTIPLIER[CharClass.NECROMANCER] + NECROMANCER_DH_BONUS
        assert multiplier == pytest.approx(expected)

    def test_mage_vs_paladin_multiplicative(self) -> None:
        attacker = make_fighter(char_class=CharClass.MAGE)
        target = make_fighter(char_class=CharClass.PALADIN)
        multiplier = calc_class_multiplier(attacker, target)
        expected = (
            DAMAGE_MULTIPLIER[CharClass.MAGE]
            * CLASS_DAMAGE_BONUS[(CharClass.MAGE, CharClass.PALADIN)]
        )
        assert multiplier == pytest.approx(expected)

    def test_druid_vs_mage_bonus(self) -> None:
        attacker = make_fighter(char_class=CharClass.DRUID)
        target = make_fighter(char_class=CharClass.MAGE)
        multiplier = calc_class_multiplier(attacker, target)
        expected = (
            DAMAGE_MULTIPLIER[CharClass.DRUID]
            * CLASS_DAMAGE_BONUS[(CharClass.DRUID, CharClass.MAGE)]
        )
        assert multiplier == pytest.approx(expected)


class TestCalcCritChance:
    def test_zero_level_target_returns_zero(self) -> None:
        attacker = make_fighter(luck=5000)
        target = make_fighter(level=0)
        assert calc_crit_chance(attacker, target) == 0.0

    def test_normal_calculation(self) -> None:
        attacker = make_fighter(luck=1000)
        target = make_fighter(level=100)
        chance = calc_crit_chance(attacker, target)
        expected = 1000 * 2.5 / 100 / 100.0
        assert chance == pytest.approx(expected)

    def test_capped_at_max(self) -> None:
        attacker = make_fighter(luck=999_999)
        target = make_fighter(level=1)
        assert calc_crit_chance(attacker, target) == pytest.approx(MAX_CRIT_CHANCE)


class TestCalcCritMultiplier:
    def test_base_crit_multiplier(self) -> None:
        attacker = make_fighter()
        target = make_fighter()
        assert calc_crit_multiplier(attacker, target) == pytest.approx(CRIT_BASE)

    def test_enchantment_adds_bonus(self) -> None:
        attacker = make_fighter(has_sword_of_vengeance=True)
        target = make_fighter()
        expected = CRIT_BASE + CRIT_ENCHANTMENT_BONUS
        assert calc_crit_multiplier(attacker, target) == pytest.approx(expected)

    def test_gladiator_advantage(self) -> None:
        attacker = make_fighter(gladiator=10)
        target = make_fighter(gladiator=5)
        expected = CRIT_BASE + CRIT_GLADIATOR_BONUS * 5
        assert calc_crit_multiplier(attacker, target) == pytest.approx(expected)

    def test_negative_gladiator_advantage_clamped(self) -> None:
        """Target has higher gladiator — no penalty, just base."""
        attacker = make_fighter(gladiator=3)
        target = make_fighter(gladiator=10)
        assert calc_crit_multiplier(attacker, target) == pytest.approx(CRIT_BASE)

    def test_combined_bonuses(self) -> None:
        attacker = make_fighter(has_sword_of_vengeance=True, gladiator=8)
        target = make_fighter(gladiator=3)
        expected = CRIT_BASE + CRIT_ENCHANTMENT_BONUS + CRIT_GLADIATOR_BONUS * 5
        assert calc_crit_multiplier(attacker, target) == pytest.approx(expected)


class TestCalcDamageRange:
    def test_basic_damage_range(self) -> None:
        attacker = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            strength=5000,
            min_dmg=100.0,
            max_dmg=200.0,
        )
        target = make_fighter(
            char_class=CharClass.MAGE,
            level=100,
            armor=0,
        )
        damage_min, damage_max = calc_damage_range(attacker, target)
        assert damage_min > 0
        assert damage_max > damage_min

    def test_portal_bonus_scales_damage(self) -> None:
        base_fighter = make_fighter(portal_dmg_bonus=0)
        bonus_fighter = make_fighter(portal_dmg_bonus=50)
        target = make_fighter(armor=0)
        base_min, _ = calc_damage_range(base_fighter, target)
        bonus_min, _ = calc_damage_range(bonus_fighter, target)
        assert bonus_min > base_min


# --- Main simulation ---


class TestSimulateFight:
    def test_strong_player_wins_most(self) -> None:
        player = make_fighter(
            char_class=CharClass.WARRIOR,
            level=200,
            strength=20_000,
            constitution=10_000,
            luck=5000,
            min_dmg=500.0,
            max_dmg=1000.0,
        )
        monster = make_fighter(
            char_class=CharClass.WARRIOR,
            level=10,
            strength=100,
            constitution=50,
            luck=20,
            min_dmg=5.0,
            max_dmg=10.0,
            health=100,
        )
        win_rate = simulate_fight(player, monster, iterations=1000)
        assert win_rate > 0.9

    def test_weak_player_loses_most(self) -> None:
        player = make_fighter(
            char_class=CharClass.WARRIOR,
            level=10,
            strength=100,
            constitution=50,
            luck=20,
            min_dmg=5.0,
            max_dmg=10.0,
        )
        monster = make_fighter(
            char_class=CharClass.WARRIOR,
            level=200,
            strength=20_000,
            constitution=10_000,
            luck=5000,
            min_dmg=500.0,
            max_dmg=1000.0,
            health=500_000,
        )
        win_rate = simulate_fight(player, monster, iterations=1000)
        assert win_rate < 0.1

    def test_win_rate_between_zero_and_one(self) -> None:
        player = make_fighter()
        monster = make_fighter(health=5000)
        win_rate = simulate_fight(player, monster, iterations=500)
        assert 0.0 <= win_rate <= 1.0

    def test_single_iteration(self) -> None:
        player = make_fighter()
        monster = make_fighter(health=5000)
        win_rate = simulate_fight(player, monster, iterations=1)
        assert win_rate in (0.0, 1.0)

    def test_enchantment_gives_advantage(self) -> None:
        """Player with enchantment should win more often than without."""
        base_player = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            strength=5000,
            constitution=3000,
            luck=2000,
            min_dmg=100.0,
            max_dmg=200.0,
        )
        enchanted_player = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            strength=5000,
            constitution=3000,
            luck=2000,
            min_dmg=100.0,
            max_dmg=200.0,
            has_sword_of_vengeance=True,
            has_shadow_of_cowboy=True,
        )
        monster = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            strength=4000,
            constitution=2500,
            luck=1500,
            min_dmg=80.0,
            max_dmg=160.0,
            health=50_000,
        )
        base_rate = simulate_fight(base_player, monster, iterations=2000)
        enchant_rate = simulate_fight(enchanted_player, monster, iterations=2000)
        # Enchanted should be at least as good (allow small variance)
        assert enchant_rate >= base_rate - 0.05


# --- Companion mechanics ---


class TestCompanionHealthMultiplier:
    def test_companion_warrior_gets_bonus_hp(self) -> None:
        """Bert (Warrior companion) has 6.1x HP vs 5.0x normal."""
        normal = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            constitution=1000,
        )
        companion = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            constitution=1000,
            is_companion=True,
        )
        normal_hp = normal.get_total_health()
        companion_hp = companion.get_total_health()
        assert companion_hp > normal_hp
        expected_ratio = (
            COMPANION_HEALTH_MULTIPLIER[CharClass.WARRIOR]
            / HEALTH_MULTIPLIER[CharClass.WARRIOR]
        )
        assert companion_hp / normal_hp == pytest.approx(expected_ratio, rel=0.01)

    def test_companion_mage_same_hp_as_normal(self) -> None:
        """Mark (Mage companion) has same HP multiplier as normal Mage."""
        normal = make_fighter(
            char_class=CharClass.MAGE,
            level=100,
            constitution=1000,
        )
        companion = make_fighter(
            char_class=CharClass.MAGE,
            level=100,
            constitution=1000,
            is_companion=True,
        )
        assert companion.get_total_health() == normal.get_total_health()

    def test_companion_scout_same_hp_as_normal(self) -> None:
        """Kunigunde (Scout companion) has same HP multiplier as normal Scout."""
        normal = make_fighter(
            char_class=CharClass.SCOUT,
            level=100,
            constitution=1000,
        )
        companion = make_fighter(
            char_class=CharClass.SCOUT,
            level=100,
            constitution=1000,
            is_companion=True,
        )
        assert companion.get_total_health() == normal.get_total_health()


class TestCompanionSkipChance:
    def test_companion_warrior_cannot_block(self) -> None:
        """Companion Warriors have 0% block chance."""
        defender = make_fighter(char_class=CharClass.WARRIOR, is_companion=True)
        attacker = make_fighter(char_class=CharClass.WARRIOR)
        # Run many times — companion warrior should never skip
        skips = sum(1 for _ in range(1000) if will_skip(defender, attacker))
        assert skips == 0

    def test_normal_warrior_can_block(self) -> None:
        defender = make_fighter(char_class=CharClass.WARRIOR, is_companion=False)
        attacker = make_fighter(char_class=CharClass.WARRIOR)
        skips = sum(1 for _ in range(1000) if will_skip(defender, attacker))
        assert skips > 0

    def test_companion_scout_can_dodge(self) -> None:
        """Kunigunde (Scout companion) has 50% dodge like normal Scout."""
        defender = make_fighter(char_class=CharClass.SCOUT, is_companion=True)
        attacker = make_fighter(char_class=CharClass.WARRIOR)
        skips = sum(1 for _ in range(1000) if will_skip(defender, attacker))
        assert skips > 0


# --- Hand damage estimation ---


class TestEstimateHandDamage:
    def test_level_10_or_below(self) -> None:
        min_dmg, max_dmg = estimate_hand_damage(10, CharClass.WARRIOR)
        assert min_dmg == 1.0
        assert max_dmg == 2.0

    def test_level_1(self) -> None:
        min_dmg, max_dmg = estimate_hand_damage(1, CharClass.MAGE)
        assert min_dmg == 1.0
        assert max_dmg == 2.0

    def test_warrior_level_100(self) -> None:
        """Rust reference example: 0.7 * (100-9) * 2.0 = 127.4"""
        min_dmg, max_dmg = estimate_hand_damage(100, CharClass.WARRIOR)
        base = HAND_DAMAGE_MULTIPLIER * (100 - 9) * WEAPON_MULTIPLIER[CharClass.WARRIOR]
        expected_min = max(1.0, float(ceil(base * HAND_DAMAGE_MIN_RATIO)))
        expected_max = max(2.0, float(round(base * HAND_DAMAGE_MAX_RATIO)))
        assert min_dmg == pytest.approx(expected_min)
        assert max_dmg == pytest.approx(expected_max)

    def test_mage_has_higher_damage_than_warrior(self) -> None:
        """Mage weapon multiplier (4.5) > Warrior (2.0)."""
        _, mage_max = estimate_hand_damage(100, CharClass.MAGE)
        _, warrior_max = estimate_hand_damage(100, CharClass.WARRIOR)
        assert mage_max > warrior_max

    def test_returns_positive_values(self) -> None:
        for cls in CharClass:
            min_dmg, max_dmg = estimate_hand_damage(50, cls)
            assert min_dmg >= 1.0
            assert max_dmg >= 2.0
            assert max_dmg >= min_dmg


class TestFighterFromMonsterNullDamage:
    def test_null_damage_uses_weapon_estimate(self) -> None:
        """Twister monsters with null damage get estimated weapon damage from dungeon data."""
        monster = make_monster(
            char_class=CharClass.WARRIOR,
            level=100,
            min_dmg=None,
            max_dmg=None,
        )
        fighter = fighter_from_monster(monster)
        assert fighter.min_dmg > 0
        assert fighter.max_dmg > 0
        expected_min, expected_max = estimate_weapon_damage(100, CharClass.WARRIOR)
        assert fighter.min_dmg == pytest.approx(expected_min)
        assert fighter.max_dmg == pytest.approx(expected_max)

    def test_explicit_damage_preserved(self) -> None:
        monster = make_monster(min_dmg=50, max_dmg=100)
        fighter = fighter_from_monster(monster)
        assert fighter.min_dmg == 50.0
        assert fighter.max_dmg == 100.0


class TestFighterFromCharacterCompanion:
    def test_is_companion_flag_set(self) -> None:
        attrs = make_attrs()
        fighter = fighter_from_character(
            char_class=CharClass.WARRIOR,
            level=100,
            total_attrs=attrs,
            armor=500,
            min_dmg=100,
            max_dmg=200,
            is_companion=True,
        )
        assert fighter.is_companion is True

    def test_default_is_not_companion(self) -> None:
        attrs = make_attrs()
        fighter = fighter_from_character(
            char_class=CharClass.WARRIOR,
            level=100,
            total_attrs=attrs,
            armor=500,
            min_dmg=100,
            max_dmg=200,
        )
        assert fighter.is_companion is False


# --- Sequential team fight ---


class TestSimulateSequentialFight:
    def test_strong_team_wins(self) -> None:
        """Strong 4-person team should beat a weak monster."""
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
        player = make_fighter(
            char_class=CharClass.WARRIOR,
            level=200,
            strength=20_000,
            constitution=10_000,
            luck=5000,
            min_dmg=500.0,
            max_dmg=1000.0,
        )
        monster = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            strength=5000,
            constitution=3000,
            luck=1000,
            min_dmg=100.0,
            max_dmg=200.0,
            health=50_000,
        )
        fighters = companions + [player]
        win_rate = simulate_sequential_fight(fighters, monster, iterations=500)
        assert win_rate > 0.9

    def test_weak_team_loses(self) -> None:
        companions = [
            make_fighter(
                char_class=CharClass.WARRIOR,
                level=10,
                strength=100,
                constitution=50,
                luck=20,
                min_dmg=5.0,
                max_dmg=10.0,
                is_companion=True,
            ),
        ]
        player = make_fighter(
            char_class=CharClass.WARRIOR,
            level=10,
            strength=100,
            constitution=50,
            luck=20,
            min_dmg=5.0,
            max_dmg=10.0,
        )
        monster = make_fighter(
            char_class=CharClass.WARRIOR,
            level=300,
            strength=50_000,
            constitution=30_000,
            luck=10_000,
            min_dmg=2000.0,
            max_dmg=4000.0,
            health=2_000_000,
        )
        fighters = companions + [player]
        win_rate = simulate_sequential_fight(fighters, monster, iterations=500)
        assert win_rate < 0.1

    def test_team_better_than_solo(self) -> None:
        """4v1 should have higher win rate than 1v1 against same monster."""
        player = make_fighter(
            char_class=CharClass.WARRIOR,
            level=100,
            strength=5000,
            constitution=3000,
            luck=2000,
            min_dmg=100.0,
            max_dmg=200.0,
        )
        companions = [
            make_fighter(
                char_class=CharClass.WARRIOR,
                level=100,
                strength=4000,
                constitution=2500,
                luck=1500,
                min_dmg=80.0,
                max_dmg=160.0,
                is_companion=True,
            ),
            make_fighter(
                char_class=CharClass.MAGE,
                level=100,
                intelligence=4000,
                constitution=2000,
                luck=1500,
                min_dmg=70.0,
                max_dmg=140.0,
                is_companion=True,
            ),
            make_fighter(
                char_class=CharClass.SCOUT,
                level=100,
                dexterity=4000,
                constitution=2500,
                luck=1500,
                min_dmg=80.0,
                max_dmg=160.0,
                is_companion=True,
            ),
        ]
        monster = make_fighter(
            char_class=CharClass.WARRIOR,
            level=150,
            strength=10_000,
            constitution=8_000,
            luck=3000,
            min_dmg=300.0,
            max_dmg=600.0,
            health=200_000,
        )
        solo_rate = simulate_fight(player, monster, iterations=1000)
        team_rate = simulate_sequential_fight(
            companions + [player],
            monster,
            iterations=1000,
        )
        assert team_rate >= solo_rate - 0.05

    def test_empty_fighters_returns_zero(self) -> None:
        monster = make_fighter(health=5000)
        assert simulate_sequential_fight([], monster, iterations=100) == 0.0

    def test_win_rate_between_zero_and_one(self) -> None:
        player = make_fighter()
        monster = make_fighter(health=50_000)
        rate = simulate_sequential_fight([player], monster, iterations=100)
        assert 0.0 <= rate <= 1.0
