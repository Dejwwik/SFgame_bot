from sfbot import Bot
from sfbot.constants import PORTAL_UNLOCK_LEVEL
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if bot.character.level < PORTAL_UNLOCK_LEVEL:
        return False
    return bot.dungeon.can_fight_portal


async def run(bot: Bot) -> None:
    logger = get_main_logger()
    try:
        await bot.dungeon.fight_portal_async()
    except APIError as exc:
        logger.warning(f"Portal: fight failed: {exc}")
