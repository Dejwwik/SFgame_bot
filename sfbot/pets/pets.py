from dataclasses import dataclass

from sfbot.constants import (
    CHARACTER_STATUS_PET_EXPLORATION_TIMER_INDEX,
    PET_BATTLED_OPPONENT_BASE,
    PET_EXPLORED_BASE,
    PET_FRUITS_TODAY_BASE,
    PET_LEVEL_BASE,
    PET_NEXT_FIGHT_LEVEL_BASE,
    PET_OPPONENT_ID_INDEX,
    PET_OPPONENT_NEXT_FREE_BATTLE_INDEX,
    RESOURCE_FRUITS_BASE_INDEX,
    VALUES_DELIMITER,
    Event,
    HabitatType,
)
from sfbot.fight import FightResult, parse_fight_result
from sfbot.logging import get_main_logger
from sfbot.pets.constants import (
    PET_FEED_LIMIT_EVENT,
    PET_FEED_LIMIT_NORMAL,
    PET_HABITAT_PRIORITY,
    PET_HABITAT_PRIORITY_200,
    PETS_PER_HABITAT,
)
from sfbot.pets.pet_reqs import (
    PET_REQUIREMENTS,
    PetRequirement,
)
from sfbot.session import GameSession


@dataclass(slots=True)
class Pet:
    pet_id: int
    element: HabitatType
    level: int
    fruits_today: int
    position: int  # 0-based position within habitat (0..19)
    unlocked: bool
    discovered: bool  # habitat explored past this position, pet is discoverable

    def format(self) -> str:
        if self.unlocked:
            status = f"lvl {self.level:>3}"
        elif self.discovered:
            status = "discovered"
        else:
            status = "locked"
        fed = f"fed {self.fruits_today}x" if self.unlocked else ""
        return f"#{self.pet_id:<3} pos {self.position:>2}  {status:<14} {fed}"


@dataclass(slots=True)
class Habitat:
    element: HabitatType
    explored_count: int
    next_fight_level: int
    battled_opponent_today: bool
    fruits: int
    pets: list[Pet]

    @property
    def is_explored(self) -> bool:
        """All 20 habitat fights won."""
        return self.explored_count == PETS_PER_HABITAT

    @property
    def is_completed(self) -> bool:
        """All 20 pets found (unlocked)."""
        return all(p.unlocked for p in self.pets)

    @property
    def unfound_pet_ids(self) -> set[int]:
        return {p.pet_id for p in self.pets if p.discovered and not p.unlocked}

    @property
    def can_explore(self) -> bool:
        return not self.is_explored

    def format(self) -> str:
        status = f"{self.explored_count}/{PETS_PER_HABITAT}"

        pvp = "fought" if self.battled_opponent_today else "available"
        unlocked = sum(1 for p in self.pets if p.unlocked)
        return (
            f"{self.element.name:<7} | explored: {status:<10} | "
            f"next fight lvl: {self.next_fight_level:<4} | "
            f"fruits: {self.fruits:<4} | pvp: {pvp:<9} | "
            f"unlocked: {unlocked}/{PETS_PER_HABITAT}"
        )


