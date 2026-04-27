from sfbot.constants import VALUES_DELIMITER
from sfbot.session import GameSession

CALENDAR_NEXT_POSSIBLE_INDEX = 9


# Calendar daily login reward (Goblin Gleeman — "Login bonus" tab)
class CalendarReward:
    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()

    def _parse(self) -> None:
        data = self.session.login_data
        status = data["characterstatus"].split(VALUES_DELIMITER)
        values = [int(x) for x in status if x]
        self.next_possible: int = values[CALENDAR_NEXT_POSSIBLE_INDEX]

    def refresh(self) -> None:
        self._parse()

    @property
    def is_completed(self) -> bool:
        return self.next_possible > self.session.server_time()

    async def claim_async(self) -> None:
        await self.session.request_and_update_async("PlayerOpenCalender", "")
