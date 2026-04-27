from dataclasses import dataclass
from enum import IntEnum

from sfbot.constants import ITEM_FIELD_COUNT, VALUES_DELIMITER, Event, Location
from sfbot.items import Item, format_item, parse_item
from sfbot.logging import get_main_logger
from sfbot.session import GameSession
from sfbot.state import PlayerState

# --- adventure field indices (per quest, 7 fields each, starting at offset 2) ---
ADVENTURE_GLOBAL_HEADER_SIZE = 2  # first 2 values are global (time_left, max_time)
ADVENTURE_FIELDS_PER_QUEST = 7
ADVENTURE_MONSTER_ID_OFFSET = 2  # negated
ADVENTURE_LOCATION_ID_OFFSET = 3
ADVENTURE_DURATION_SECONDS_OFFSET = 4
ADVENTURE_BASE_XP_OFFSET = 5
ADVENTURE_BASE_SILVER_OFFSET = 6

ADVENTURE_QUEST_COUNT = 3


class SkipQuestPayment(IntEnum):
    MUSHROOMS = 1
    HOURGLASS = 2


class QuestPreference(IntEnum):
    GOLD = 1
    XP = 2
    TIME = 3
    ITEM = 4


EVENT_QUEST_PREFERENCE: dict[Event, QuestPreference] = {
    Event.EXCEPTIONAL_XP: QuestPreference.XP,
    Event.GLORIOUS_GOLD_GALORE: QuestPreference.GOLD,
    # Shorter quests better
    Event.PIECEWORK_PARTY: QuestPreference.TIME,
    Event.CRAZY_MUSHROOM_HARVEST: QuestPreference.TIME,
    # Items
    Event.EPIC_QUEST_EXTRAVAGANZA: QuestPreference.ITEM,
    Event.EPIC_GOOD_LUCK: QuestPreference.ITEM,
    Event.LUCKY_DAY: QuestPreference.ITEM,
}


@dataclass(slots=True)
class Quest:
    """A single tavern quest offer."""

    index: int
    monster_id: int
    location: Location

    base_length: int
    base_xp: int
    base_silver: int
    item: Item | None

    @property
    def silver_per_minute(self) -> float:
        return (
            self.base_silver + (self.item.cost.silver if self.item else 0)
        ) / self.base_length

    @property
    def xp_per_minute(self) -> float:
        return self.base_xp / self.base_length


class Quests:
    """Tavern quest system - accept and complete quests."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data

        adventure_raw_data = list(map(int, data["adventure"].split(VALUES_DELIMITER)))

        items_raw = data["questofferitems"].split(VALUES_DELIMITER)
        items_values = [int(x) for x in items_raw if x]

        self.quests: list[Quest] = []
        for i in range(ADVENTURE_QUEST_COUNT):
            off = ADVENTURE_GLOBAL_HEADER_SIZE + i * ADVENTURE_FIELDS_PER_QUEST

            location = Location(adventure_raw_data[off + ADVENTURE_LOCATION_ID_OFFSET])

            item_offset = i * ITEM_FIELD_COUNT
            item = parse_item(
                items_values[item_offset : item_offset + ITEM_FIELD_COUNT]
            )

            self.quests.append(
                Quest(
                    index=i,
                    monster_id=-adventure_raw_data[off + ADVENTURE_MONSTER_ID_OFFSET],
                    location=location,
                    base_length=adventure_raw_data[
                        off + ADVENTURE_DURATION_SECONDS_OFFSET
                    ],
                    base_xp=adventure_raw_data[off + ADVENTURE_BASE_XP_OFFSET],
                    base_silver=adventure_raw_data[off + ADVENTURE_BASE_SILVER_OFFSET],
                    item=item,
                )
            )

    def refresh(self) -> None:
        self._parse()

    def status(self) -> None:
        for q in self.quests:
            mins, secs = divmod(q.base_length, 60)
            item_str = f" | Item: {format_item(q.item)}" if q.item else ""
            print(
                f"  Quest {q.index + 1}: {q.location.name}, "
                f"XP {q.base_xp:,}, Silver {q.base_silver:,}, "
                f"Time {mins}:{secs:02d}{item_str}"
            )

    async def start_quest_async(
        self, quest_index: int, *, overwrite_inventory: bool = True
    ) -> dict[str, str]:
        result = await self.session.request_and_update_async(
            "PlayerAdventureStart",
            f"{quest_index}/{int(overwrite_inventory)}",
        )
        self.refresh()
        return result

    def get_best_quest(
        self,
        state: PlayerState,
        *,
        quest_preference: QuestPreference = QuestPreference.GOLD,
    ) -> Quest:
        """Get the best quest offer based on reward."""
        if not self.quests:
            raise ValueError("No quests available")

        # If there is event, override preference based on event
        event_for_preference: Event | None = None
        for event, preference in EVENT_QUEST_PREFERENCE.items():
            if state.has_event(event):
                quest_preference = preference
                event_for_preference = event
                break

        key_funcs = {
            QuestPreference.GOLD: lambda q: q.silver_per_minute,
            QuestPreference.XP: lambda q: q.xp_per_minute,
            QuestPreference.TIME: lambda q: -q.base_length,
            # Tuple comparison: (has_item=True > False, then Item.__gt__ to pick best)
            QuestPreference.ITEM: lambda q: (q.item is not None, q.item),
        }

        # If prefer item, but no quests have items, fallback to time preference
        if quest_preference == QuestPreference.ITEM:
            has_item = [q for q in self.quests if q.item is not None]
            if not has_item:
                quest_preference = QuestPreference.TIME

        logger = get_main_logger()
        logger.info(
            f"Quest: selecting preference {quest_preference.name} for event {event_for_preference.name if event_for_preference is not None else 'None'}"
        )
        return max(self.quests, key=key_funcs[quest_preference])

    async def collect_quest_async(self) -> dict[str, str]:
        """Async collect a finished quest reward."""
        result = await self.session.request_and_update_async(
            "PlayerAdventureFinished", "0"
        )
        self.refresh()

        return result
