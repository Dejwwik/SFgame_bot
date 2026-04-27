from sfbot import Bot
from sfbot.constants import Attribute
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return not bot.arena.is_completed and bot.arena.is_free


async def run(bot: Bot) -> None:
    if bot.arena.is_completed or not bot.arena.is_free:
        return

    my_totals = bot.character.total_attrs
    my_main = max(
        my_totals[Attribute.STRENGTH],
        my_totals[Attribute.DEXTERITY],
        my_totals[Attribute.INTELLIGENCE],
    )
    my_con = my_totals[Attribute.CONSTITUTION]

    opponents = await bot.arena.get_opponents_async()

    best = bot.arena.find_best_opponent(opponents, my_main, my_con)

    try:
        await bot.arena.fight_async(best.name)
    except (APIError, ValueError) as exc:
        get_main_logger().warning(f"Arena: {exc}")
