from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger

GOLD_RESERVE_HOURS = 50


def should_run(bot: Bot) -> bool:
    reserve_silver = bot.guard.wage_per_hour * GOLD_RESERVE_HOURS
    return bot.resources.silver_total > reserve_silver


async def run(bot: Bot) -> None:
    reserve_silver = bot.guard.wage_per_hour * GOLD_RESERVE_HOURS
    try:
        await bot.attributes.upgrade_loop_async(
            base_attrs=bot.character.base_attrs,
            weights=bot.base_attrs_target_ratios,
            reserve_silver=reserve_silver,
        )
    except APIError as exc:
        get_main_logger().warning(f"Attributes: {exc}")
