from sfbot import Bot
from sfbot.underworld.constants import UNLOCK_LEVEL, BuildingType


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    return bot.underworld.is_unlocked


async def run(bot: Bot) -> None:
    uw = bot.underworld
    has_extractor = uw.building_level(BuildingType.SOUL_EXTRACTOR) >= 1
    has_gold_pit = uw.building_level(BuildingType.GOLD_PIT) >= 1
    await uw.collect_resources_async(souls=has_extractor, silver=has_gold_pit)
