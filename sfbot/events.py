"""Game events - mushroom, gold, XP, and other server-side bonus events."""

from sfbot.constants import Event
from sfbot.session import GameSession


class Events:
    """Active server-side game events (parsed from tavernspecialsub bitmask)."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data
        flags = int(data.get("tavernspecialsub", "0"))
        self.active: set[Event] = {
            event for event in Event if (flags & (1 << event.value)) > 0
        }
        self.ends: int = int(data.get("tavernspecialend", "0"))

    def refresh(self) -> None:
        self._parse()

    def is_active(self, event: Event) -> bool:
        return event in self.active

    @property
    def xp_event(self) -> bool:
        return Event.EXCEPTIONAL_XP in self.active

    @property
    def gold_event(self) -> bool:
        return Event.GLORIOUS_GOLD_GALORE in self.active

    @property
    def mushroom_event(self) -> bool:
        return Event.CRAZY_MUSHROOM_HARVEST in self.active

    @property
    def epic_quest_event(self) -> bool:
        return Event.EPIC_QUEST_EXTRAVAGANZA in self.active

    @property
    def epic_luck_event(self) -> bool:
        return Event.EPIC_GOOD_LUCK in self.active

    @property
    def epic_shop_event(self) -> bool:
        return Event.EPIC_SHOPPING_SPREE in self.active

    @property
    def toilet_event(self) -> bool:
        return Event.TIDY_TOILET_TIME in self.active

    @property
    def fortress_event(self) -> bool:
        return Event.FANTASTIC_FORTRESS_FESTIVITY in self.active

    @property
    def forge_event(self) -> bool:
        return Event.FORGE_FRENZY_FESTIVAL in self.active

    @property
    def beer_event(self) -> bool:
        return Event.ONE_BEER_TWO_BEER_FREE_BEER in self.active

    def status(self) -> None:
        if not self.active:
            print("  No active events")
            return
        for event in sorted(self.active, key=lambda e: e.value):
            print(f"  - {event.name}")
