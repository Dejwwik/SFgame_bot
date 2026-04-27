"""Scrapbook decoding and equipment → scrapbook position mapping."""

import base64
from dataclasses import dataclass

from sfbot.constants import VALUES_DELIMITER
from sfbot.constants.parsing import (
    ITEM_FIELD_ATTR_TYPE_0,
    ITEM_FIELD_ATTR_VALUE_0,
    ITEM_FIELD_COUNT,
    ITEM_FIELD_MAX_DAMAGE,
    ITEM_FIELD_MIN_DAMAGE,
    ITEM_FIELD_MODEL,
    ITEM_FIELD_TYPE,
    MODEL_CLASS_DIVISOR,
)
from sfbot.logging import get_main_logger
from sfbot.scrapbook.constants import (
    MAX_MODEL_ID,
    MAX_QUEUE_SIZE,
    MONSTER_POSITIONS,
    SCRAPBOOK_BOUNDARIES,
)
from sfbot.scrapbook.crawl_persistence import load_players
from sfbot.session import GameSession

# Normal model counts per item type.
# Warrior weapons (type 1, class 1) have 30 models; all other
# weapon/armor slots have 10.  Accessories are special.
NORMAL_MODELS: dict[int, int] = {8: 21, 9: 16, 10: 37}  # amulet, ring, talisman
WARRIOR_WEAPON_MODELS = 30
DEFAULT_MODELS = 10

# Epic model counts: weapons/shields/accessories have 21 continuous,
# armor types (3-7) have 19 with a gap at offsets +10/+11 (models 59-60).
EPIC_CONTINUOUS = 21
EPIC_ARMOR_GAP = {9, 10}  # 0-based offsets to skip


def build_valid_positions() -> frozenset[int]:
    """Build set of all valid scrapbook item positions (1704 total).

    Uses exact model counts from the game client: normal models vary by type,
    epic items are 21 (continuous) for weapons/shields/accessories or 19
    (with gap at models 59-60) for armor slots.
    """
    positions: set[int] = set()

    for color_class, boundary_map in enumerate(SCRAPBOOK_BOUNDARIES):
        for type_key, boundary in boundary_map.items():
            normal_start = boundary[0]
            epic_start = boundary[1]
            item_type = type_key + 1

            # --- Normal models ---
            if item_type == 1 and color_class == 1:
                normal_models = WARRIOR_WEAPON_MODELS
            else:
                normal_models = NORMAL_MODELS.get(item_type, DEFAULT_MODELS)

            if item_type == 10:  # talisman — no color variant
                for m in range(normal_models):
                    positions.add(normal_start + m + 1)
            else:
                for m in range(normal_models):
                    for c in range(5):
                        positions.add(normal_start + m * 5 + c + 1)

            # --- Epic models ---
            if item_type in (1, 2, 8, 9, 10):  # weapon/shield/accessories
                for m in range(EPIC_CONTINUOUS):
                    positions.add(epic_start + m + 1)
            else:  # armor types 3-7: skip gap at offsets 9,10
                for m in range(EPIC_CONTINUOUS):
                    if m in EPIC_ARMOR_GAP:
                        continue
                    positions.add(epic_start + m + 1)

    return frozenset(positions)


VALID_ITEM_POSITIONS = build_valid_positions()

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class EquipmentIdent:
    item_type: int  # 1-10 (Weapon..Talisman)
    color_class: int  # 0=classless, 1=Warrior, 2=Mage, 3=Scout
    model_id: int  # picIndex % 1000
    color: int  # 0-4 (sf-tools style, 0-indexed)


@dataclass(slots=True)
class HofPlayer:
    rank: int
    name: str
    level: int


@dataclass(slots=True)
class CrawlTarget:
    name: str
    missing: int
    level: int


# ---------------------------------------------------------------------------
# Pure parsing functions
# ---------------------------------------------------------------------------


def decode_scrapbook(raw_b64: str) -> set[int]:
    """Decode a URL-safe base64 scrapbook string into 1-indexed bit positions.

    Positions 1..800 = monsters, 801+ = items.
    """
    b64 = raw_b64.replace("-", "+").replace("_", "/")
    padding = 4 - (len(b64) % 4)
    if padding < 4:
        b64 += "=" * padding
    data = base64.b64decode(b64)

    positions: set[int] = set()
    for byte_index, byte_value in enumerate(data):
        for bit_index in range(8):
            if byte_value & (1 << (7 - bit_index)):
                positions.add(byte_index * 8 + bit_index + 1)
    return positions


def parse_hof_players(raw: str) -> list[HofPlayer]:
    """Parse HoF response into player entries.

    Format: ;rank,name,guild,level,honor,class,flag;...;
    """
    players: list[HofPlayer] = []
    for entry in raw.strip(";").split(";"):
        if not entry:
            continue
        parts = entry.split(",")
        if len(parts) < 4:
            continue
        if parts[1] == "" or entry.endswith(",,,0,0,0,"):
            continue
        try:
            rank = int(parts[0])
            name = parts[1]
            level = int(parts[3])
            players.append(HofPlayer(rank=rank, name=name, level=level))
        except (ValueError, IndexError):
            continue
    return players


