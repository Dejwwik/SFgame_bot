from sfbot import Bot
from sfbot.fortress.fortress import BuildingType, UnitType, UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.fortress.is_unlocked:
        return False
    f = bot.fortress
    if f.building_level(BuildingType.SMITHY) < 1:
        return False
    return any(f.can_upgrade_unit(u) for u in UnitType)


async def run(bot: Bot) -> None:
    f = bot.fortress
    for unit in UnitType:
        if f.can_upgrade_unit(unit):
            await f.upgrade_unit_async(unit)
            f.refresh()
