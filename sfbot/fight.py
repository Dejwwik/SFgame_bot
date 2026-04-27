from dataclasses import dataclass

from sfbot.constants import VALUES_DELIMITER

FIGHT_WON_INDEX = 0
FIGHT_SILVER_INDEX = 2
FIGHT_XP_INDEX = 3


@dataclass(slots=True)
class FightResult:
    won: bool
    xp: int
    silver: int


def parse_fight_result(result: dict[str, str]) -> FightResult:
    raw = result.get("fightresult.battlereward", "")
    values = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
    return FightResult(
        won=values[FIGHT_WON_INDEX] != 0 if values else False,
        xp=values[FIGHT_XP_INDEX] if len(values) > FIGHT_XP_INDEX else 0,
        silver=values[FIGHT_SILVER_INDEX] if len(values) > FIGHT_SILVER_INDEX else 0,
    )
