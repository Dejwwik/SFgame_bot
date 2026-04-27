from sfbot.constants import VALUES_DELIMITER
from sfbot.logging import get_main_logger
from sfbot.reward.models import MessageStatus
from sfbot.session import GameSession

# pendingrewards.r chunk layout (6 fields per entry)
PENDING_CHUNK_SIZE = 6
PENDING_MSG_ID_INDEX = 0
PENDING_STATUS_INDEX = 1

# Pending rewards in the mailbox (messages tab)
# Rewards land here after daily/event chest claims, twitch drops, coupons, etc.
# pendingrewards.r format: chunks of 6 — msg_id/status/type/name/received/claimable_until


class MailReward:
    def __init__(self, session: GameSession) -> None:
        self.session = session

    @property
    def claimable_ids(self) -> list[str]:
        raw = self.session.login_data.get("pendingrewards.r", "")
        if not raw:
            return []
        parts = raw.split(VALUES_DELIMITER)
        ids: list[str] = []
        # Walk chunks of 6: [msg_id, status, type, name, received, claimable_until]
        for chunk_start in range(
            0, len(parts) - PENDING_CHUNK_SIZE + 1, PENDING_CHUNK_SIZE
        ):
            status = parts[chunk_start + PENDING_STATUS_INDEX]
            if status != MessageStatus.CLAIMED:
                ids.append(parts[chunk_start + PENDING_MSG_ID_INDEX])
        return ids

    @property
    def has_claimable(self) -> bool:
        return bool(self.claimable_ids)

    async def claim_all_async(self) -> None:
        logger = get_main_logger()
        for msg_id in self.claimable_ids:
            await self.session.request_and_update_async("PendingRewardClaim", msg_id)
            logger.info(f"Mail: claimed reward {msg_id}")
