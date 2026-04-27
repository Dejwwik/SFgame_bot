from dataclasses import dataclass

from sfbot.constants import GemAttr


@dataclass(slots=True)
class Gem:
    """A gem found in the backpack."""

    slot: int
    wire: str
    attr: GemAttr
    power: int
