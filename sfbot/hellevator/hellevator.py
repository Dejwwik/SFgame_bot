from sfbot.constants import VALUES_DELIMITER
from sfbot.fight import parse_fight_result
from sfbot.hellevator.constants import (
    DAILY_REWARD_ITEMS_END,
    DAILY_REWARD_ITEMS_START,
    GT_CARDS_AVAILABLE_INDEX,
    GT_FLOOR_INDEX,
    GT_JOIN_TS_INDEX,
    GT_TIME_END_INDEX,
    GT_TIME_START_INDEX,
)
from sfbot.logging import get_main_logger
from sfbot.session import GameSession


class Hellevator:
    """Hellevator group tournament event — fight monsters, collect hell tokens, claim daily rewards."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.event_start: int = 0
        self.event_end: int = 0
        self.cards_available: int = 0
        self.floor: int = 0
        self.join_ts: int = 0
        self.today_reward_claimable: bool = False
        self.yesterday_reward_claimable: bool = False
        self.refresh()

    def refresh(self) -> None:
        data = self.session.login_data
        if "gttime" not in data:
            self._reset()
            return
        time_vals = [int(x) for x in data["gttime"].split(VALUES_DELIMITER) if x]
        self.event_start = time_vals[GT_TIME_START_INDEX]
        self.event_end = time_vals[GT_TIME_END_INDEX]
        if "gtsave" in data:
            save_vals = [int(x) for x in data["gtsave"].split(VALUES_DELIMITER) if x]
            self.cards_available = save_vals[GT_CARDS_AVAILABLE_INDEX]
            self.floor = save_vals[GT_FLOOR_INDEX]
            self.join_ts = save_vals[GT_JOIN_TS_INDEX]
        self.today_reward_claimable = self._is_claimable("gtdailyreward", data)
        self.yesterday_reward_claimable = self._is_claimable(
            "gtdailyrewardyesterday", data
        )

    def _reset(self) -> None:
        self.event_start = 0
        self.event_end = 0
        self.cards_available = 0
        self.floor = 0
        self.join_ts = 0
        self.today_reward_claimable = False
        self.yesterday_reward_claimable = False

    @staticmethod
    def _is_claimable(field: str, data: dict[str, str]) -> bool:
        if field not in data:
            return False
        vals = [int(x) for x in data[field].split(VALUES_DELIMITER) if x]
        items = vals[DAILY_REWARD_ITEMS_START:DAILY_REWARD_ITEMS_END]
        return any(v > 0 for v in items)

    @property
    def is_active(self) -> bool:
        if self.event_end == 0:
            return False
        return self.session.server_time() < self.event_end

    @property
    def is_joined(self) -> bool:
        return self.join_ts > 0

    async def manage_async(self) -> None:
        if not self.is_joined:
            await self.session.request_and_update_async("GroupTournamentJoin", "")
            self.refresh()

        if self.cards_available > 0:
            await self._fight_async()

        if self.yesterday_reward_claimable:
            await self.session.request_and_update_async(
                "GroupTournamentClaimDailyYesterday", ""
            )
            self.refresh()
            get_main_logger().info("Hellevator: claimed yesterday's reward")

        if self.today_reward_claimable:
            await self.session.request_and_update_async("GroupTournamentClaimDaily", "")
            self.refresh()
            get_main_logger().info("Hellevator: claimed daily reward")

    async def _fight_async(self) -> None:
        result = await self.session.request_and_update_async(
            "GroupTournamentBattle", "0"
        )
        self.refresh()
        fight = parse_fight_result(result)
        outcome = "won" if fight.won else "lost"
        get_main_logger().info(
            f"Hellevator: {outcome} floor {self.floor} +{fight.xp:,} XP"
        )
