from sfbot import Bot
from sfbot.constants import WITCH_UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < WITCH_UNLOCK_LEVEL:
        return False
    return bool(bot.witch.missing_enchantments())


async def run(bot: Bot) -> None:
    await bot.witch.buy_all_missing_async()
