"""Core combat loop and Monte Carlo simulation runners.

fight_once() executes a single fight between two pre-computed fighters.
simulate_fight() runs N iterations for 1v1 win rate estimation.
simulate_sequential_fight() runs N iterations for team vs monster (Tower/Shadow).
"""

import random

from sfbot.dungeon.models import Fighter
from sfbot.dungeon.simulate.class_models import (
    CombatStats,
    FightContext,
    TurnState,
    create_model,
)
from sfbot.dungeon.simulate.combat import calc_hit_damage, will_skip
from sfbot.dungeon.simulate.constants import (
    MAX_ROUNDS,
    PD_TINCTURE_DMG_BONUS,
    PD_TINCTURE_SKIP_CHANCE,
    SKIP_TYPE_DEFAULT,
)
from sfbot.dungeon.simulate.fighters import precompute_combat_stats


def fight_once(
    player_stats: CombatStats,
    opponent_stats: CombatStats,
) -> tuple[float, float]:
    """Run one fight iteration. Returns (player_hp, opponent_hp) after fight."""
    player_model = create_model(player_stats.fighter.char_class)
    opponent_model = create_model(opponent_stats.fighter.char_class)
    ctx = FightContext(player_stats, opponent_stats, player_model, opponent_model)

    # --- Phase 1: Pre-combat abilities (BattleMage fireball) ---
    ctx.a_is_attacker = True
    player_model.before(ctx)
    if ctx.hp_b <= 0:
        return ctx.hp_a, ctx.hp_b
    ctx.a_is_attacker = False
    opponent_model.before(ctx)
    if ctx.hp_a <= 0:
        return ctx.hp_a, ctx.hp_b

    # --- Phase 2: Determine who attacks first (Shadow of Cowboy enchant) ---
    player_fighter = player_stats.fighter
    opponent_fighter = opponent_stats.fighter
    if player_fighter.has_shadow_of_cowboy == opponent_fighter.has_shadow_of_cowboy:
        ctx.a_is_attacker = random.random() < 0.5
    else:
        ctx.a_is_attacker = player_fighter.has_shadow_of_cowboy

    # --- Phase 3: Main combat loop ---
    for _ in range(MAX_ROUNDS):
        attacker_model = ctx.attacker_model
        defender_model = ctx.defender_model

        # Step 1: Berserker chain-skip check (defender forces attacker to lose turn)
        if defender_model.check_control_skip(ctx):
            ctx.swap()
            continue
        defender_model.skip_count = 0

        # Step 2: Rage scaling (increases each turn: 1 + turn/6)
        rage = ctx.get_rage()

        # Step 3: Build mutable turn state from pre-computed stats
        attacker_combat = ctx.attacker_stats
        turn_state = TurnState(
            dmg_min=attacker_combat.dmg_min,
            dmg_max=attacker_combat.dmg_max,
            crit_chance=attacker_combat.crit_chance,
            crit_mult=attacker_combat.crit_mult,
            dmg_mult=1.0,
            defender_skip_override=None,
        )

        # Step 4: Defender modifies attacker's dodge chance (Paladin stance, Necro spectre)
        skip_override = defender_model.get_skip_override(ctx)
        if skip_override is not None:
            turn_state.defender_skip_override = skip_override

        # Step 5: Plague Doctor tincture debuff (reduces damage, increases dodge chance)
        tincture_phase = ctx.tincture_on_attacker
        if tincture_phase > 0:
            phase_index = tincture_phase - 1
            turn_state.dmg_mult *= 1.0 + PD_TINCTURE_DMG_BONUS[phase_index]
            turn_state.defender_skip_override = PD_TINCTURE_SKIP_CHANCE[phase_index]

        # Step 6: Attacker self-buffs (Paladin stance, Bard melody, Druid bear rage)
        attacker_model.before_attack(ctx, turn_state)

        # Step 7: Control abilities (Druid swoop, PD tincture throw, Necro summon)
        control_result = attacker_model.control(ctx, turn_state, rage)
        if control_result is not None:
            if not control_result:
                break  # Defender killed by control ability
            ctx.swap()
            continue  # Control ability consumed the turn

        # Step 8: Normal attack — check if defender dodges
        dodged = will_skip(
            ctx.defender_fighter,
            ctx.attacker_fighter,
            SKIP_TYPE_DEFAULT,
            override_skip_chance=turn_state.defender_skip_override,
        )

        if dodged:
            # Dodge reaction (Druid enters bear rage on dodge)
            defender_model.on_dodge(ctx, turn_state, rage)
        else:
            # Roll damage and apply
            hit_damage = calc_hit_damage(
                turn_state.dmg_min,
                turn_state.dmg_max,
                rage,
                turn_state.crit_chance,
                turn_state.crit_mult,
            )
            hit_damage *= turn_state.dmg_mult
            alive = ctx.deal_damage_to_defender(hit_damage)
            if not alive:
                break
            # Post-hit ability (Assassin second weapon strike)
            if attacker_model.after_hit(ctx, turn_state, rage):
                break

        # Step 9: End of turn (Necro minion follow-up attack, Bard melody tick)
        if attacker_model.end_turn(ctx, turn_state, rage):
            break

        ctx.swap()

    return ctx.hp_a, ctx.hp_b


