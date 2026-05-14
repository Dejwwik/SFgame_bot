from sfbot.constants import VALUES_DELIMITER
from sfbot.expedition.constants import (
    AE_SPECIAL,
    AE_THIRST_SEC,
    ES_BUSY_UNTIL,
    ES_CURRENT_FLOOR,
    ES_FLOOR_STAGE,
    ES_HEROISM,
    ES_TARGET_AMOUNT,
    ES_TARGET_CURRENT,
    ES_TARGET_THING,
    EXPEDITION_FIELDS,
    REWARD_PRIORITY,
    TARGET_CHAIN,
    TARGET_TO_BOUNTY,
    TOTAL_FLOORS,
    ExpeditionThing,
    FloorStage,
    RewardType,
)
from sfbot.logging import get_main_logger
from sfbot.session import GameSession


def _thing_name(tid: int) -> str:
    try:
        return ExpeditionThing(tid).name
    except ValueError:
        return str(tid)


def _reward_name(rtype: int) -> str:
    try:
        return RewardType(rtype).name
    except ValueError:
        return str(rtype)


class Expedition:
    """Expedition event — automated expedition runs."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.logger = get_main_logger()
        self.is_available: bool = False
        self.has_active: bool = False
        self.floor_stage: int = 0
        self.current_floor: int = 0
        self.target_thing: int = 0
        self.target_current: int = 0
        self.target_amount: int = 0
        self.heroism: int = 0
        self.busy_until: int = 0
        self.available_count: int = 0
        self.encounters: list[tuple[int, int]] = []  # (thing_id, heroism)
        self.rewards: list[tuple[int, int]] = []  # (reward_type, amount)
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data

        # Check if expedition event is active
        event_raw = data.get("expeditionevent", "")
        if not event_raw:
            self.is_available = False
            return
        event_vals = [int(x) for x in event_raw.split(VALUES_DELIMITER) if x]
        if len(event_vals) < 2:
            self.is_available = False
            return
        event_end = event_vals[1]
        self.is_available = event_end > self.session.server_time()

        # Parse available expeditions
        avail_raw = data.get("expeditions", "")
        if avail_raw:
            avail_vals = [int(x) for x in avail_raw.split(VALUES_DELIMITER) if x]
            self.available_count = len(avail_vals) // EXPEDITION_FIELDS
            self._available_data = avail_vals
        else:
            self.available_count = 0
            self._available_data = []

        # Parse active expedition state
        state_raw = data.get("expeditionstate", "")
        if not state_raw:
            self.has_active = False
            return

        vals = [int(x) for x in state_raw.split(VALUES_DELIMITER) if x]
        if len(vals) < ES_BUSY_UNTIL + 1:
            self.has_active = False
            return

        self.has_active = True
        self.current_floor = vals[ES_CURRENT_FLOOR]
        self.floor_stage = vals[ES_FLOOR_STAGE]
        self.target_thing = vals[ES_TARGET_THING]
        self.target_current = vals[ES_TARGET_CURRENT]
        self.target_amount = vals[ES_TARGET_AMOUNT]
        self.heroism = vals[ES_HEROISM]
        self.busy_until = vals[ES_BUSY_UNTIL]

        # Parse crossroad encounters
        cross_raw = data.get("expeditioncrossroad", "")
        if cross_raw:
            cross_vals = [int(x) for x in cross_raw.split(VALUES_DELIMITER) if x]
            self.encounters = [
                (cross_vals[i], cross_vals[i + 1])
                for i in range(0, len(cross_vals) - 1, 2)
            ]
        else:
            self.encounters = []

        # Parse reward options from boss halftime/final
        halftime_raw = data.get("expeditionhalftime", "")
        if halftime_raw:
            ht_vals = [int(x) for x in halftime_raw.split(VALUES_DELIMITER) if x]
            # First value is negated boss id, rest are (type, amount) pairs
            self.rewards = [
                (ht_vals[i], ht_vals[i + 1])
                for i in range(1, len(ht_vals) - 1, 2)
            ]
        else:
            self.rewards = []

    def refresh(self) -> None:
        self._parse()

    @property
    def is_finished(self) -> bool:
        if not self.has_active:
            return True
        if self.current_floor >= TOTAL_FLOORS and self.floor_stage == FloorStage.WAITING:
            return self.busy_until <= self.session.server_time()
        return False

    @property
    def is_waiting(self) -> bool:
        if not self.has_active:
            return False
        if self.floor_stage != FloorStage.WAITING:
            return False
        return self.busy_until > self.session.server_time()

    def _best_encounter_index(self) -> int:
        """Pick the best encounter based on target collection strategy.

        Priority:
        1. Target thing itself (collects toward goal)
        2. Chain prerequisite — furthest along the chain wins if multiple offered
        3. Matching bounty (gives +10 heroism bonus on future target finds)
        4. Highest heroism
        """
        if not self.encounters:
            return 0

        chain = TARGET_CHAIN.get(self.target_thing, [])
        target_bounty = TARGET_TO_BOUNTY.get(self.target_thing)

        # Priority 1: target thing itself
        for i, (thing_id, _) in enumerate(self.encounters):
            if thing_id == self.target_thing:
                return i

        # Priority 2: chain prerequisite (pick furthest along the chain)
        if chain:
            best_chain_idx: int | None = None
            best_chain_rank = -1
            for i, (thing_id, _) in enumerate(self.encounters):
                if thing_id in chain:
                    rank = chain.index(thing_id)
                    if rank > best_chain_rank:
                        best_chain_rank = rank
                        best_chain_idx = i
            if best_chain_idx is not None:
                return best_chain_idx

        # Priority 3: matching bounty
        for i, (thing_id, _) in enumerate(self.encounters):
            if target_bounty is not None and thing_id == target_bounty:
                return i

        # Priority 4: highest heroism
        best_idx = 0
        best_heroism = self.encounters[0][1]
        for i, (_, heroism) in enumerate(self.encounters):
            if heroism > best_heroism:
                best_heroism = heroism
                best_idx = i
        return best_idx

    def _get_best_expedition_index(self) -> int:
        """Pick the expedition with the lowest thirst cost. 0-indexed."""
        if self.available_count <= 0:
            return 0

        best_idx = 0
        best_thirst = self._available_data[AE_THIRST_SEC]
        for i in range(self.available_count):
            offset = i * EXPEDITION_FIELDS
            # Prefer daily task expeditions (special=2)
            special = self._available_data[offset + AE_SPECIAL]
            if special == 2:
                return i
            thirst = self._available_data[offset + AE_THIRST_SEC]
            if thirst < best_thirst:
                best_thirst = thirst
                best_idx = i
        return best_idx

    def _best_reward_index(self) -> int:
        """Pick the most valuable reward. 0-indexed."""
        if not self.rewards:
            return 0
        best_idx = 0
        best_priority = -1
        for i, (reward_type, _) in enumerate(self.rewards):
            priority = REWARD_PRIORITY.get(reward_type, 0)
            if priority > best_priority:
                best_priority = priority
                best_idx = i
        return best_idx

    async def start_async(self, index: int) -> None:
        """Start an expedition. index is 0-based."""
        await self.session.request_and_update_async(
            "ExpeditionStart", str(index + 1)
        )
        self.refresh()
        self.logger.info(
            f"Expedition: started, target {_thing_name(self.target_thing)} "
            f"(0/{self.target_amount})"
        )

    async def pick_encounter_async(self, index: int) -> None:
        """Pick a crossroad encounter. index is 0-based."""
        await self.session.request_and_update_async(
            "ExpeditionProceed", str(index + 1)
        )
        self.refresh()

    async def proceed_async(self) -> None:
        """Continue expedition (boss fight or collect reward)."""
        await self.session.request_and_update_async("ExpeditionProceed", "1")
        self.refresh()

    async def run_expedition_async(self) -> None:
        """Run through the full expedition lifecycle."""
        if not self.is_available:
            return

        # Start a new expedition if none is active or current one is finished
        if not self.has_active or self.is_finished:
            if self.available_count <= 0:
                return
            idx = self._get_best_expedition_index()
            await self.start_async(idx)

        # Process the active expedition
        while self.has_active and not self.is_finished:
            if self.is_waiting:
                return

            if self.floor_stage == FloorStage.CROSSROADS:
                idx = self._best_encounter_index()
                thing_id = self.encounters[idx][0] if self.encounters else 0
                self.logger.info(
                    f"Expedition: floor {self.current_floor}, "
                    f"picked {_thing_name(thing_id)}"
                )
                await self.pick_encounter_async(idx)

            elif self.floor_stage == FloorStage.BOSS:
                self.logger.info(
                    f"Expedition: floor {self.current_floor}, fighting boss"
                )
                await self.proceed_async()

            elif self.floor_stage == FloorStage.REWARDS:
                idx = self._best_reward_index()
                reward_type, amount = self.rewards[idx] if self.rewards else (0, 0)
                self.logger.info(
                    f"Expedition: floor {self.current_floor}, "
                    f"picked {_reward_name(reward_type)} x{amount}"
                )
                await self.pick_encounter_async(idx)

            elif self.floor_stage == FloorStage.WAITING:
                if self.busy_until <= self.session.server_time():
                    await self.session.poll_async()
                    self.refresh()
                else:
                    return
            else:
                self.logger.warning(f"Expedition: unknown floor_stage {self.floor_stage}")
                return

        if self.is_finished:
            self.logger.info(
                f"Expedition: completed with {self.heroism} heroism, "
                f"collected {self.target_current}/{self.target_amount} "
                f"{_thing_name(self.target_thing)}"
            )
