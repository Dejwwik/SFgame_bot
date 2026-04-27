from sfbot.constants import (
    CHARACTER_MOUNT_END_INDEX,
    CHARACTER_MOUNT_INDEX,
    VALUES_DELIMITER,
    Cost,
    Mount,
)
from sfbot.session import GameSession

MOUNT_COSTS: dict[Mount, Cost] = {
    Mount.COW: Cost(silver=100_00),
    Mount.HORSE: Cost(silver=500_00),
    Mount.TIGER: Cost(silver=1000_00, mushrooms=1),
    Mount.DRAGON: Cost(mushrooms=25),
}

# Ordered list from best to worst for downgrade logic
MOUNT_PRIORITY = [Mount.DRAGON, Mount.TIGER, Mount.HORSE, Mount.COW]


class Mounts:
    """Mount management - check, buy, and ensure desired mount is active."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self._parse()

    def _parse(self) -> None:
        ch = self.session.login_data["ownplayersavecharacter"].split(VALUES_DELIMITER)
        values = [int(x) for x in ch if x]
        self.current_mount: Mount = Mount(values[CHARACTER_MOUNT_INDEX] & 0xFF)
        self.mount_end: int = (
            values[CHARACTER_MOUNT_END_INDEX]
            if len(values) > CHARACTER_MOUNT_END_INDEX
            else 0
        )

    def refresh(self) -> None:
        self._parse()

    @property
    def is_mount_active(self) -> bool:
        return self.current_mount != Mount.NONE

    @property
    def is_completed(self) -> bool:
        return self.is_mount_active

    def can_afford(self, mount: Mount, silver_total: int, mushrooms: int) -> bool:
        """Check if the player can afford a specific mount."""
        cost = MOUNT_COSTS[mount]
        return silver_total >= cost.silver and mushrooms >= cost.mushrooms

    async def buy_mount_async(self, mount: Mount) -> None:
        """Async buy a mount by type."""
        await self.session.request_and_update_async("PlayerMountBuy", str(mount.value))

    async def ensure_mount_async(
        self, desired: Mount, *, silver_total: int, mushrooms: int
    ) -> None:
        """Async ensure the desired mount (or best affordable) is active."""
        if self.is_mount_active and self.current_mount == desired:
            return

        start_idx = MOUNT_PRIORITY.index(desired)
        for mount in MOUNT_PRIORITY[start_idx:]:
            if self.can_afford(mount, silver_total, mushrooms):
                await self.buy_mount_async(mount)
                break

        return

    def status(self) -> None:
        mount = self.current_mount
        if mount == Mount.NONE:
            print("  Mount: None")
            return
        end = self.mount_end
        now = self.session.server_time()
        if end > now:
            remaining = end - now
            hours, rem = divmod(remaining, 3600)
            mins, _ = divmod(rem, 60)
            print(f"  Mount: {mount.name} ({hours}h {mins}m remaining)")
        else:
            print(f"  Mount: {mount.name} (expired)")