# --- Monte Carlo 1v1 simulation ---


def simulate_fight(
    player: Fighter, monster: Fighter, iterations: int = 10_000
) -> float:
    """Simulate N fight iterations and return player win ratio (0.0 to 1.0)."""
    wins = 0
    player_stats = precompute_combat_stats(player, monster)
    monster_stats = precompute_combat_stats(monster, player)

    for _ in range(iterations):
        player_hp, _ = fight_once(player_stats, monster_stats)
        if player_hp > 0:
            wins += 1

    return wins / iterations


# --- Monte Carlo sequential team simulation (Tower / Shadow dungeons) ---


def simulate_sequential_fight(
    fighters: list[Fighter],
    monster: Fighter,
    iterations: int = 10_000,
) -> float:
    """Simulate a sequential team fight (Tower/Shadow dungeon style).

    Fighters enter one at a time (companions first, then player).
    The monster retains HP between fights. Rage resets each fight.
    Monster damage/crit is recalculated per opponent.
    """
    if not fighters:
        return 0.0

    wins = 0
    monster_total_hp = monster.get_total_health()

    # Pre-compute per-fighter combat values
    all_fighter_stats: list[CombatStats] = []
    all_monster_stats: list[CombatStats] = []
    for fighter in fighters:
        all_fighter_stats.append(precompute_combat_stats(fighter, monster))
        all_monster_stats.append(precompute_combat_stats(monster, fighter))

    for _ in range(iterations):
        remaining_monster_hp = monster_total_hp
        team_won = False

        for fighter_index, fighter_stats in enumerate(all_fighter_stats):
            if remaining_monster_hp <= 0:
                team_won = True
                break

            monster_vs_fighter = all_monster_stats[fighter_index]
            adjusted_monster_stats = CombatStats(
                dmg_min=monster_vs_fighter.dmg_min,
                dmg_max=monster_vs_fighter.dmg_max,
                dmg_min2=monster_vs_fighter.dmg_min2,
                dmg_max2=monster_vs_fighter.dmg_max2,
                crit_chance=monster_vs_fighter.crit_chance,
                crit_mult=monster_vs_fighter.crit_mult,
                total_hp=remaining_monster_hp,
                fighter=monster_vs_fighter.fighter,
            )

            _, monster_hp_after = fight_once(fighter_stats, adjusted_monster_stats)
            if monster_hp_after <= 0:
                team_won = True
                break
            else:
                remaining_monster_hp = monster_hp_after

        if team_won:
            wins += 1

    return wins / iterations
