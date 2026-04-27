from dataclasses import dataclass

from sfbot.constants import Event


@dataclass(slots=True, frozen=True)
class PlayerState:
    events: frozenset[Event]
    silver_total: int
    mushrooms: int
    lucky_coins: int
    hourglasses: int

    def has_event(self, event: Event) -> bool:
        return event in self.events
