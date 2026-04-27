from sfbot import Bot
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger

UNLOCK_NAMES: dict[int, str] = {
    9: "Deeds",
    21: "Pet",
    30: "Dungeon",
    31: "Shadow Dungeon",
}


def should_run(bot: Bot) -> bool:
    return bool(bot.pending_unlocks)


async def run(bot: Bot) -> None:
    logger = get_main_logger()

    for main_ident, sub_ident in list(bot.pending_unlocks):
        label = UNLOCK_NAMES.get(main_ident, f"unknown({main_ident})")
        try:
            await bot.unlock_feature_async(main_ident, sub_ident)
            logger.info(f"Unlock: {label} {main_ident}/{sub_ident}")
        except APIError as exc:
            logger.warning(f"Unlock: {label} {main_ident}/{sub_ident} failed — {exc}")
