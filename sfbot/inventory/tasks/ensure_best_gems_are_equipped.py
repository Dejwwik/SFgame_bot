from sfbot import Bot


def should_run(bot: Bot) -> bool:
    return bool(bot.inventory.get_gems())


async def run(bot: Bot) -> None:
    profiles = bot.build_comparison_profiles()
    while True:
        socketed = await bot.inventory.socket_best_gem_async(profiles)
        if not socketed:
            break
