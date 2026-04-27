from sfbot.constants import (
    CHARACTER_STATUS_BEER_DRUNK_INDEX,
    CHARACTER_STATUS_BEER_MAX_INDEX,
    CHARACTER_STATUS_THIRST_INDEX,
    VALUES_DELIMITER,
    Event,
)
from sfbot.session import GameSession
from sfbot.state import PlayerState
from sfbot.tavern.quests import Quests

PLAY_FOR_EVENTS = True
EVENTS_TO_BUY_BEER = {
    Event.EXCEPTIONAL_XP,
    Event.GLORIOUS_GOLD_GALORE,
    Event.ONE_BEER_TWO_BEER_FREE_BEER,
}


class Tavern:
    """Tavern — beer buying and quest management."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.quests = Quests(session)
        self._parse()

    def _parse(self) -> None:
        status_raw = self.session.login_data["characterstatus"].split(VALUES_DELIMITER)
        values = [int(x) for x in status_raw if x]
        self.beer_max: int = values[CHARACTER_STATUS_BEER_MAX_INDEX]
        self.thirst_seconds: int = values[CHARACTER_STATUS_THIRST_INDEX]
        self.beer_drunk: int = values[CHARACTER_STATUS_BEER_DRUNK_INDEX]

    def refresh(self) -> None:
        self._parse()
        self.quests.refresh()

    async def buy_beer_async(self) -> dict[str, str]:
        """Async buy a beer to refill thirst for adventure."""
        result = await self.session.request_and_update_async("PlayerBeerBuy")
        self.refresh()
        return result

    def status(self) -> None:
        print("\n=== Tavern ===")
        print(f"\n  Beer: {self.beer_drunk}/{self.beer_max}")
        print(f"  Thirst: {self.thirst_seconds // 60}/100 min")
        print("\n[Quests]")
        self.quests.status()

    @property
    def has_free_beer(self) -> bool:
        return self.beer_drunk == 0 and self.beer_max == 11

    def should_buy_beer(self, state: PlayerState) -> bool:
        self.refresh()

        if self.thirst_seconds >= 20 * 60:  # Do not buy beer unless its needed
            return False
        if self.has_free_beer:
            return True
        if PLAY_FOR_EVENTS and any(
            state.has_event(event)
            for event in EVENTS_TO_BUY_BEER  # Currently event we are interested in
        ):
            return self.beer_drunk < self.beer_max and state.mushrooms > 0
        return False

    def is_completed(self, state: PlayerState) -> bool:
        return not (self.should_buy_beer(state) or self.thirst_seconds > 0)
