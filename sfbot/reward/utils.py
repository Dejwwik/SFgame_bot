from sfbot.reward.models import RewardChest, Task

TASK_CHUNK_SIZE = 4


# Reward preview format: 3 chests sequentially, each:
#   [opened, required_points, reward_count, (reward_type, amount)...]
def parse_rewards(values: list[int]) -> list[RewardChest]:
    chests: list[RewardChest] = []
    i = 0
    for _ in range(3):
        if i >= len(values):
            break
        opened = values[i] != 0
        required_points = values[i + 1]
        reward_count = values[i + 2]
        chests.append(
            RewardChest(
                opened=opened,
                required_points=required_points,
            )
        )
        i += 3 + reward_count * 2
    return chests


# Task list format: chunks of 4 ints [type, progress, required, reward_points]
def parse_tasks(parts: list[int]) -> list[Task]:
    tasks: list[Task] = []
    for chunk_start in range(0, len(parts) - TASK_CHUNK_SIZE + 1, TASK_CHUNK_SIZE):
        tasks.append(
            Task(
                progress=parts[chunk_start + 1],
                required=parts[chunk_start + 2],
                reward_points=parts[chunk_start + 3],
            )
        )
    return tasks


def earned_points(tasks: list[Task]) -> int:
    return sum(t.reward_points for t in tasks if t.is_completed)


def claimable_chests(tasks: list[Task], rewards: list[RewardChest]) -> list[int]:
    points = earned_points(tasks)
    return [
        i
        for i, chest in enumerate(rewards)
        if not chest.opened and points >= chest.required_points
    ]
