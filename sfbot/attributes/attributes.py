from collections import defaultdict

from sfbot.constants import RESOURCE_SILVER_RAW_INDEX, VALUES_DELIMITER, Attribute
from sfbot.logging import get_main_logger
from sfbot.session import GameSession


class Attributes:
    """Upgrade character attributes based on weighted target ratios."""

    def __init__(self, session: GameSession) -> None:
        self.session = session

    def _current_silver(self) -> int:
        resource_raw = self.session.login_data["resources"]
        parts = resource_raw.split(VALUES_DELIMITER)
        return int(parts[RESOURCE_SILVER_RAW_INDEX])

    def find_most_deficient(
        self,
        base_attrs: dict[Attribute, int],
        weights: dict[Attribute, float],
    ) -> Attribute:
        """Return the attribute with the largest deficit vs. the target ratio."""
        total_base_points = sum(base_attrs[attr] for attr in weights)

        if total_base_points == 0:
            return max(weights, key=lambda a: weights[a])

        largest_deficit = -float("inf")
        most_deficient = Attribute.STRENGTH
        for attr, target_ratio in weights.items():
            current_ratio = base_attrs[attr] / total_base_points
            deficit = target_ratio - current_ratio
            if deficit > largest_deficit:
                largest_deficit = deficit
                most_deficient = attr
        return most_deficient

    async def upgrade_async(
        self,
        attr: Attribute,
        current_base: int,
    ) -> None:
        """Upgrade a single attribute by +1."""
        new_value = current_base + 1
        await self.session.request_and_update_async(
            "PlayerAttributIncrease", f"{attr.server_value}/{new_value}"
        )

    async def upgrade_loop_async(
        self,
        base_attrs: dict[Attribute, int],
        weights: dict[Attribute, float],
        reserve_silver: int,
    ) -> dict[Attribute, int]:
        """Upgrade attributes in a loop until server rejects or silver drops below reserve.

        Returns a dict mapping each upgraded attribute to the number of points
        added.
        """
        logger = get_main_logger()
        upgraded: defaultdict[Attribute, int] = defaultdict(int)

        # Make copy of the base attributes to keep track of upgrades in the loop without modifying the original dict.
        working_attrs = dict(base_attrs)

        while True:
            if not self._current_silver() > reserve_silver:
                logger.info(
                    f"Attributes: stopping upgrades to maintain silver reserve of {reserve_silver}"
                )
                break

            attr = self.find_most_deficient(working_attrs, weights)
            await self.upgrade_async(attr, working_attrs[attr])

            working_attrs[attr] += 1
            upgraded[attr] += 1

        if upgraded:
            parts_str = ", ".join(f"{a.name} +{n}" for a, n in upgraded.items())
            logger.info(f"Attributes: upgraded {parts_str}")

        return upgraded
