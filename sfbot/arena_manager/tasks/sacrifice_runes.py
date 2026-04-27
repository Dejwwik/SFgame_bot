from sfbot import Bot
from sfbot.arena_manager.constants import ARENA_MANAGER_UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < ARENA_MANAGER_UNLOCK_LEVEL:
        return False
    return bot.arena_manager.is_unlocked


async def run(bot: Bot) -> None:
    if not bot.arena_manager.should_sacrifice():
        return
    await bot.arena_manager.sacrifice_async()
