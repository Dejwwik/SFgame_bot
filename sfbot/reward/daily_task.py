from sfbot.constants import VALUES_DELIMITER
from sfbot.logging import get_main_logger
from sfbot.reward.models import RewardChest, Task
from sfbot.reward.utils import claimable_chests, parse_rewards, parse_tasks
from sfbot.session import GameSession


# Daily task chests (Goblin Gleeman — "Daily reward" tab)
# DailyTaskClaim:1/{pos} to claim unlocked chests
class DailyReward:
    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.tasks: list[Task] = []
        self.rewards: list[RewardChest] = []
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data

        raw = data.get("dailytasklist", "")
        if raw:
            parts = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
            # "dailytasklist" has a leading bell quest count — strip it before parsing
            self.tasks = parse_tasks(parts[1:])
        else:
            self.tasks = []

        # 3 chests with required point thresholds
        raw = data.get("dailytaskrewardpreview", "")
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
                "DailyTaskClaim", f"1/{pos + 1}"
            )
            logger.info(f"Daily: claimed chest {pos + 1}")
