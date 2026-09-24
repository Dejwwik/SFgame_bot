from typing import Any

import aiohttp

from sfbot.constants import VALUES_DELIMITER
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.session import COMMON_HEADERS, SERVER_MAP_CACHE, GameSession

COUPON_URL = "https://coupon.playa-games.com/redeem"
PAYMENT_STRING_SUFFIX = "1"

# Coupon redemption goes to a separate Playa endpoint, not cmd.php.
# Body: coupon=<code>&paymentstring=<player_id>_<save_id>_<server_id>_1&lang=en
# Response: JSON {"status": "error", "message": "code invalid"} (HTTP 400) on failure.
# Rewards arrive in the mailbox and are claimed by the mail_reward task.


class Coupon:
    def __init__(self, session: GameSession) -> None:
        self.session = session

    @property
    def payment_string(self) -> str:
        save = self.session.login_data["ownplayersavecharacter"].split(VALUES_DELIMITER)
        server_id = SERVER_MAP_CACHE.get(self.session.server)
        if server_id is None:
            raise APIError(f"Unknown server id for {self.session.server}")
        return f"{save[1]}_{save[0]}_{server_id}_{PAYMENT_STRING_SUFFIX}"

    async def redeem_async(self, code: str) -> bool:
        logger = get_main_logger()
        try:
            async with self.session._client.post(
                COUPON_URL,
                data={
                    "coupon": code,
                    "paymentstring": self.payment_string,
                    "lang": "en",
                },
                headers=COMMON_HEADERS,
            ) as resp:
                data: dict[str, Any] = await resp.json(content_type=None)
        except (aiohttp.ClientError, ValueError) as exc:
            raise APIError(f"Coupon request failed: {exc}") from exc
        if resp.status != 200 or data.get("status") == "error":
            logger.debug(f"Coupon: {code} rejected ({data.get('message', resp.status)})")
            return False
        logger.info(f"Coupon: redeemed {code} ({data})")
        return True
