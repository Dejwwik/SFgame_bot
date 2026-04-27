from sfbot import Bot
from sfbot.underworld.constants import (
    UNIT_PRICE_SOULS,
    UNLOCK_LEVEL,
)


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.underworld.is_unlocked:
        return False
    return bot.underworld.pick_unit_upgrade() is not None


async def run(bot: Bot) -> None:
    uw = bot.underworld
    reserved_souls = uw.next_building_soul_cost()

    unit = uw.pick_unit_upgrade()
    if unit is None:
        return
    cost = uw.unit_upgrade_costs.get(unit)
    if not cost:
        return
    if bot.resources.souls - cost[UNIT_PRICE_SOULS] < reserved_souls:
        return
    await uw.upgrade_unit_async(unit)
