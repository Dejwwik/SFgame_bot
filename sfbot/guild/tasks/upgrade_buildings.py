from sfbot import Bot


def should_run(bot: Bot) -> bool:
    # Ignore it for the too low level
    if bot.character.level < 20:
        return False
    return bot.guild.should_upgrade_skills(bot.get_player_state())


async def run(bot: Bot) -> None:
    await bot.guild.upgrade_skills_async(bot.get_player_state())
