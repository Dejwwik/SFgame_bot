from sfbot import Bot


def should_run(bot: Bot) -> bool:
    return True


async def run(bot: Bot) -> None:
    await bot.shop.buy_free_potions_async(bot.inventory)
    await bot.shop.buy_free_special_items_async(bot.inventory)
