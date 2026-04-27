from sfbot.session import GameSession


class Guard:
    """City Guard - earn gold by guarding the city."""

    def __init__(self, session: GameSession) -> None:
        self.session = session

    @property
    def wage_per_hour(self) -> int:
        return int(self.session.login_data.get("wagesperhour", "0"))

    async def start_async(self, hours: int = 10) -> None:
        """Async start city guard duty for given hours."""
        await self.session.request_and_update_async("PlayerWorkStart", str(hours))

    async def collect_async(self) -> None:
        """Async collect guard duty pay after shift ends."""
        await self.session.request_and_update_async("PlayerWorkFinished")
