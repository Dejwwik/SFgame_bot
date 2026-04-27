from sfbot import Bot
from sfbot.fortress.fortress import UnitType, UNLOCK_LEVEL

UNITS = [UnitType.ARCHER, UnitType.MAGICIAN]


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.fortress.is_unlocked:
        return False
    return any(bot.fortress.can_train(ut) for ut in UNITS)


async def run(bot: Bot) -> None:
    f = bot.fortress
    for ut in UNITS:
        if f.can_train(ut):
            await f.train_unit_async(ut, count=f.trainable_count(ut))