class Pets:
    """Pet system — habitats, feeding, PvP fights, and pet dungeons."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.habitats: dict[HabitatType, Habitat] = {}
        self.opponent_id: int = 0
        self.opponent_next_free_battle: int = 0
        self.next_free_exploration: int = 0
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data
        pet_raw = data.get("ownpets.petsSave", "").split(VALUES_DELIMITER)
        pet_vals = [int(x) for x in pet_raw if x]

        # Too low level for pets to be unlocked, Initialize empty state.
        if not pet_vals:
            self.habitats = {}
            self.max_pet_level = 0
            self.opponent_id = 0
            self.opponent_next_free_battle = 0
            self.next_free_exploration = 0
            return

        resource_raw = data.get("resources", "").split(VALUES_DELIMITER)
        resource_vals = [int(x) for x in resource_raw if x]

        self.max_pet_level: int = int(data.get("maxpetlevel", "100"))

        for element in HabitatType:
            e = element.value

            # Per-element fields from ownpets array
            explored_count = pet_vals[PET_EXPLORED_BASE + e]
            next_fight_level = pet_vals[PET_NEXT_FIGHT_LEVEL_BASE + e]
            battled = pet_vals[PET_BATTLED_OPPONENT_BASE + e] == 1

            # Fruit counts from resources array
            fruits = resource_vals[RESOURCE_FRUITS_BASE_INDEX + e]

            pets: list[Pet] = []
            for pos in range(PETS_PER_HABITAT):
                pet_id = e * PETS_PER_HABITAT + pos + 1  # 1-based global ID
                pet_level = pet_vals[PET_LEVEL_BASE + pet_id - 1]  # indices 2..101
                pet_fruits_today = pet_vals[PET_FRUITS_TODAY_BASE + pet_id - 1]
                pet_discovered = explored_count > pos
                pet_unlocked = pet_level > 0

                pets.append(
                    Pet(
                        pet_id=pet_id,
                        element=element,
                        level=pet_level,
                        fruits_today=pet_fruits_today,
                        position=pos,
                        unlocked=pet_unlocked,
                        discovered=pet_discovered,
                    )
                )

            self.habitats[element] = Habitat(
                element=element,
                explored_count=explored_count,
                next_fight_level=next_fight_level,
                battled_opponent_today=battled,
                fruits=fruits,
                pets=pets,
            )

        # PvP opponent data
        self.opponent_id = pet_vals[PET_OPPONENT_ID_INDEX]
        self.opponent_next_free_battle = pet_vals[PET_OPPONENT_NEXT_FREE_BATTLE_INDEX]

        # Habitat exploration cooldown from characterstatus[20]
        char_status_raw = data.get("characterstatus", "").split(VALUES_DELIMITER)
        char_status_vals = [int(x) for x in char_status_raw if x]
        if len(char_status_vals) > CHARACTER_STATUS_PET_EXPLORATION_TIMER_INDEX:
            self.next_free_exploration = char_status_vals[
                CHARACTER_STATUS_PET_EXPLORATION_TIMER_INDEX
            ]
        else:
            self.next_free_exploration = 0

    def refresh(self) -> None:
        self._parse()

    def get_pet(self, pet_id: int) -> Pet | None:
        """Look up a pet by its global 1-based ID (1..100)."""
        element = HabitatType((pet_id - 1) // PETS_PER_HABITAT)
        pet_index_in_habitat = (pet_id - 1) % PETS_PER_HABITAT
        return self.habitats[element].pets[pet_index_in_habitat]

    def get_feed_limit(self, events: frozenset[Event]) -> int:
        if Event.ASSEMBLY_OF_AWESOME_ANIMALS in events:
            return PET_FEED_LIMIT_EVENT
        return PET_FEED_LIMIT_NORMAL

    def get_unfought_pvp_elements(self) -> list[HabitatType]:
        return [
            habitat_type
            for habitat_type, hab in self.habitats.items()
            if not hab.battled_opponent_today
        ]

    def get_explorable_habitats(self) -> list[Habitat]:
        return [hab for hab in self.habitats.values() if hab.can_explore]

    def get_pet_to_feed(self, element: HabitatType) -> Pet | None:
        """Get the highest-priority pet to feed in a habitat.

        Phase 1: First unlocked pet below level 100 from HABITAT_PRIORITY.
        Phase 2: Once ALL phase-1 pets are at 100+, feed from HABITAT_PRIORITY_200
                 to level 200 (only if habitat fully explored).
        """
        habitat = self.habitats[element]
        habitat_feed_priorities = PET_HABITAT_PRIORITY[element.value]

        if not habitat.is_explored:
            # Phase 1: feed priority pets to level 100
            for index_priority in habitat_feed_priorities:
                pet = habitat.pets[index_priority]

                # Pet not yet obtained, wait for it to be unlocked
                if not pet.unlocked:
                    return None

                # First pet that hasn't hit level 100
                if pet.level < 100:
                    return pet

            # No pet to feed (all priority pets are at lvl 100+)
            return None
        else:
            # Phase 2: feed to level 200 (only if habitat fully explored)
            for idx in PET_HABITAT_PRIORITY_200:
                pet = habitat.pets[idx]
                # Pet not yet obtained, skip
                if not pet.unlocked:
                    continue
                # First pet that still needs feeding to 200
                if pet.level < 200:
                    return pet

            # No pet needs feeding, all are level 200 already
            return None

    def total_fruits(self) -> int:
        """Sum of all fruits across all habitats."""
        return sum(hab.fruits for hab in self.habitats.values())

    async def feed_pet_async(self, pet_id: int) -> None:
        """Feed a pet. fruit_idx = total fruit count across all habitats."""
        await self.session.request_and_update_async(
            "PlayerPetFeed", f"{pet_id}/{self.total_fruits()}"
        )

    async def fight_pvp_async(self, element: HabitatType) -> FightResult:
        """Fight PvP using your pet of the given element.

        You choose which of your 5 elements to send — element advantage applies.
        """
        # Wire: PetsPvPFight:0/{opponent_id}/{element+1}
        result = await self.session.request_and_update_async(
            "PetsPvPFight", f"0/{self.opponent_id}/{element.value + 1}"
        )
        fight = parse_fight_result(result)
        outcome = "won" if fight.won else "lost"
        get_main_logger().info(f"Pets: {outcome} PvP {element.name} +{fight.xp:,} XP")
        return fight

    async def fight_pet_dungeon_async(
        self, element: HabitatType, enemy_pos: int, player_pet_id: int
    ) -> FightResult:
        """Fight a habitat exploration enemy. enemy_pos is explored + 1."""
        # Wire: PetsDungeonFight:{use_mush}/{element+1}/{enemy_pos}/{player_pet_id}
        result = await self.session.request_and_update_async(
            "PetsDungeonFight",
            f"0/{element.value + 1}/{enemy_pos}/{player_pet_id}",
        )
        fight = parse_fight_result(result)
        outcome = "won" if fight.won else "lost"
        get_main_logger().info(
            f"Pets: {outcome} {element.name} dungeon #{enemy_pos} +{fight.xp:,} XP"
        )
        return fight

    def can_fight_pet_dungeon_now(self) -> bool:
        """True if the pet dungeon exploration cooldown has expired."""
        return self.next_free_exploration <= self.session.server_time()

    def can_fight_pvp_now(self) -> bool:
        """True if the 15min PvP pet fight cooldown has expired."""
        return self.opponent_next_free_battle <= self.session.server_time()

    def get_todays_pet_requirements(
        self, events: frozenset[Event], server_time: int
    ) -> list[PetRequirement]:
        unfound_pet_ids: set[int] = set()
        for habitat in self.habitats.values():
            unfound_pet_ids |= habitat.unfound_pet_ids

        if not unfound_pet_ids:
            return []

        active_requirements: list[PetRequirement] = []
        for requirement in PET_REQUIREMENTS:
            if requirement.pet_id not in unfound_pet_ids:
                continue
            if requirement.check(events, server_time):
                active_requirements.append(requirement)

        active_requirements.sort(key=lambda r: r.days_per_year)
        return active_requirements

    def show(self, events: frozenset[Event] = frozenset()) -> None:
        feed_limit = self.get_feed_limit(events)
        print("\n=== Pets ===")
        print(f"  Max pet level: {self.max_pet_level}")
        print(f"  Feed limit: {feed_limit}/day")
        print(f"  Opponent ID: {self.opponent_id}")
        print(f"  Can fight PvP: {self.can_fight_pvp_now()}")
        print(f"  Can explore habitat: {self.can_fight_pet_dungeon_now()}")

        for habitat in self.habitats.values():
            print(f"\n  --- {habitat.format()} ---")
            for pet in habitat.pets:
                print(f"    {pet.format()}")
