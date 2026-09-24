from sfbot.reward.inbox import extract_coupon_candidates
from sfbot.utils import from_sf_string


def test_from_sf_string_decodes_escapes() -> None:
    assert from_sf_string("a$bb$cc$Cd$sf$d") == "a\nb:c,d/f$"


def test_candidates_are_words_without_short_ones() -> None:
    text: str = from_sf_string("Ist nur bis 19.30 Uhr einlösbar$b$bLG")
    assert extract_coupon_candidates(text) == [
        "Ist",
        "nur",
        "bis",
        "19.30",
        "Uhr",
        "einlösbar",
    ]


def test_candidates_strip_and_dedupe() -> None:
    text: str = from_sf_string("Hallo$b  SFCODE123  $bLG$bCode: SFCODE123")
    assert extract_coupon_candidates(text) == [
        "Hallo",
        "SFCODE123",
        "Code:",
    ]
