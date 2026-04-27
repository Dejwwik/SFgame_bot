from sfbot import Bot
from sfbot.constants import PET_UNLOCK_LEVEL
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.pets.simulate import get_best_pet_dungeon_fight


def should_run(bot: Bot) -> bool:
    if bot.character.level < PET_UNLOCK_LEVEL:
        return False
    if not bot.pets.can_fight_pet_dungeon_now():
        return False
    return bool(bot.pets.get_explorable_habitats())


async def run(bot: Bot) -> None:
    logger = get_main_logger()

    if not bot.pets.can_fight_pet_dungeon_now():
        return

    result = get_best_pet_dungeon_fight(
        bot.pets.habitats,
        bot.character.gladiator,
    )
    if not result:
        return

    hab = result.habitat
    best_pet = result.pet
    enemy_pos = hab.explored_count + 1

    logger.info(
        f"Pets: {hab.element.name} pet dungeon fight #{enemy_pos} "
        f"with pet {best_pet.pet_id} (lvl {best_pet.level}), "
        f"win chance {result.win_chance:.0%}"
    )

    try:
        await bot.pets.fight_pet_dungeon_async(hab.element, enemy_pos, best_pet.pet_id)
    except APIError as exc:
        logger.warning(f"Pets: {hab.element.name} pet dungeon fight failed — {exc}")
