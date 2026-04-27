from sfbot import Bot
from sfbot.constants import PORTAL_UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < PORTAL_UNLOCK_LEVEL:
        return False
    if not bot.guild.is_24h_member:
        return False
    return bot.guild.can_portal


async def run(bot: Bot) -> None:
    await bot.guild.run_portal_async()
