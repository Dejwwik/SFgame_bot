from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.reward.inbox import extract_coupon_candidates


def should_run(bot: Bot) -> bool:
    return bool(bot.inbox.message_ids)


async def run(bot: Bot) -> None:
    msg_id = bot.inbox.message_ids[0]
    try:
        text = await bot.inbox.read_async(msg_id)
        for code in extract_coupon_candidates(text):
            await bot.coupon.redeem_async(code)
        await bot.inbox.delete_async(msg_id)
    except APIError as exc:
        get_main_logger().warning(f"Coupon: message {msg_id}: {exc}")
