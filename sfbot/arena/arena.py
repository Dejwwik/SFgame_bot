from dataclasses import dataclass

from sfbot.constants import (
    CHARACTER_ATTR_COUNT,
    CHARACTER_BASE_ATTR_INDEX,
    CHARACTER_BONUS_ATTR_INDEX,
    CHARACTER_CLASS_INDEX,
    CHARACTER_LEVEL_INDEX,
    VALUES_DELIMITER,
    Attribute,
    CharClass,
)
from sfbot.fight import FightResult, parse_fight_result
from sfbot.logging import get_main_logger
from sfbot.session import GameSession

# --- Arena constants ---
MAX_XP_FIGHTS = 10
SCORE_WEIGHT_MAIN_ATTR = 1.5
SCORE_WEIGHT_CON = 1.0

# --- Arena response field indices ---
ARENA_NEXT_FREE_FIGHT_INDEX = 0
ARENA_FIGHTS_FOR_XP_INDEX = 1
ARENA_ENEMY_IDS_START_INDEX = 2
ARENA_ENEMY_IDS_END_INDEX = 5


@dataclass(slots=True)
class Opponent:
    """A parsed arena opponent."""

    name: str
    level: int
    class_id: int
    base_attrs: list[int]  # [Str, Dex, Int, Con, Luck]
    bonus_attrs: list[int]  # [Str, Dex, Int, Con, Luck]

    @property
    def total_attrs(self) -> list[int]:
        return [b + a for b, a in zip(self.base_attrs, self.bonus_attrs)]

    @property
    def main_attr_value(self) -> int:
        """Main attribute value based on class (Str for warriors, Dex for scouts, etc.)."""
        return self.total_attrs[CharClass.main_attr_index(self.class_id)]

    @property
    def constitution(self) -> int:
        return self.total_attrs[Attribute.CONSTITUTION]

    def score_opponent(self, my_main_attr: int, my_con: int) -> float:
        """Score this opponent — higher = harder to beat.

        Computes the difference between opponent and own attrs:
        ``(their_main - my_main) * 1.5 + (their_con - my_con) * 1.0``
        Most negative score = easiest target.
        """
        return (self.main_attr_value - my_main_attr) * SCORE_WEIGHT_MAIN_ATTR + (
            self.constitution - my_con
        ) * SCORE_WEIGHT_CON


class Arena:
    """Arena opponent analysis and fighting."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()

    def _parse(self) -> None:
        raw = self.session.login_data["arena"].split(VALUES_DELIMITER)
        values = list(map(int, raw))  # Convert raw string data into integers

        self.next_free_fight: int = values[ARENA_NEXT_FREE_FIGHT_INDEX]
        self.fights_for_xp: int = values[ARENA_FIGHTS_FOR_XP_INDEX]
        self.enemy_ids: list[int] = values[
            ARENA_ENEMY_IDS_START_INDEX:ARENA_ENEMY_IDS_END_INDEX
        ]

    def refresh(self) -> None:
        self._parse()

    def _build_opponent(self, result: dict[str, str]) -> Opponent:
        opponent_raw_data = result["otherplayersavecharacter"]
        opponent_name = result["otherplayername.r"]

        opponent_data = list(map(int, opponent_raw_data.split(VALUES_DELIMITER)))

        level = opponent_data[CHARACTER_LEVEL_INDEX] & 0xFFFF
        class_id = opponent_data[CHARACTER_CLASS_INDEX] - 1
        base_attrs = opponent_data[
            CHARACTER_BASE_ATTR_INDEX : CHARACTER_BASE_ATTR_INDEX + CHARACTER_ATTR_COUNT
        ]
        bonus_attrs = opponent_data[
            CHARACTER_BONUS_ATTR_INDEX : CHARACTER_BONUS_ATTR_INDEX
            + CHARACTER_ATTR_COUNT
        ]

        return Opponent(
            name=opponent_name,
            level=level,
            class_id=class_id,
            base_attrs=base_attrs,
            bonus_attrs=bonus_attrs,
        )

    async def get_opponents_async(self) -> list[Opponent]:
        """Async version of get_opponents."""

        await self.session.request_and_update_async("PlayerArenaEnemy", "")
        self.refresh()

        opponents: list[Opponent] = []
        for enemy_id in self.enemy_ids:
            result = await self.session.request_and_update_async(
                "PlayerLookAt", str(enemy_id)
            )
            opponent = self._build_opponent(result)
            opponents.append(opponent)
        return opponents

    def find_best_opponent(
        self,
        opponents: list[Opponent],
        my_main_attr: int,
        my_con_attr: int,
    ) -> Opponent:
        """Find the opponent with the lowest score (weakest)."""

        return min(
            opponents,
            key=lambda o: o.score_opponent(my_main_attr, my_con_attr),
        )

    async def fight_async(self, opponent_name: str) -> FightResult:
        if not self.is_free:
            raise ValueError("Arena fight is not free")

        result = await self.session.request_and_update_async(
            "PlayerArenaFight",
            f"{opponent_name}/'0'",
        )
        self.refresh()
        fight = parse_fight_result(result)
        outcome = "won" if fight.won else "lost"
        get_main_logger().info(f"Arena: {outcome} vs {opponent_name} +{fight.xp:,} XP")
        return fight

    @property
    def is_completed(self) -> bool:
        """True if all 10 XP fights have been completed for today."""
        return self.fights_for_xp >= MAX_XP_FIGHTS

    @property
    def is_free(self) -> bool:
        """True if the next fight costs no mushroom."""
        return self.next_free_fight <= self.session.server_time()
