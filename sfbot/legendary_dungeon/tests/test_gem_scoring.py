from sfbot.legendary_dungeon.constants import (
    BOSS_DMG,
    FIGHT_DMG,
    TRAP_DMG,
)
from sfbot.legendary_dungeon.models import (
    GemEffect,
    GemSpecial,
    GemType,
)
from sfbot.legendary_dungeon.tests.conftest import make_gem
from sfbot.legendary_dungeon.utils import (
    effect_hp_impact,
    pick_best_gem,
    remaining_context,
    score_gem,
    special_hp_impact,
)

# ═══════════════════════════════════════════════════════════════════════════
# remaining_context
# ═══════════════════════════════════════════════════════════════════════════


class TestRemainingContext:
    def test_floor_0_returns_all_sections(self):
        sections, bosses = remaining_context(0)
        assert sections == [0, 1, 2, 3]
        assert bosses == [25, 50, 75, 100]

    def test_floor_25_returns_sections_1_through_3(self):
        sections, bosses = remaining_context(25)
        assert sections == [1, 2, 3]
        assert bosses == [50, 75, 100]

    def test_floor_50_returns_sections_2_and_3(self):
        sections, bosses = remaining_context(50)
        assert sections == [2, 3]
        assert bosses == [75, 100]

    def test_floor_75_returns_section_3(self):
        sections, bosses = remaining_context(75)
        assert sections == [3]
        assert bosses == [100]

    def test_floor_24_still_section_0(self):
        sections, bosses = remaining_context(24)
        assert sections == [0, 1, 2, 3]
        assert bosses == [25, 50, 75, 100]

    def test_floor_26_means_section_1_done(self):
        sections, bosses = remaining_context(26)
        assert sections == [1, 2, 3]
        assert bosses == [50, 75, 100]

    def test_floor_99_returns_section_3(self):
        sections, bosses = remaining_context(99)
        assert sections == [3]
        assert bosses == [100]


# ═══════════════════════════════════════════════════════════════════════════
# effect_hp_impact
# ═══════════════════════════════════════════════════════════════════════════