def parse_equipment_idents(raw: str) -> list[EquipmentIdent]:
    """Parse otherplayersaveequipment into equipment identities.

    Format: 19 integers per slot, 10 slots, delimited by '/'.
    """
    fields = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
    idents: list[EquipmentIdent] = []
    for slot in range(10):
        offset = slot * ITEM_FIELD_COUNT
        if offset + ITEM_FIELD_COUNT > len(fields):
            break
        item_type = fields[offset + ITEM_FIELD_TYPE] & 0xFF
        if item_type < 1 or item_type > 10:
            continue

        model_info = fields[offset + ITEM_FIELD_MODEL] & 0xFFFF
        class_id = model_info // MODEL_CLASS_DIVISOR
        model_id = model_info % MODEL_CLASS_DIVISOR

        # sf-tools: Class = trunc(picIndex / 1000) + 1 → 1-based
        # color_class: type >= 8 → 0 (classless), else Class
        sf_class = class_id + 1
        color_class = 0 if item_type >= 8 else sf_class

        # Color: (Index >= 50 || Type == 10) ? 0 : (sum_fields % 5)
        is_epic = model_id >= 50
        if is_epic or item_type == 10:
            color = 0
        else:
            damage_min = fields[offset + ITEM_FIELD_MIN_DAMAGE]
            damage_max = fields[offset + ITEM_FIELD_MAX_DAMAGE]
            attr_types_sum = sum(
                fields[offset + ITEM_FIELD_ATTR_TYPE_0 + i] for i in range(3)
            )
            attr_values_sum = sum(
                fields[offset + ITEM_FIELD_ATTR_VALUE_0 + i] for i in range(3)
            )
            color = (damage_max + damage_min + attr_types_sum + attr_values_sum) % 5

        idents.append(
            EquipmentIdent(
                item_type=item_type,
                color_class=color_class,
                model_id=model_id,
                color=color,
            )
        )
    return idents


def get_scrapbook_position(ident: EquipmentIdent) -> int | None:
    """Compute scrapbook bit position for an equipment ident.

    Returns None if the item has no valid boundary entry.
    sf-tools boundaries are 0-indexed; our bitfield is 1-indexed, so +1.
    """
    type_key = ident.item_type - 1
    if ident.color_class >= len(SCRAPBOOK_BOUNDARIES):
        return None
    boundary_map = SCRAPBOOK_BOUNDARIES[ident.color_class]
    if type_key not in boundary_map:
        return None
    boundary = boundary_map[type_key]

    is_epic = ident.model_id >= 50
    position = ident.model_id - 1

    if is_epic:
        position -= 49  # model_id - 50
        start = boundary[1]
    elif ident.item_type == 10:
        start = boundary[0]
    else:
        position *= 5
        position += ident.color
        start = boundary[0]

    return max(0, start + position) + 1


def count_missing_items(
    idents: list[EquipmentIdent],
    owned_positions: set[int],
) -> int:
    """Count how many equipment idents are missing from the owned scrapbook."""
    missing_count = 0
    for ident in idents:
        if ident.model_id >= MAX_MODEL_ID:
            continue
        position = get_scrapbook_position(ident)
        if position is not None and position not in owned_positions:
            missing_count += 1
    return missing_count


# ---------------------------------------------------------------------------
# Scrapbook class — state + crawl orchestration
# ---------------------------------------------------------------------------


class Scrapbook:
    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.owned_positions: set[int] = set()
        self.item_count: int = 0
        self.monster_count: int = 0

    def parse(self) -> None:
        raw = self.session.login_data.get("scrapbook.r", "")
        if not raw:
            return
        self.owned_positions = decode_scrapbook(raw)
        self.item_count = len(self.owned_positions & VALID_ITEM_POSITIONS)
        self.monster_count = sum(
            1 for p in self.owned_positions if p <= MONSTER_POSITIONS
        )

    async def poll_async(self) -> None:
        """Fetch the full scrapbook bitfield from the server and re-parse."""
        await self.session.request_and_update_async("PlayerPollScrapbook", "")
        self.parse()

    @property
    def owned_total(self) -> int:
        return self.item_count + self.monster_count

    @property
    def missing_items(self) -> int:
        return len(VALID_ITEM_POSITIONS) - self.item_count

    @property
    def item_pct(self) -> float:
        if not self.owned_positions:
            return 0.0
        return min(self.item_count / len(VALID_ITEM_POSITIONS) * 100.0, 100.0)

    async def rank_from_db_async(self, max_level: int) -> list[CrawlTarget]:
        """Score pre-crawled players from DB against own scrapbook.

        Reads player equipment positions from scrapbook_players table
        (populated by cron_crawl.py), counts missing items per player,
        returns sorted targets.
        """
        logger = get_main_logger()
        await self.poll_async()
        server = self.session.server
        own_name = self.session.player_name

        logger.info("Scrapbook: loading players from DB ")

        players = await load_players(server, max_level)

        logger.info(
            f"Scrapbook: scoring {len(players)} players from DB "
            f"({self.missing_items} missing items, {self.item_pct:.1f}% complete)"
        )

        targets: list[CrawlTarget] = []
        for name, level, positions in players:
            if name == own_name:
                continue
            missing = len((positions & VALID_ITEM_POSITIONS) - self.owned_positions)
            if missing > 0:
                targets.append(CrawlTarget(name=name, missing=missing, level=level))

        targets.sort(key=lambda t: (-t.missing, t.level))
        targets = targets[:MAX_QUEUE_SIZE]

        if targets:
            logger.info(
                f"Scrapbook: top target: {targets[0].name} "
                f"({targets[0].missing} missing items)"
            )
        else:
            logger.info("Scrapbook: no targets with missing items found")

        return targets
