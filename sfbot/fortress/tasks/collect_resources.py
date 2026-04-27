from sfbot import Bot
from sfbot.fortress.fortress import UNLOCK_LEVEL, BuildingType


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    return bot.fortress.is_unlocked


async def run(bot: Bot) -> None:
    f = bot.fortress
    has_wood = f.building_level(BuildingType.WOODCUTTER) >= 1
    has_mine = f.building_level(BuildingType.QUARRY) >= 1
    has_academy = f.building_level(BuildingType.ACADEMY) >= 1
    await f.collect_resources_async(wood=has_wood, stone=has_mine, xp=has_academy)