class TestEffectHpImpact:
    def test_damage_from_monsters_positive(self):
        sections = [0, 1, 2, 3]
        bosses = [25, 50, 75, 100]
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_MONSTERS, 20, sections, bosses)
        assert result > 0

    def test_damage_from_monsters_scales_with_power(self):
        sections = [0, 1, 2, 3]
        bosses = [25, 50, 75, 100]
        low = effect_hp_impact(GemEffect.DAMAGE_FROM_MONSTERS, 10, sections, bosses)
        high = effect_hp_impact(GemEffect.DAMAGE_FROM_MONSTERS, 30, sections, bosses)
        assert high > low

    def test_damage_from_monsters_scales_with_sections(self):
        bosses_full = [25, 50, 75, 100]
        bosses_late = [100]
        full = effect_hp_impact(
            GemEffect.DAMAGE_FROM_MONSTERS, 20, [0, 1, 2, 3], bosses_full
        )
        late = effect_hp_impact(GemEffect.DAMAGE_FROM_MONSTERS, 20, [3], bosses_late)
        assert full > late

    def test_damage_from_traps(self):
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_TRAPS, 50, [0, 1, 2, 3], [])
        assert result > 0

    def test_damage_from_sac_doors(self):
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_SAC_DOORS, 25, [0], [])
        assert result > 0

    def test_damage_from_chests(self):
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_CHESTS, 30, [0, 1], [])
        assert result > 0

    def test_damage_from_escape(self):
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_ESCAPE, 20, [0, 1], [])
        assert result > 0

    def test_healing_from_blessings(self):
        result = effect_hp_impact(GemEffect.HEALING_FROM_BLESSINGS, 40, [0, 1], [])
        assert result > 0

    def test_chance_of_keys(self):
        result = effect_hp_impact(
            GemEffect.CHANCE_OF_KEYS, 20, [0, 1, 2, 3], [25, 50, 75, 100]
        )
        assert result > 0

    def test_chance_of_key_after_escape(self):
        result = effect_hp_impact(GemEffect.CHANCE_OF_KEY_AFTER_ESCAPE, 20, [0], [25])
        assert result > 0

    def test_escape_chance(self):
        result = effect_hp_impact(GemEffect.ESCAPE_CHANCE, 30, [0, 1], [])
        assert result > 0

    def test_chance_of_blessing_after_fight(self):
        result = effect_hp_impact(GemEffect.CHANCE_OF_BLESSING_AFTER_FIGHT, 15, [0], [])
        assert result > 0

    def test_chance_of_curse_after_fight(self):
        result = effect_hp_impact(GemEffect.CHANCE_OF_CURSE_AFTER_FIGHT, 10, [0, 1], [])
        assert result > 0

    def test_chance_of_curse_after_escape(self):
        result = effect_hp_impact(GemEffect.CHANCE_OF_CURSE_AFTER_ESCAPE, 10, [0], [])
        assert result > 0

    def test_blessing_or_curse_after_revive(self):
        result = effect_hp_impact(GemEffect.BLESSING_OR_CURSE_AFTER_REVIVE, 50, [0], [])
        assert result > 0

    def test_duration_of_blessings(self):
        result = effect_hp_impact(GemEffect.DURATION_OF_BLESSINGS, 20, [0, 1], [])
        assert result > 0

    def test_duration_of_curses(self):
        result = effect_hp_impact(GemEffect.DURATION_OF_CURSES, 20, [0], [])
        assert result > 0

    def test_chance_of_stronger_curses(self):
        result = effect_hp_impact(GemEffect.CHANCE_OF_STRONGER_CURSES, 15, [0], [])
        assert result > 0

    def test_blessings_in_barrels_chests_corpses(self):
        result = effect_hp_impact(
            GemEffect.BLESSINGS_IN_BARRELS_CHESTS_CORPSES, 25, [0, 1, 2, 3], []
        )
        assert result > 0

    def test_chance_of_blessings_in_barrels(self):
        result = effect_hp_impact(GemEffect.CHANCE_OF_BLESSINGS_IN_BARRELS, 20, [0], [])
        assert result > 0

    def test_chance_of_better_blessings_in_barrels(self):
        result = effect_hp_impact(
            GemEffect.CHANCE_OF_BETTER_BLESSINGS_IN_BARRELS, 20, [0], []
        )
        assert result > 0

    def test_unknown_effect_returns_zero(self):
        # Use a value not in the if-chain
        result = effect_hp_impact(999, 20, [0, 1], [25])  # type: ignore
        assert result == 0.0

    def test_zero_power_returns_zero(self):
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_MONSTERS, 0, [0, 1], [25])
        assert result == 0.0

    def test_empty_sections_returns_zero(self):
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_TRAPS, 20, [], [])
        assert result == 0.0

    def test_damage_from_monsters_correct_value(self):
        # 1 section [0], 1 boss [25], power=100 (p=1.0)
        # total_fight_dmg = 7 * 14.4 = 100.8
        # total_boss_dmg = 19.6
        # result = (100.8 + 19.6) * 1.0 = 120.4
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_MONSTERS, 100, [0], [25])
        expected = 7 * FIGHT_DMG[0] + BOSS_DMG[25]
        assert abs(result - expected) < 0.01

    def test_damage_from_traps_correct_value(self):
        # 2 sections, power=50 (p=0.5)
        # result = 2 * 4 * 10.0 * 0.5 = 40.0
        result = effect_hp_impact(GemEffect.DAMAGE_FROM_TRAPS, 50, [0, 1], [])
        expected = 2 * 4 * TRAP_DMG * 0.5
        assert abs(result - expected) < 0.01


# ═══════════════════════════════════════════════════════════════════════════
# special_hp_impact
# ═══════════════════════════════════════════════════════════════════════════


