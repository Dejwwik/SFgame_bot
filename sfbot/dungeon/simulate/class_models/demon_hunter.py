import random
from typing import override

from sfbot.dungeon.simulate.class_models.base import ClassModel, FightContext
from sfbot.dungeon.simulate.constants import (
    BYPASS_SPECIAL,
    DH_REVIVE_CHANCE,
    DH_REVIVE_DECAY,
    DH_REVIVE_HP,
    DH_REVIVE_HP_DECAY,
    DH_REVIVE_HP_MIN,
)


class DemonHunterModel(ClassModel):
    """Revive on death with decaying probability and HP fraction."""

    def __init__(self) -> None:
        super().__init__()
        self.death_triggers = 0

    @override
    def on_death(self, ctx: FightContext) -> bool:
        """Chance to revive with a fraction of max HP.

        Each revive reduces the next revive chance by DH_REVIVE_DECAY and
        the HP fraction by DH_REVIVE_HP_DECAY. Mage attackers negate
        revive entirely (BYPASS_SPECIAL).
        """
        if ctx.attacker_fighter.char_class in BYPASS_SPECIAL:
            return False
        revive_chance = DH_REVIVE_CHANCE - DH_REVIVE_DECAY * self.death_triggers
        if revive_chance <= 0:
            return False
        if random.random() < revive_chance:
            hp_fraction = max(
                DH_REVIVE_HP_MIN,
                DH_REVIVE_HP - self.death_triggers * DH_REVIVE_HP_DECAY,
            )
            ctx.defender_hp = ctx.defender_stats.total_hp * hp_fraction
            self.death_triggers += 1
            ctx.turn += 1
            return True
        return False
