from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    h = bot.hellevator
    if not h.is_active:
        return False
    return (
        not h.is_joined
        or h.cards_available > 0
        or h.today_reward_claimable
        or h.yesterday_reward_claimable
    )


async def run(bot: Bot) -> None:
    try:
        await bot.hellevator.manage_async()
    except APIError as exc:
        get_main_logger().warning(f"Hellevator: {exc}")
