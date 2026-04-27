from sfbot import Bot


def should_run(bot: Bot) -> bool:
    if bot.character.potion_slots_full:
        return False
    return bot.inventory.has_drinkable_potions(
        bot.character.main_attr,
        bot.character.active_potion_sizes,
    )


async def run(bot: Bot) -> None:
    await bot.inventory.drink_potion_async(
        bot.character.main_attr,
        bot.character.active_potion_sizes,
    )
