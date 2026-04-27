from sfbot import Bot
from sfbot.fortress.fortress import UnitType, UNLOCK_LEVEL


def should_run(bot: Bot) -> bool:
    if bot.character.level < UNLOCK_LEVEL:
        return False
    if not bot.fortress.is_unlocked:
        return False
    return bot.fortress.can_train(UnitType.SOLDIER)


async def run(bot: Bot) -> None:
    f = bot.fortress
    if not f.can_train(UnitType.SOLDIER):
        return
    await f.train_unit_async(UnitType.SOLDIER, count=f.trainable_count(UnitType.SOLDIER))
