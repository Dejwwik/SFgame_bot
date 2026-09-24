from sfbot.session import GameSession
from sfbot.utils import from_sf_string

# messagelist.r: entries separated by ";", fields by "," — id,sender,read,subject,sent_ts
MESSAGE_ENTRY_DELIMITER = ";"
MESSAGE_FIELD_DELIMITER = ","
MESSAGE_ID_INDEX = 0

COUPON_MIN_LENGTH = 2
COUPON_MAX_LENGTH = 30


class Inbox:
    def __init__(self, session: GameSession) -> None:
        self.session = session

    @property
    def message_ids(self) -> list[str]:
        raw = self.session.login_data.get("messagelist.r", "")
        ids: list[str] = []
        for entry in raw.split(MESSAGE_ENTRY_DELIMITER):
            if not entry:
                continue
            ids.append(entry.split(MESSAGE_FIELD_DELIMITER)[MESSAGE_ID_INDEX])
        return ids

    async def read_async(self, msg_id: str) -> str:
        result = await self.session.request_and_update_async(
            "PlayerMessageView", msg_id
        )
        return from_sf_string(result.get("messagetext.s", ""))

    async def delete_async(self, msg_id: str) -> None:
        await self.session.request_and_update_async("PlayerMessageDelete", msg_id)


def extract_coupon_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for word in text.split():
        if (
            COUPON_MIN_LENGTH < len(word) < COUPON_MAX_LENGTH
            and word not in candidates
        ):
            candidates.append(word)
    return candidates
