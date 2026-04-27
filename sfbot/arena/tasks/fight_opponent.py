from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.persistence import load_opponents, remove_opponent


def should_run(bot: Bot) -> bool:
    return bot.arena.is_free and bot.arena.is_completed


async def run(bot: Bot) -> None:
    logger = get_main_logger()

    opponents = await load_opponents(bot.session.character_id)
    if not opponents:
        return

    name = opponents[0]
    logger.info(f"Arena: fighting {name} ({len(opponents) - 1} remaining in queue)")
    try:
        await bot.arena.fight_async(name)
        bot.arena.refresh()
    except (APIError, ValueError) as exc:
        logger.warning(f"Arena: failed vs {name}: {exc}")

    await remove_opponent(bot.session.character_id, name)
