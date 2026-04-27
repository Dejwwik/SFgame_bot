from sfbot import Bot
from sfbot.constants import PET_UNLOCK_LEVEL
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if bot.character.level < PET_UNLOCK_LEVEL:
        return False
    if not bot.pets.can_fight_pvp_now():
        return False
    return bool(bot.pets.get_unfought_pvp_elements())


async def run(bot: Bot) -> None:
    logger = get_main_logger()
    if not bot.pets.can_fight_pvp_now():
        return

    unfought = bot.pets.get_unfought_pvp_elements()
    if not unfought:
        return

    # Fight one element per cycle, next element on next run
    element = unfought[0]
    try:
        await bot.pets.fight_pvp_async(element)
    except APIError as exc:
        logger.warning(f"Pets: PvP {element.name} failed — {exc}")
