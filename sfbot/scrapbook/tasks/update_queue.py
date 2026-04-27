"""Task: score pre-crawled players by missing scrapbook items, update opponent queue."""

from sfbot import Bot
from sfbot.logging import get_main_logger
from sfbot.persistence import clear_opponents, insert_opponents
from sfbot.scrapbook.constants import QUEUE_REFRESH_INTERVAL
from sfbot.scrapbook.persistence import get_last_crawl_ts, set_last_crawl_ts


def should_run(bot: Bot) -> bool:
    return bool(bot.scrapbook.owned_positions) and bot.scrapbook.missing_items > 0


async def run(bot: Bot) -> None:
    logger = get_main_logger()
    scrapbook = bot.scrapbook
    if scrapbook is None:
        return

    account = bot.session.character_id
    now = bot.session.server_time()
    last_ts = await get_last_crawl_ts(account)
    if now - last_ts < QUEUE_REFRESH_INTERVAL:
        return

    targets = await scrapbook.rank_from_db_async(bot.character.level)

    if not targets:
        await set_last_crawl_ts(account, now)
        return

    names = [t.name for t in targets]
    await clear_opponents(account)
    await insert_opponents(account, names)
    await set_last_crawl_ts(account, now)

    logger.info(
        f"Scrapbook: queued {len(names)} opponents "
        f"(top: {targets[0].name} with {targets[0].missing} missing, "
        f"{scrapbook.item_pct:.1f}% complete)"
    )
