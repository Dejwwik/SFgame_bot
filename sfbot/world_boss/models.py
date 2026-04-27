from dataclasses import dataclass, field

from sfbot.world_boss.constants import (
    UPGRADE_SLOT_COUNT,
    PriceType,
    ProjectileType,
    TowerSegment,
    UpgradeType,
)


@dataclass(slots=True)
class CatapultUpgrade:
    typ: UpgradeType
    restriction: TowerSegment  # NONE = works on all segments
    amount: int  # 0-10
    effect: int


@dataclass(slots=True)
class Catapult:
    breaks: int  # timestamp when catapult breaks
    upgrades: list[CatapultUpgrade | None] = field(
        default_factory=lambda: [None] * UPGRADE_SLOT_COUNT
    )


@dataclass(slots=True)
class Projectile:
    typ: ProjectileType
    amount: int
    extra_dmg: int


@dataclass(slots=True)
class UpgradeOffer:
    slot: int
    typ: UpgradeType
    restriction: TowerSegment
    effect: int
    main_price: int  # raw price (scales with remaining catapult time)
    price_type: PriceType
    catalyst_price: int
    mushroom_price: int


@dataclass(slots=True)
class ProjectileOffer:
    slot: int
    typ: ProjectileType
    small_amount: int
    large_amount: int
    effect: int
    small_price: int  # catalyst price for small purchase
    large_price: int  # catalyst price for large purchase
