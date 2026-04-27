from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    return not bot.wheel.is_completed(bot.get_player_state())


async def run(bot: Bot) -> None:
    try:
        await bot.wheel.spin_async(bot.get_player_state(), bot.inventory)
    except ValueError as exc:
        get_main_logger().warning(f"Wheel: {exc}")
    except APIError as exc:
        get_main_logger().warning(f"Wheel: {exc}")
