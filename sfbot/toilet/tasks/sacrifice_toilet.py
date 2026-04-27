from sfbot import Bot
from sfbot.constants import TOILET_UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < TOILET_UNLOCK_LEVEL:
        return False
    return bot.toilet.can_sacrifice


async def run(bot: Bot) -> None:
    await bot.toilet.sacrifice_async(bot.inventory, bot.character.char_class)
