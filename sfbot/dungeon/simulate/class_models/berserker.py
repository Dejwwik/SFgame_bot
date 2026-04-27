from typing import override

from sfbot.dungeon.simulate.class_models.base import ClassModel, FightContext
from sfbot.dungeon.simulate.combat import will_skip
from sfbot.dungeon.simulate.constants import BERSERKER_SKIP_LIMIT, SKIP_TYPE_CONTROL


class BerserkerModel(ClassModel):
    """Chain-skip: forces the attacker to lose consecutive turns (up to BERSERKER_SKIP_LIMIT)."""

    @override
    def check_control_skip(self, ctx: FightContext) -> bool:
        """Roll for chain-skip. Each success extends the chain, capped at BERSERKER_SKIP_LIMIT."""
        if will_skip(
            ctx.defender_fighter,
            ctx.attacker_fighter,
            SKIP_TYPE_CONTROL,
            skip_count=self.skip_count,
            skip_limit=BERSERKER_SKIP_LIMIT,
        ):
            self.skip_count += 1
            return True
        self.skip_count = 0
        return False