class TestSpecialHpImpact:
    def test_weaker_monsters_positive(self):
        result = special_hp_impact(GemSpecial.WEAKER_MONSTERS_SPAWN, [0, 1, 2, 3])
        assert result > 0

    def test_stronger_monsters_negative(self):
        result = special_hp_impact(GemSpecial.STRONGER_MONSTERS_SPAWN, [0, 1, 2, 3])
        assert result < 0

    def test_weaker_vs_stronger_symmetric(self):
        weaker = special_hp_impact(GemSpecial.WEAKER_MONSTERS_SPAWN, [0, 1, 2, 3])
        stronger = special_hp_impact(GemSpecial.STRONGER_MONSTERS_SPAWN, [0, 1, 2, 3])
        assert abs(weaker + stronger) < 0.01

    def test_more_traps_negative(self):
        result = special_hp_impact(GemSpecial.MORE_TRAPS_SPAWN, [0, 1])
        assert result < 0

    def test_always_one_trap_negative(self):
        result = special_hp_impact(GemSpecial.ALWAYS_ONE_TRAP, [0])
        assert result < 0

    def test_traps_inflict_curse_negative(self):
        result = special_hp_impact(GemSpecial.TRAPS_INFLICT_CURSE, [0, 1])
        assert result < 0

    def test_more_sac_doors_negative(self):
        result = special_hp_impact(GemSpecial.MORE_SAC_DOORS, [0])
        assert result < 0

    def test_fewer_sac_doors_positive(self):
        result = special_hp_impact(GemSpecial.FEWER_SAC_DOORS, [0])
        assert result > 0

    def test_sac_chests_behind_closed_doors_negative(self):
        result = special_hp_impact(GemSpecial.SAC_CHESTS_BEHIND_CLOSED_DOORS, [0])
        assert result < 0

    def test_more_cursed_doors_negative(self):
        result = special_hp_impact(GemSpecial.MORE_CURSED_DOORS, [0])
        assert result < 0

    def test_fewer_cursed_doors_positive(self):
        result = special_hp_impact(GemSpecial.FEWER_CURSED_DOORS, [0])
        assert result > 0

    def test_cursed_chests_behind_doors_negative(self):
        result = special_hp_impact(GemSpecial.CURSED_CHESTS_BEHIND_CLOSED_DOORS, [0])
        assert result < 0

    def test_chance_of_unlocked_doors_positive(self):
        result = special_hp_impact(GemSpecial.CHANCE_OF_UNLOCKED_DOORS, [0, 1])
        assert result > 0

    def test_chance_of_double_locked_door_negative(self):
        result = special_hp_impact(GemSpecial.CHANCE_OF_DOUBLE_LOCKED_DOOR, [0])
        assert result < 0

    def test_always_one_lock_negative(self):
        result = special_hp_impact(GemSpecial.ALWAYS_ONE_LOCK, [0])
        assert result < 0

    def test_chance_of_epic_doors_positive(self):
        result = special_hp_impact(GemSpecial.CHANCE_OF_EPIC_DOORS, [0, 1, 2])
        assert result > 0

    def test_no_more_epic_chests_negative(self):
        result = special_hp_impact(GemSpecial.NO_MORE_EPIC_CHESTS, [0, 1])
        assert result < 0

    def test_more_mysterious_rooms_negative(self):
        result = special_hp_impact(GemSpecial.MORE_MYSTERIOUS_ROOMS, [0])
        assert result < 0

    def test_fewer_mysterious_rooms_positive(self):
        result = special_hp_impact(GemSpecial.FEWER_MYSTERIOUS_ROOMS, [0])
        assert result > 0

    def test_monsters_behind_doors_negative(self):
        result = special_hp_impact(GemSpecial.MONSTERS_BEHIND_DOORS, [0, 1, 2, 3])
        assert result < 0

    def test_unknown_special_returns_zero(self):
        result = special_hp_impact(9999, [0, 1])  # type: ignore
        assert result == 0.0

    def test_empty_sections(self):
        result = special_hp_impact(GemSpecial.WEAKER_MONSTERS_SPAWN, [])
        assert result == 0.0

    def test_scales_with_sections(self):
        one = special_hp_impact(GemSpecial.MORE_TRAPS_SPAWN, [0])
        four = special_hp_impact(GemSpecial.MORE_TRAPS_SPAWN, [0, 1, 2, 3])
        assert abs(four / one - 4.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════
# score_gem
# ═══════════════════════════════════════════════════════════════════════════


class TestScoreGem:
    def test_pure_advantage_gem_positive(self):
        gem = make_gem(advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=20)
        assert score_gem(gem, 0) > 0

    def test_pure_disadvantage_gem_negative(self):
        gem = make_gem(disadvantage=GemEffect.DAMAGE_FROM_MONSTERS, disadvantage_pwr=20)
        assert score_gem(gem, 0) < 0

    def test_advantage_minus_disadvantage(self):
        gem = make_gem(
            advantage=GemEffect.DAMAGE_FROM_MONSTERS,
            advantage_pwr=30,
            disadvantage=GemEffect.DAMAGE_FROM_TRAPS,
            disadvantage_pwr=10,
        )
        # Big monster reduction minus small trap penalty
        score = score_gem(gem, 0)
        assert score > 0

    def test_special_adds_to_score(self):
        gem_no_special = make_gem(
            advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=20
        )
        gem_with_special = make_gem(
            advantage=GemEffect.DAMAGE_FROM_MONSTERS,
            advantage_pwr=20,
            special=GemSpecial.WEAKER_MONSTERS_SPAWN,
        )
        assert score_gem(gem_with_special, 0) > score_gem(gem_no_special, 0)

    def test_bad_special_reduces_score(self):
        gem_no_special = make_gem(
            advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=20
        )
        gem_with_bad = make_gem(
            advantage=GemEffect.DAMAGE_FROM_MONSTERS,
            advantage_pwr=20,
            special=GemSpecial.STRONGER_MONSTERS_SPAWN,
        )
        assert score_gem(gem_with_bad, 0) < score_gem(gem_no_special, 0)

    def test_empty_gem_scores_zero(self):
        gem = make_gem()
        assert score_gem(gem, 0) == 0.0

    def test_later_floor_lower_score(self):
        gem = make_gem(advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=20)
        early = score_gem(gem, 0)
        late = score_gem(gem, 75)
        assert early > late

    def test_zero_power_contributes_nothing(self):
        gem = make_gem(
            advantage=GemEffect.DAMAGE_FROM_MONSTERS,
            advantage_pwr=0,
            disadvantage=GemEffect.DAMAGE_FROM_TRAPS,
            disadvantage_pwr=0,
        )
        assert score_gem(gem, 0) == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# pick_best_gem
# ═══════════════════════════════════════════════════════════════════════════


class TestPickBestGem:
    def test_picks_highest_scoring_gem(self):
        gems = [
            make_gem(
                typ=GemType.SOUL_OF_THE_RABBIT,
                advantage=GemEffect.DAMAGE_FROM_TRAPS,
                advantage_pwr=10,
            ),
            make_gem(
                typ=GemType.EYE_OF_THE_BULL,
                advantage=GemEffect.DAMAGE_FROM_MONSTERS,
                advantage_pwr=30,
            ),
            make_gem(
                typ=GemType.BOULDER_OF_GREED,
                advantage=GemEffect.DAMAGE_FROM_TRAPS,
                advantage_pwr=5,
            ),
        ]
        result = pick_best_gem(gems, 0)
        assert result is not None
        idx, gem, score = result
        assert idx == 1
        assert gem.typ == GemType.EYE_OF_THE_BULL
        assert score > 0

    def test_single_gem(self):
        gems = [make_gem(advantage=GemEffect.ESCAPE_CHANCE, advantage_pwr=20)]
        result = pick_best_gem(gems, 0)
        assert result is not None
        idx, gem, score = result
        assert idx == 0

    def test_all_negative_picks_least_bad(self):
        gems = [
            make_gem(disadvantage=GemEffect.DAMAGE_FROM_MONSTERS, disadvantage_pwr=30),
            make_gem(disadvantage=GemEffect.DAMAGE_FROM_MONSTERS, disadvantage_pwr=10),
        ]
        result = pick_best_gem(gems, 0)
        assert result is not None
        idx, gem, score = result
        assert idx == 1  # -10 is better than -30
        assert score < 0

    def test_returns_correct_score(self):
        gem = make_gem(advantage=GemEffect.DAMAGE_FROM_MONSTERS, advantage_pwr=20)
        result = pick_best_gem([gem], 0)
        assert result is not None
        _, _, score = result
        expected = score_gem(gem, 0)
        assert abs(score - expected) < 0.01
