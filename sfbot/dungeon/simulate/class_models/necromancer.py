import random
from typing import override

from sfbot.dungeon.models import Fighter
from sfbot.dungeon.simulate.class_models.base import (
    ClassModel,
    CombatStats,
    FightContext,
    TurnState,
)
from sfbot.dungeon.simulate.combat import calc_hit_damage, will_skip
from sfbot.dungeon.simulate.constants import (
    BYPASS_SPECIAL,
    NECRO_SKELETON,
    NECRO_SKELETON_REVIVE_CHANCE,
    NECRO_SKELETON_REVIVE_COUNT,
    NECRO_SKELETON_REVIVE_DURATION,
    NECRO_SPECTRE,
    NECRO_SUMMON_CHANCE,
    NECRO_SUMMON_CRIT_BONUS,
    NECRO_SUMMON_CRIT_CHANCE,
    NECRO_SUMMON_CRIT_CHANCE_BONUS,
    NECRO_SUMMON_DMG_BONUS,
    NECRO_SUMMON_DURATION,
    NECRO_SUMMON_SKIP_CHANCE,
    SKIP_TYPE_DEFAULT,
)
from sfbot.simulate.constants import CRIT_BASE


def calc_necro_minion_damage(
    minion_type: int,
    attacker_stats: CombatStats,
    attacker_dmg_mult: float,
    defender: Fighter,
    rage: float,
    defender_skip_override: float | None = None,
) -> float:
    """Calculate minion attack damage. Each minion type has different crit/dmg bonuses."""
    dmg_bonus = NECRO_SUMMON_DMG_BONUS[minion_type]
    crit_chance_cap = NECRO_SUMMON_CRIT_CHANCE[minion_type]
    crit_chance_bonus = NECRO_SUMMON_CRIT_CHANCE_BONUS[minion_type]
    crit_bonus = NECRO_SUMMON_CRIT_BONUS[minion_type]
    crit_mult = (CRIT_BASE + crit_bonus) * attacker_stats.crit_mult / CRIT_BASE
    crit_chance = min(crit_chance_cap, attacker_stats.crit_chance + crit_chance_bonus)

    minion_dmg_min = attacker_stats.dmg_min * (1.0 + dmg_bonus)
    minion_dmg_max = attacker_stats.dmg_max * (1.0 + dmg_bonus)

    if will_skip(
        defender,
        attacker_stats.fighter,
        SKIP_TYPE_DEFAULT,
        override_skip_chance=defender_skip_override,
    ):
        return 0.0

    dmg = calc_hit_damage(minion_dmg_min, minion_dmg_max, rage, crit_chance, crit_mult)
    dmg *= attacker_dmg_mult
    return dmg


def expire_necro_minion(
    turns: int,
    minion_type: int,
    revives: int,
) -> tuple[int, int | None, int]:
    """Tick down minion duration. Skeletons can revive once on expiry."""
    turns -= 1
    if turns <= 0:
        if (
            minion_type == NECRO_SKELETON
            and revives > 0
            and random.random() < NECRO_SKELETON_REVIVE_CHANCE
        ):
            return NECRO_SKELETON_REVIVE_DURATION, minion_type, revives - 1
        return 0, None, 0
    return turns, minion_type, revives


class NecromancerModel(ClassModel):
    """Summons minions (skeleton/zombie/spectre) that attack alongside the caster."""

    def __init__(self) -> None:
        super().__init__()
        self.minion_type: int | None = None
        self.minion_turns = 0
        self.minion_revives = 0

    @override
    def get_skip_override(self, ctx: FightContext) -> float | None:
        """Spectre minion suppresses the defender's dodge chance."""
        if self.minion_type == NECRO_SPECTRE:
            return NECRO_SUMMON_SKIP_CHANCE[NECRO_SPECTRE]
        return None

    def _expire_minion(self) -> None:
        if self.minion_type is None:
            return
        self.minion_turns, self.minion_type, self.minion_revives = expire_necro_minion(
            self.minion_turns,
            self.minion_type,
            self.minion_revives,
        )

    def _minion_attack(
        self, ctx: FightContext, ts: TurnState, minion_type: int
    ) -> bool:
        """Execute minion attack. Returns True if defender died."""
        minion_rage = ctx.get_rage()
        minion_dmg = calc_necro_minion_damage(
            minion_type,
            ctx.attacker_stats,
            ts.dmg_mult,
            ctx.defender_fighter,
            minion_rage,
            ts.defender_skip_override,
        )
        if minion_dmg > 0:
            if not ctx.deal_damage_to_defender(minion_dmg):
                return True
        return False

    @override
    def control(self, ctx: FightContext, ts: TurnState, rage: float) -> bool | None:
        """Summon a new minion if none active.

        Skipped against Mages (BYPASS_SPECIAL). Minion type is random
        (skeleton, zombie, or spectre), each with unique combat bonuses.
        """
        if ctx.defender_fighter.char_class in BYPASS_SPECIAL:
            return None
        if self.minion_type is not None:
            return None

        if random.random() >= NECRO_SUMMON_CHANCE:
            return None

        ctx.turn += 1
        minion_type = random.randint(0, 2)
        self.minion_type = minion_type
        self.minion_turns = NECRO_SUMMON_DURATION[minion_type]
        self.minion_revives = (
            NECRO_SKELETON_REVIVE_COUNT if minion_type == NECRO_SKELETON else 0
        )

        killed = self._minion_attack(ctx, ts, minion_type)
        self._expire_minion()
        if killed:
            return False
        return True

    @override
    def end_turn(self, ctx: FightContext, ts: TurnState, rage: float) -> bool:
        """Active minion performs a follow-up attack, then tick its duration.

        Skipped against Mages (BYPASS_SPECIAL).
        """
        if self.minion_type is None:
            return False
        if ctx.defender_fighter.char_class in BYPASS_SPECIAL:
            return False
        if ctx.defender_hp <= 0:
            return False

        killed = self._minion_attack(ctx, ts, self.minion_type)
        self._expire_minion()
        return killed
