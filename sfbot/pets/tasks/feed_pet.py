from sfbot import Bot
from sfbot.constants import PET_UNLOCK_LEVEL, HabitatType
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger


def should_run(bot: Bot) -> bool:
    if bot.character.level < PET_UNLOCK_LEVEL:
        return False

    feed_limit = bot.pets.get_feed_limit(bot.get_player_state().events)
    for element in HabitatType:
        hab = bot.pets.habitats.get(element)
        if not hab:
            continue
        # No fruits available for this element
        if hab.fruits <= 0:
            continue
        pet = bot.pets.get_pet_to_feed(element)
        # Found a pet that hasn't hit today's feed limit
        if pet and pet.fruits_today < feed_limit:
            return True
    return False


async def run(bot: Bot) -> None:
    logger = get_main_logger()
    state = bot.get_player_state()
    feed_limit = bot.pets.get_feed_limit(state.events)

    for element in HabitatType:
        hab = bot.pets.habitats.get(element)
        if not hab:
            continue

        # No fruits to feed
        if hab.fruits <= 0:
            continue
        pet = bot.pets.get_pet_to_feed(element)
        # No pet exists, or already fed this pet the maximum times today
        if not pet or pet.fruits_today >= feed_limit:
            continue

        try:
            await bot.pets.feed_pet_async(pet.pet_id)
            logger.info(f"Pets: fed pet {pet.pet_id} ({pet.element.name})")
        except APIError as exc:
            logger.warning(
                f"Pets: feed pet {pet.pet_id} ({pet.element.name}) failed — {exc}"
            )
        # Feed only the one pet per task, call task again to feed next pet (if any)
        return
