from sfbot.arena_manager.constants import (
    MERCHANT_MONEY_TOILET,
    MERCHANT_SPEED_TOILET,
    IdleBuildingType,
)
from sfbot.arena_manager.models import MerchantOffer
from sfbot.arena_manager.tests.conftest import _build_idle_data, make_arena_manager


class TestMerchantOfferModel:
    def test_speed_boost(self) -> None:
        offer = MerchantOffer(index=1, offer_type=4, cost=100)
        assert offer.is_speed_boost
        assert not offer.is_money_boost
        assert offer.building_type == IdleBuildingType.TRAP

    def test_money_boost(self) -> None:
        offer = MerchantOffer(index=2, offer_type=15, cost=150)
        assert not offer.is_speed_boost
        assert offer.is_money_boost
        assert offer.building_type == IdleBuildingType.DRINKS

    def test_skip_time(self) -> None:
        offer = MerchantOffer(index=3, offer_type=22, cost=20)
        assert not offer.is_speed_boost
        assert not offer.is_money_boost
        assert offer.building_type is None


class TestGetToiletOffers:
    def test_filters_toilet_speed_and_money(self) -> None:
        data = _build_idle_data(
            offer_types=[MERCHANT_SPEED_TOILET, MERCHANT_MONEY_TOILET, 22],
            offer_costs=[100, 100, 20],
        )
        am = make_arena_manager(idle_data=data)
        offers = am.get_toilet_offers()
        assert len(offers) == 2
        assert offers[0].offer_type == MERCHANT_SPEED_TOILET
        assert offers[1].offer_type == MERCHANT_MONEY_TOILET

    def test_no_toilet_offers(self) -> None:
        data = _build_idle_data(
            offer_types=[4, 15, 22],
            offer_costs=[100, 150, 20],
        )
        am = make_arena_manager(idle_data=data)
        offers = am.get_toilet_offers()
        assert len(offers) == 0

    def test_empty_offers(self) -> None:
        data = _build_idle_data()
        am = make_arena_manager(idle_data=data)
        assert not am.has_merchant_offers
        assert am.get_toilet_offers() == []

    def test_excludes_skip_time_offers(self) -> None:
        """Skip time offers (types 21-23) should never appear in toilet offers."""
        data = _build_idle_data(
            offer_types=[21, 22, 23],
            offer_costs=[15, 20, 25],
        )
        am = make_arena_manager(idle_data=data)
        assert am.has_merchant_offers
        assert am.get_toilet_offers() == []
