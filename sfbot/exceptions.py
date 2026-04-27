"""Exception hierarchy for the sfbot package."""


class SFGameError(Exception):
    """Base exception for all SFGame errors."""


class LoginError(SFGameError):
    """SSO or game login failed."""


class APIError(SFGameError):
    """Game API returned an error response."""


class KnownAPIError(APIError):
    """API error with a known cause — logged without stack trace."""


class RateLimitError(KnownAPIError):
    """Server returned 'too many requests'."""


class MoveError(APIError):
    """Item move/swap failed."""


class GemExtractedAlert(Exception):
    """Raised when a gem was extracted from equipment to free a slot.

    The caller should socket the extracted gem back into equipment.
    """


class InventoryFullError(SFGameError):
    """Raised when an item must be collected but inventory is full."""


class InventoryStuckError(SFGameError):
    """Raised when the free-slot chain exhausted all strategies.

    Requires manual intervention (e.g. user clears inventory).
    """
