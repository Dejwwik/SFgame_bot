from sfbot import Bot
from sfbot.underworld.constants import UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.underworld.is_unlocked:
        return False
    return bot.underworld.can_lure


async def run(bot: Bot) -> None:
    uw = bot.underworld
    remaining = uw.max_lures - uw.lured_today
    for _ in range(remaining):
        player_id = await uw.get_lure_suggestion_async()
        if player_id is None:
            break
        result = await uw.lure_hero_async(player_id)
        if result is None:
            break
        uw.refresh()
        if not uw.can_lure:
            break
