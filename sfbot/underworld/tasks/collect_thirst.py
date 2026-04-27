from sfbot import Bot
from sfbot.logging import get_main_logger
from sfbot.underworld.constants import UNLOCK_LEVEL, BuildingType


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.underworld.is_unlocked:
        return False
    if bot.underworld.building_level(BuildingType.ADVENTUROMATIC) < 1:
        return False
    return bot.underworld.current_thirst_collectable > 0


async def run(bot: Bot) -> None:
    uw = bot.underworld
    logger = get_main_logger()
    before = uw.thirst_current
    if await uw.collect_thirst_async():
        logger.info(f"Underworld: collected {before} thirst")
