from sfbot.constants import VALUES_DELIMITER
from sfbot.logging import get_main_logger
from sfbot.reward.models import RewardChest, Task
from sfbot.reward.utils import claimable_chests, parse_rewards, parse_tasks
from sfbot.session import GameSession


# Event task chests (Goblin Gleeman — "Event" tab, may be locked)
# DailyTaskClaim:2/{pos} to claim unlocked chests
class EventReward:
    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.tasks: list[Task] = []
        self.rewards: list[RewardChest] = []
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data

        raw = data.get("eventtasklist", "")
        if raw:
            parts = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
            self.tasks = parse_tasks(parts)
        else:
            self.tasks = []

        # Same 3-chest format, empty when event is locked
        raw = data.get("eventtaskrewardpreview", "")
        if raw:
            values = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
            self.rewards = parse_rewards(values)
        else:
            self.rewards = []

    def refresh(self) -> None:
        self._parse()

    @property
    def claimable(self) -> list[int]:
        return claimable_chests(self.tasks, self.rewards)

    @property
    def has_claimable(self) -> bool:
        return bool(self.claimable)

    async def claim_all_async(self) -> None:
        logger = get_main_logger()
        for pos in self.claimable:
            await self.session.request_and_update_async(
                "DailyTaskClaim", f"2/{pos + 1}"
            )
            logger.info(f"Event: claimed chest {pos + 1}")
