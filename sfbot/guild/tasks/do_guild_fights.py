from sfbot import Bot


def should_run(bot: Bot) -> bool:
    if not bot.guild.is_24h_member:
        return False
    return not bot.guild.is_completed


async def run(bot: Bot) -> None:
    await bot.guild.run_daily_async()
