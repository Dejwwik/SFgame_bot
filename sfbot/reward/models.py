from dataclasses import dataclass
from enum import StrEnum


class MessageStatus(StrEnum):
    UNREAD = "0"
    READ = "1"
    CLAIMED = "2"


@dataclass(slots=True)
class RewardChest:
    opened: bool
    required_points: int


@dataclass(slots=True)
class Task:
    progress: int
    required: int
    reward_points: int

    @property
    def is_completed(self) -> bool:
        return self.progress >= self.required
