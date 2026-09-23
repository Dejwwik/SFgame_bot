"""Tests for scrapbook constants."""

from sfbot.scrapbook.constants import (
    ITEM_POSITIONS,
    MONSTER_COUNT,
    MONSTER_POSITIONS,
    QUEUE_REFRESH_INTERVAL,
    SCRAPBOOK_COUNT,
)
from sfbot.scrapbook.scrapbook import VALID_ITEM_POSITIONS


class TestQueueRefreshInterval:
    def test_value(self) -> None:
        assert QUEUE_REFRESH_INTERVAL == 1800


class TestConstants:
    def test_item_positions(self) -> None:
        assert ITEM_POSITIONS == len(VALID_ITEM_POSITIONS) == 1748

    def test_monster_count(self) -> None:
        assert MONSTER_COUNT == SCRAPBOOK_COUNT - ITEM_POSITIONS == 736

    def test_scrapbook_count(self) -> None:
        assert SCRAPBOOK_COUNT == 2484

    def test_monster_positions(self) -> None:
        assert MONSTER_POSITIONS == 800
