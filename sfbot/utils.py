from sfbot.constants import SMITH_UPGRADE_MULTIPLIER


def strip_upgrades(value: int, upgrade_count: int) -> int:
    """Reverse smith upgrades from an attribute value.

    Each upgrade multiplied the value by SMITH_UPGRADE_MULTIPLIER with
    rounding, so we reverse by dividing iteratively with rounding each step.
    """
    v = float(value)
    for _ in range(upgrade_count):
        v = round(v / SMITH_UPGRADE_MULTIPLIER)
    return int(v)


def format_silver(silver_raw: int) -> str:
    gold = silver_raw // 100
    silver = silver_raw % 100
    if silver == 0:
        return f"{gold:,} gold"
    return f"{gold:,} gold {silver} silver"


_SUFFIXES: list[tuple[int, str]] = [
    (10**99, "duotrigintillion"),
    (10**96, "untrigintillion"),
    (10**93, "trigintillion"),
    (10**90, "novemvigintillion"),
    (10**87, "octovigintillion"),
    (10**84, "septenvigintillion"),
    (10**81, "sexvigintillion"),
    (10**78, "quinvigintillion"),
    (10**75, "quattuorvigintillion"),
    (10**72, "trevigintillion"),
    (10**69, "duovigintillion"),
    (10**66, "unvigintillion"),
    (10**63, "vigintillion"),
    (10**60, "novemdecillion"),
    (10**57, "octodecillion"),
    (10**54, "septendecillion"),
    (10**51, "sexdecillion"),
    (10**48, "quindecillion"),
    (10**45, "quattuordecillion"),
    (10**42, "tredecillion"),
    (10**39, "duodecillion"),
    (10**36, "undecillion"),
    (10**33, "decillion"),
    (10**30, "nonillion"),
    (10**27, "octillion"),
    (10**24, "septillion"),
    (10**21, "sextillion"),
    (10**18, "quintillion"),
    (10**15, "quadrillion"),
    (10**12, "trillion"),
    (10**9, "billion"),
    (10**6, "million"),
]


def format_large_number(n: int) -> str:
    for threshold, suffix in _SUFFIXES:
        if n >= threshold:
            value = n / threshold
            return f"{value:,.2f} {suffix}"
    return f"{n:,}"
