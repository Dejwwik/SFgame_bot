from sfbot.constants import (
    ITEM_FIELD_MODEL,
    ITEM_FIELD_MUSHROOM_PRICE,
    ITEM_FIELD_PRICE,
    ITEM_FIELD_TYPE,
    VALUES_DELIMITER,
)
from sfbot.exceptions import APIError, InventoryFullError
from sfbot.inventory import Inventory
from sfbot.legendary_dungeon.constants import (
    BASE_ESCAPE_RATE,
    BOSS_DMG,
    BROKEN_ARMOR_MULTIPLIER,
    FIGHT_DMG,
    GEM_FIELDS,
    GOOD_DOOR_TYPES,
    HEAL_THRESHOLD,
    INSTA_HEAL_EFFECT,
    KEYS_TARGET,
    MAX_STEPS,
    MONSTER_DOOR_TYPES,
    OWNED_GEM_SLOTS,
    RESOURCE_DOOR_TYPES,
    SAFE_ENCOUNTERS,
    SAFE_ROOMS,
    SHOP_ITEMS,
    SKIP_ROOMS,
    START_HP_THRESHOLD,
    TRAP_DMG,
    TRIAL_DOOR_TYPES,
    URGENT_HP_THRESHOLD,
    URGENT_TIME_REMAINING,
)
from sfbot.legendary_dungeon.models import (
    Door,
    DoorTrap,
    DoorType,
    DungeonEffect,
    DungeonEffectType,
    DungeonStage,
    DungeonState,
    EventTheme,
    GemEffect,
    GemOfFate,
    GemSpecial,
    GemType,
    MerchantOffer,
    RoomEncounter,
    RoomType,
    RunStats,
    TotalStats,
)
from sfbot.legendary_dungeon.utils import pick_best_gem, safe_enum, score_gem
from sfbot.logging import get_main_logger
from sfbot.session import GameSession

logger = get_main_logger()


# ── Parsing ──────────────────────────────────────────────────────────────────


# Parse a blessing or curse from wire fields.
# The strength field encodes both remaining_uses (upper digits) and power (lower 4 digits):
#   remaining_uses = remaining_strength // 10_000
#   strength       = remaining_strength % 10_000
def parse_effect(
    typ_val: int,
    remaining_strength: int,
    max_uses: int,
) -> DungeonEffect | None:
    if typ_val <= 0:
        return None
    effect_type = safe_enum(DungeonEffectType, typ_val)
    if effect_type is None:
        return None
    return DungeonEffect(
        typ=effect_type,
        remaining_uses=remaining_strength // 10_000,
        max_uses=max_uses,
        strength=remaining_strength % 10_000,
    )


# ── iadungeon field layout ──────────────────────────────────────────────────
#
#  [0]  random_id        [1]  health_status   [2]  current_hp
#  [3]  pre_battle_hp    [4]  max_hp
#  [5..7]  blessing types          [8..10]  curse types
#  [11..13] blessing strength      [14] curse_0 strength
#  [15] stage            [16] gem_count       [17] current_floor  [18] max_floor
#  [19..20] door types (DoorSelect) / [19] room_type (otherwise)
#  [22] encounter
#  [25..26] door traps
#  [39] keys
#  [40..41] curse_1/curse_2 strength
#  [42..44] blessing max_uses      [45..47] curse max_uses


def parse_dungeon_state(vals: list[str]) -> DungeonState:
    state = DungeonState(
        health_status=int(vals[1]),
        current_hp=int(vals[2]),
        pre_battle_hp=int(vals[3]),
        max_hp=int(vals[4]),
        gem_count=int(vals[16]),
        current_floor=int(vals[17]),
        max_floor=int(vals[18]),
        keys=int(vals[39]),
    )

    # Blessings: types at [5..7], strength at [11..13], max_uses at [42..44]
    for i in range(3):
        state.blessings[i] = parse_effect(
            typ_val=int(vals[5 + i]),
            remaining_strength=int(vals[11 + i]),
            max_uses=int(vals[42 + i]),
        )
    # Curses: types at [8..10], strength at [14,40,41] (non-contiguous), max_uses at [45..47]
    curse_strength_indices = [14, 40, 41]
    for i in range(3):
        state.curses[i] = parse_effect(
            typ_val=int(vals[8 + i]),
            remaining_strength=int(vals[curse_strength_indices[i]]),
            max_uses=int(vals[45 + i]),
        )

    state.stage = DungeonStage(int(vals[15]))

    if state.stage == DungeonStage.DOOR_SELECT:
        for i in range(2):
            raw_door = int(vals[19 + i])
            door_type = safe_enum(DoorType, raw_door) if raw_door else DoorType.BLOCKED
            if door_type is None:
                door_type = DoorType.BLOCKED
            raw_trap = int(vals[25 + i])
            trap = safe_enum(DoorTrap, raw_trap) if raw_trap else None
            state.doors[i] = Door(typ=door_type, trap=trap)
    else:
        raw_room = int(vals[19])
        if raw_room:
            state.room_type = safe_enum(RoomType, raw_room)

    state.encounter = RoomEncounter.parse(int(vals[22]))
    return state


# Parse a single gem from 6 consecutive wire ints: [type, adv_effect, adv_pwr, dis_effect, dis_pwr, special].
def parse_gem(chunk: list[int]) -> GemOfFate | None:
    if all(v == 0 for v in chunk):
        return None
    return GemOfFate(
        typ=GemType(chunk[0]),
        advantage=safe_enum(GemEffect, chunk[1]) if chunk[1] else None,
        advantage_pwr=chunk[2],
        disadvantage=safe_enum(GemEffect, chunk[3]) if chunk[3] else None,
        disadvantage_pwr=chunk[4],
        special=safe_enum(GemSpecial, chunk[5]) if chunk[5] else None,
    )


# Parse the iadungeonsoulstones wire string into (owned, available) gem lists.
# First 3 chunks = owned gems (carried this run), remaining = choices after boss kill.
def parse_soul_stones(raw: str) -> tuple[list[GemOfFate], list[GemOfFate]]:
    vals = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
    chunks = [vals[i : i + GEM_FIELDS] for i in range(0, len(vals), GEM_FIELDS)]

    owned: list[GemOfFate] = []
    for chunk in chunks[:OWNED_GEM_SLOTS]:
        gem = parse_gem(chunk)
        if gem is not None:
            owned.append(gem)

    available: list[GemOfFate] = []
    for chunk in chunks[OWNED_GEM_SLOTS:]:
        gem = parse_gem(chunk)
        if gem is not None:
            available.append(gem)

    return owned, available


# Parse current run statistics from iadungeonstats.
def parse_run_stats(vals: list[str]) -> RunStats:
    return RunStats(
        items_found=int(vals[0]),
        epics_found=int(vals[1]),
        keys_found=int(vals[2]),
        silver_found=int(vals[3]),
        attempts=int(vals[4]),
    )


# Parse lifetime statistics from iadungeonstatstotal.
def parse_total_stats(vals: list[str]) -> TotalStats:
    return TotalStats(
        legendaries_found=int(vals[0]),
        best_run_attempts=int(vals[1]),
        enemies_defeated=int(vals[2]),
        epics_found=int(vals[3]),
        gold_found=int(vals[4]),
    )


# ── Main class ───────────────────────────────────────────────────────────────


class LegendaryDungeon:
    def __init__(self, session: GameSession, inventory: Inventory) -> None:
        self.session = session
        self.inventory = inventory
        self.theme: EventTheme | None = None
        self.start_ts: int = 0
        self.end_ts: int = 0
        self.close_ts: int = 0
        self.dungeon: DungeonState | None = None
        self.run_stats: RunStats | None = None
        self.total_stats: TotalStats | None = None
        self.owned_gems: list[GemOfFate] = []
        self.available_gems: list[GemOfFate] = []
        self.merchant_offers: list[MerchantOffer] = []
        self.refresh()

    def log_info(self, msg: str) -> None:
        get_main_logger().info(msg)

    # ── Parsing ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        data = self.session.login_data
        self._parse_event_time(data)
        self._parse_dungeon(data)
        self._parse_stats(data)
        self._parse_gems(data)
        self._parse_merchant(data)

    def _parse_event_time(self, data: dict[str, str]) -> None:
        if "iadungeontime" not in data:
            self.theme = None
            self.start_ts = self.end_ts = self.close_ts = 0
            return
        vals = data["iadungeontime"].split(VALUES_DELIMITER)
        self.theme = EventTheme(int(vals[0]))
        self.start_ts = int(vals[1])
        self.end_ts = int(vals[2])
        self.close_ts = int(vals[3])

    def _parse_dungeon(self, data: dict[str, str]) -> None:
        raw = (
            data.get("iadungeonsave")
            or data.get("iadungeon.iadungeonsave")
            or data.get("iadungeon")
        )
        if raw is None:
            self.dungeon = None
            return
        self.dungeon = parse_dungeon_state(raw.split(VALUES_DELIMITER))

    def _parse_stats(self, data: dict[str, str]) -> None:
        if "iadungeonstats" in data:
            self.run_stats = parse_run_stats(
                data["iadungeonstats"].split(VALUES_DELIMITER)
            )
        else:
            self.run_stats = None

        if "iadungeonstatstotal" in data:
            self.total_stats = parse_total_stats(
                data["iadungeonstatstotal"].split(VALUES_DELIMITER)
            )
        else:
            self.total_stats = None

    def _parse_gems(self, data: dict[str, str]) -> None:
        if "iadungeonsoulstones" in data:
            self.owned_gems, self.available_gems = parse_soul_stones(
                data["iadungeonsoulstones"]
            )
        else:
            self.owned_gems = []
            self.available_gems = []

    def _parse_merchant(self, data: dict[str, str]) -> None:
        # Server sends key as "iamerchant(N)" with size hint — find it.
        raw = data.get("iamerchant", "")
        found_key = "iamerchant" if raw else ""
        if not raw:
            found_key = next((k for k in data if k.startswith("iamerchant")), "")
            raw = data.get(found_key, "") if found_key else ""
        if not raw:
            return  # preserve offers — server only sends iamerchant on room entry
        vals = [int(x) for x in raw.split(VALUES_DELIMITER) if x]
        offers: list[MerchantOffer] = []
        for i in range(0, len(vals) - 2, 3):
            chunk = vals[i : i + 3]
            if all(v == 0 for v in chunk):
                continue
            typ = safe_enum(DungeonEffectType, chunk[0])
            if typ is None:
                continue
            strength_enc = chunk[1]
            offers.append(
                MerchantOffer(
                    typ=typ,
                    max_uses=strength_enc // 10_000,
                    strength=strength_enc % 10_000,
                    keys=chunk[2],
                )
            )
        self.merchant_offers = offers

    # ── Properties ───────────────────────────────────────────────────────

    def healing_pct(self) -> float:
        raw = self.session.login_data.get("characterstatus", "")
        vals = raw.split(VALUES_DELIMITER)
        if len(vals) <= 22 or not vals[22]:
            return 0.0
        heal_started_ts = int(vals[22])
        if heal_started_ts <= 0:
            return 0.0
        now = self.session.server_time()
        elapsed_minutes = (now - heal_started_ts) / 60
        return min(elapsed_minutes * (100 / 24 / 60), 100.0)

    @property
    def is_active(self) -> bool:
        if self.theme is None:
            return False
        now = self.session.server_time()
        return self.start_ts <= now <= self.close_ts

    @property
    def is_enterable(self) -> bool:
        if self.theme is None:
            return False
        now = self.session.server_time()
        return self.start_ts <= now <= self.end_ts

    @property
    def is_entered(self) -> bool:
        if self.dungeon is None:
            return False
        return self.dungeon.stage != DungeonStage.NOT_ENTERED

    @property
    def current_floor(self) -> int:
        return self.dungeon.current_floor if self.dungeon else 0

    @property
    def max_floor(self) -> int:
        return self.dungeon.max_floor if self.dungeon else 0

    @property
    def hp_pct(self) -> float:
        if not self.dungeon or self.dungeon.max_hp <= 0:
            return 0.0
        return self.dungeon.current_hp / self.dungeon.max_hp * 100

    def status_summary(self) -> str:
        if not self.is_active:
            return "Dungeon: event not active"
        parts = [f"Dungeon: {self.theme.name if self.theme else 'unknown'}"]
        if self.dungeon:
            d = self.dungeon
            parts.append(f"floor {d.current_floor}/{d.max_floor}")
            parts.append(f"HP {d.current_hp}/{d.max_hp}")
            parts.append(f"keys={d.keys}")
            parts.append(f"stage={d.stage.name}")
        else:
            parts.append("not entered")
        return ", ".join(parts)

    # ── Combat helpers ───────────────────────────────────────────────────

    def section_index(self) -> int:
        if not self.dungeon:
            return 0
        return min(self.dungeon.current_floor // 25, 3)

    def next_boss_floor(self) -> int:
        if not self.dungeon:
            return 25
        floor = self.dungeon.current_floor
        return next((b for b in (25, 50, 75, 100) if floor < b), 100)

    def floors_to_boss(self) -> int:
        if not self.dungeon:
            return 25
        return self.next_boss_floor() - self.dungeon.current_floor

    def max_fight_dmg_pct(self) -> float:
        return FIGHT_DMG[self.section_index()]

    def max_boss_dmg_pct(self) -> float:
        return BOSS_DMG[self.next_boss_floor()]

    def has_curse(self, typ: DungeonEffectType) -> bool:
        if not self.dungeon:
            return False
        return any(c is not None and c.typ == typ for c in self.dungeon.curses)

    def has_blessing(self, typ: DungeonEffectType) -> bool:
        if not self.dungeon:
            return False
        return any(
            b is not None and b.typ == typ and b.remaining_uses > 0
            for b in self.dungeon.blessings
        )

    def effective_fight_dmg_pct(self) -> float:
        if self.has_blessing(DungeonEffectType.ONE_HIT_WONDER):
            return 0.0
        dmg = self.max_fight_dmg_pct()
        if self.has_curse(DungeonEffectType.BROKEN_ARMOR):
            dmg *= BROKEN_ARMOR_MULTIPLIER
        return dmg

    def can_survive_boss(self) -> bool:
        return self.hp_pct > self.max_boss_dmg_pct()

    def can_survive_fight(self) -> bool:
        return self.hp_pct > self.effective_fight_dmg_pct()

    def is_last_section(self) -> bool:
        if not self.dungeon:
            return False
        return self.dungeon.current_floor >= 75

    def needs_more_keys(self) -> bool:
        if not self.dungeon:
            return False
        if self.is_last_section():
            return False
        section = self.section_index()
        target = KEYS_TARGET[min(section, len(KEYS_TARGET) - 1)]
        return self.dungeon.keys < target

    def gem_monster_dmg_reduction(self) -> float:
        total = sum(
            (
                abs(g.advantage_pwr)
                if g.advantage == GemEffect.DAMAGE_FROM_MONSTERS
                else 0
            )
            - (
                abs(g.disadvantage_pwr)
                if g.disadvantage == GemEffect.DAMAGE_FROM_MONSTERS
                else 0
            )
            for g in self.owned_gems
        )
        return total / 100

    def gem_escape_chance_bonus(self) -> float:
        total = sum(
            (abs(g.advantage_pwr) if g.advantage == GemEffect.ESCAPE_CHANCE else 0)
            - (
                abs(g.disadvantage_pwr)
                if g.disadvantage == GemEffect.ESCAPE_CHANCE
                else 0
            )
            for g in self.owned_gems
        )
        return total / 100

    def should_start_run(self) -> bool:
        if not self.dungeon:
            return False
        if self.dungeon.stage in (DungeonStage.NOT_ENTERED, DungeonStage.COMPLETED):
            return True

        # Less than 1 hour left → enter no matter what if HP >= 20%
        now = self.session.server_time()
        if self.end_ts - now < URGENT_TIME_REMAINING:
            if self.hp_pct >= URGENT_HP_THRESHOLD:
                return True

        floor = self.dungeon.current_floor
        dmg_reduction = self.gem_monster_dmg_reduction()
        escape_bonus = self.gem_escape_chance_bonus()
        boss_dmg = BOSS_DMG[100] * (1 - dmg_reduction)
        fight_dmg = FIGHT_DMG[3] * (1 - dmg_reduction)
        escape_rate = min(BASE_ESCAPE_RATE + escape_bonus, 1.0)
        fight_cost = fight_dmg * (1 - escape_rate)
        if floor == 99:
            return self.hp_pct > boss_dmg
        if floor == 98:
            return self.hp_pct > boss_dmg + fight_cost
        if floor == 97:
            return self.hp_pct > boss_dmg + 2 * fight_cost
        return self.hp_pct >= START_HP_THRESHOLD

    # ── API commands ─────────────────────────────────────────────────────

    async def enter_async(self) -> None:
        if self.theme is None:
            return
        await self.session.request_and_update_async(
            "IADungeonStart", f"{self.theme.value}/0"
        )
        self.refresh()
        logger.info(f"Dungeon: entered {self.theme.name}")

    async def pick_door_async(self, pos: int, use_key: bool = False) -> None:
        code = pos + 5 if use_key else pos + 1
        await self.session.request_and_update_async("IADungeonInteract", str(code))
        self.refresh()

    async def fight_async(self) -> None:
        await self.session.request_and_update_async("IADungeonInteract", "20")
        self.refresh()

    async def escape_async(self) -> None:
        await self.session.request_and_update_async("IADungeonInteract", "21")
        self.refresh()

    async def open_encounter_async(self) -> None:
        await self.session.request_and_update_async("IADungeonInteract", "40")
        self.refresh()

    async def skip_encounter_async(self) -> None:
        await self.session.request_and_update_async("IADungeonInteract", "42")
        self.refresh()

    async def interact_room_async(self) -> None:
        await self.session.request_and_update_async("IADungeonInteract", "50")
        self.refresh()

    async def leave_room_async(self) -> None:
        await self.session.request_and_update_async("IADungeonInteract", "51")
        self.refresh()

    async def collect_key_async(self) -> None:
        await self.session.request_and_update_async("IADungeonInteract", "60")
        self.refresh()

    async def continue_async(self) -> None:
        await self.session.request_and_update_async("IADungeonInteract", "70")
        self.refresh()

    async def play_rps_async(self, choice: int) -> None:
        await self.session.request_and_update_async(
            "IADungeonInteract", str(90 + choice)
        )
        self.refresh()

    async def pick_gem_async(self, gem_type: int) -> None:
        await self.session.request_and_update_async(
            "IADungeonSelectSoulStone", str(gem_type)
        )
        self.refresh()

    async def merchant_buy_async(self, effect: int, keys: int) -> None:
        await self.session.request_and_update_async(
            "IADungeonMerchantBuy", f"{effect}/{keys}"
        )
        self.refresh()

    # ── Loot item handling ───────────────────────────────────────────────

    # Find where pending loot data lives. Returns (data_key, field_offset) or None.
    # "ialootitem" = regular room loot (offset 0, fields start at index 0).
    # "iapendingitems" = boss kill reward (offset 1, fields[0] is count prefix).
    def _loot_source(self) -> tuple[str, int] | None:
        raw = self.session.login_data.get("ialootitem", "")
        if raw:
            fields = raw.split(VALUES_DELIMITER)
            # 19 fields = a full item; ITEM_FIELD_TYPE != 0 means it's a real item
            if len(fields) >= 19 and int(fields[ITEM_FIELD_TYPE]) != 0:
                return "ialootitem", 0
        raw = self.session.login_data.get("iapendingitems", "")
        if raw:
            fields = raw.split(VALUES_DELIMITER)
            if (
                len(fields) >= 20
                and int(fields[0]) > 0
                and int(fields[1 + ITEM_FIELD_TYPE]) != 0
            ):
                return "iapendingitems", 1
        return None

    def has_pending_loot(self) -> bool:
        return self._loot_source() is not None

    # Build the ItemCommandIdent string (typ/model/price/mush_price) for the loot item.
    # The server verifies this to prevent item duplication or spoofing.
    def _loot_ident(self) -> str:
        source = self._loot_source()
        if source is None:
            return ""
        key, offset = source
        raw = self.session.login_data[key]
        f = raw.split(VALUES_DELIMITER)
        typ = int(f[offset + ITEM_FIELD_TYPE]) & 0xFF
        model = int(f[offset + ITEM_FIELD_MODEL]) & 0xFFFF
        silver = int(f[offset + ITEM_FIELD_PRICE])
        mush = int(f[offset + ITEM_FIELD_MUSHROOM_PRICE])
        return f"{typ}/{model}/{silver}/{mush}"

    async def take_loot_async(self, to_wire: str) -> None:
        ident = self._loot_ident()
        params = f"401/1/{to_wire}/{ident}"
        result = await self.session.request_and_update_async("PlayerItemMove", params)
        self.session.login_data.update(result)
        self.refresh()

    # Auto-collect any pending loot into the first free backpack slot.
    async def _take_loot_if_pending(self) -> None:
        source = self._loot_source()
        if source is None:
            return
        slot = self.inventory.get_free_slot()
        if slot is None:
            raise InventoryFullError("dungeon loot pending but inventory full")
        source_label = "boss reward" if source[0] == "iapendingitems" else "room loot"
        try:
            await self.take_loot_async(slot.wire)
            logger.info(f"Dungeon: collected {source_label}")
        except APIError:
            logger.debug("Dungeon: stale loot cleared")

    # ── Door selection ───────────────────────────────────────────────────

    def pick_door(self) -> int:
        if not self.dungeon:
            return 0
        doors = self.dungeon.doors
        keys = self.dungeon.keys
        has_pick = self.has_blessing(DungeonEffectType.LOCK_PICK)
        has_disarm = self.has_blessing(DungeonEffectType.DISARM_TRAPS)
        has_healing = self.has_blessing(
            DungeonEffectType.ROAD_TO_RECOVERY
        ) or self.has_blessing(DungeonEffectType.ELIXIR_OF_LIFE)
        hoarding = self.needs_more_keys()
        doomed = not self.can_survive_boss()

        last_section = self.is_last_section()

        hp = self.hp_pct

        def door_score(door: Door) -> int:
            t = door.typ
            if t == DoorType.BLOCKED:
                return -100
            if door.trap and not has_disarm and hp <= TRAP_DMG:
                return -95
            if t == DoorType.DOUBLE_LOCKED_DOOR:
                if has_pick:
                    return 10
                if keys < 2:
                    return -100
                if doomed:
                    return -90
                if hoarding:
                    return -30
                if last_section:
                    return 10
                return -5
            if t == DoorType.LOCKED_DOOR:
                if has_pick:
                    return 15
                if keys < 1:
                    return -100
                if doomed:
                    return -80
                if hoarding:
                    return -20
                if last_section:
                    return 15
                return -5
            if t == DoorType.SACRIFICIAL_DOOR:
                return -25
            if t == DoorType.CURSED_DOOR:
                return -60
            if t in GOOD_DOOR_TYPES:
                return 50
            if t in RESOURCE_DOOR_TYPES:
                return 30
            if t == DoorType.TRIAL_ROOM_EXIT:
                return 40
            if t in TRIAL_DOOR_TYPES:
                return -10
            if t == DoorType.MYSTERY_DOOR:
                if door.trap and not has_disarm:
                    return -40
                return 15
            if t in MONSTER_DOOR_TYPES and door.trap and not has_disarm:
                return -55
            if t in MONSTER_DOOR_TYPES and has_healing:
                return 20
            if hoarding:
                return 5
            return 0

        s0 = door_score(doors[0])
        s1 = door_score(doors[1])
        return 0 if s0 >= s1 else 1

    # ── Room handling ────────────────────────────────────────────────────

    def log_status(self) -> None:
        d = self.dungeon
        if d is None:
            return
        blessings = [f"{b.typ.name}({b.remaining_uses})" for b in d.blessings if b]
        curses = [f"{c.typ.name}({c.remaining_uses})" for c in d.curses if c]
        gems = [g.typ.name for g in self.owned_gems if g.typ]
        parts = [f"HP {self.hp_pct:.1f}%", f"Keys ({d.keys})"]
        if blessings:
            parts.append(f"Blessings: {', '.join(blessings)}")
        if curses:
            parts.append(f"Curses: {', '.join(curses)}")
        if gems:
            parts.append(f"Gems: {', '.join(gems)}")
        self.log_info(f"Floor {d.current_floor} | {' | '.join(parts)}")

    async def handle_monster(self) -> None:
        d = self.dungeon
        if d is None:
            return

        if d.room_type == RoomType.BOSS_ROOM or self.floors_to_boss() <= 1:
            self.log_info(f"   Encounter: BOSS (id={d.encounter.monster_id})")
            self.log_info("   Decision: FIGHT (boss)")
            await self.fight_async()
            self.log_info(f"   Result: HP now {self.hp_pct:.1f}%")
            logger.info(
                f"Dungeon: fought boss on floor {d.current_floor}, "
                f"HP {self.hp_pct:.0f}%"
            )
            return

        self.log_info(f"   Encounter: MONSTER (id={d.encounter.monster_id})")

        if self.has_blessing(DungeonEffectType.ONE_HIT_WONDER):
            self.log_info("   Decision: FIGHT (ONE_HIT_WONDER)")
            await self.fight_async()
            self.log_info(f"   Result: HP now {self.hp_pct:.1f}%")
            return

        if self.has_blessing(DungeonEffectType.ESCAPE_ASSISTANT):
            self.log_info("   Decision: ESCAPE (ESCAPE_ASSISTANT)")
            await self.escape_async()
            self.log_info(f"   Result: HP now {self.hp_pct:.1f}%")
            return

        if self.floors_to_boss() <= 2 and not self.can_survive_boss():
            if self.can_survive_fight():
                self.log_info("   Decision: FIGHT (doomed, hunting keys)")
                await self.fight_async()
            else:
                self.log_info("   Decision: ESCAPE (doomed, too weak to fight)")
                await self.escape_async()
            self.log_info(f"   Result: HP now {self.hp_pct:.1f}%")
            return

        if self.needs_more_keys() and self.can_survive_fight():
            self.log_info("   Decision: FIGHT (need keys)")
            await self.fight_async()
            self.log_info(f"   Result: HP now {self.hp_pct:.1f}%")
            return

        self.log_info("   Decision: ESCAPE (preserving HP)")
        await self.escape_async()
        self.log_info(f"   Result: HP now {self.hp_pct:.1f}%")

    async def handle_encounter(self, stay_in_room: bool = False) -> None:
        d = self.dungeon
        if d is None:
            return
        etype = d.encounter.encounter_type
        if etype is not None and etype in SAFE_ENCOUNTERS:
            self.log_info(f"   Encounter: {etype.name} (safe)")
            self.log_info("   Decision: OPEN")
            await self.open_encounter_async()
        else:
            self.log_info(f"   Encounter: {etype.name if etype else 'unknown'} (risky)")
            self.log_info("   Decision: SKIP")
            await self.skip_encounter_async()
        if (
            not stay_in_room
            and self.dungeon is not None
            and self.dungeon.stage == DungeonStage.ROOM_ENTERED
        ):
            await self.continue_async()

    async def handle_key_master_shop(self) -> None:
        if not self.dungeon:
            return

        # iamerchant(N) is present in login_data from login and re-sent on shop entry,
        # so offers should always be populated here. Re-login only as a last resort.
        if not self.merchant_offers:
            await self.session.login_async()
            self.refresh()
        keys = self.dungeon.keys
        if not self.merchant_offers:
            self.log_info("   Shop: no offers available")
            return

        # Log what the merchant is selling.
        self.log_info(f"   Shop: KEY_MASTER_SHOP (keys={keys})")
        for offer in self.merchant_offers:
            self.log_info(
                f"     Offer: {offer.typ.name} uses={offer.max_uses} "
                f"strength={offer.strength} cost={offer.keys} keys"
            )

        hp = self.hp_pct

        # Walk SHOP_ITEMS in priority order (ONE_HIT_WONDER > ESCAPE_ASSISTANT > healing).
        # Buy the first affordable item the merchant offers that we don't already have.
        for effect, _, _ in SHOP_ITEMS:
            # Already have this blessing active — no point buying again.
            if self.has_blessing(effect):
                continue
            # Don't waste keys on healing when HP is already comfortable.
            if effect in INSTA_HEAL_EFFECT and hp >= HEAL_THRESHOLD:
                continue
            # Merchant may not stock every effect — skip if not on offer.
            offer = next((o for o in self.merchant_offers if o.typ == effect), None)
            if offer is None:
                continue
            # Can't afford it — try next priority.
            if keys < offer.keys:
                continue
            await self.merchant_buy_async(effect.value, offer.keys)
            self.log_info(f"   Bought: {effect.name} for {offer.keys} keys")
            return

    async def handle_room_entered(self) -> None:
        d = self.dungeon
        if d is None:
            return
        enc = d.encounter
        room = d.room_type

        if enc.is_monster:
            await self.handle_monster()
            return

        # Known room types take priority over encounter field.
        # Many special rooms send encounter=0 as default (not a real BRONZE_CHEST).
        if room == RoomType.KEY_MASTER_SHOP:
            self.log_info(f"   Encounter: KEY_MASTER_SHOP (keys={d.keys})")
            await self.handle_key_master_shop()
            self.log_info("   Decision: LEAVE")
            await self.leave_room_async()
            return

        if room is not None and room in SAFE_ROOMS:
            self.log_info(f"   Encounter: {room.name}")
            self.log_info("   Decision: INTERACT")
            await self.interact_room_async()
            await self._take_loot_if_pending()
            return

        if room is not None and room in SKIP_ROOMS:
            self.log_info(f"   Encounter: {room.name} (risky)")
            self.log_info("   Decision: LEAVE")
            await self.leave_room_async()
            return

        if enc.encounter_type is not None:
            await self.handle_encounter(stay_in_room=False)
            return

        if room is None or room == RoomType.EMPTY:
            self.log_info("   Encounter: empty room")
            await self.continue_async()
            return

        self.log_info(f"   Encounter: {room.name if room else 'unknown'} (unhandled)")
        self.log_info("   Decision: LEAVE")
        await self.leave_room_async()

    async def handle_room_interacted(self) -> None:
        d = self.dungeon
        if d is None:
            return
        self.log_info("   COLLECT")
        await self.collect_key_async()
        await self._take_loot_if_pending()
        if self.dungeon and self.dungeon.stage == DungeonStage.ROOM_INTERACTED:
            await self.continue_async()

    async def handle_pick_gem(self) -> None:
        if not self.available_gems:
            return
        floor = self.current_floor

        self.log_info(f"   GEM SELECTION — {len(self.available_gems)} choices:")
        for i, g in enumerate(self.available_gems):
            s = score_gem(g, floor)
            adv = f"{g.advantage.name}({g.advantage_pwr})" if g.advantage else "-"
            dis = (
                f"{g.disadvantage.name}({g.disadvantage_pwr})"
                if g.disadvantage
                else "-"
            )
            spc = g.special.name if g.special else "-"
            self.log_info(
                f"     [{i}] {g.typ.name if g.typ else '?':30s}  "
                f"adv={adv:25s}  dis={dis:25s}  spc={spc:20s}  "
                f"score={s:+.1f}"
            )

        result = pick_best_gem(self.available_gems, floor)
        if result is None:
            return
        idx, gem, score = result
        if gem.typ is None:
            return
        self.log_info(
            f"   Decision: PICK [{idx}] {gem.typ.name} (score={score:+.1f}% HP)"
        )
        await self.pick_gem_async(gem.typ.value)
        await self._take_loot_if_pending()
        logger.info(
            f"Dungeon: picked {gem.typ.name} ({score:+.1f}% HP) at floor {floor}"
        )

    # ── Main step ────────────────────────────────────────────────────────

    async def step_async(self) -> bool:
        if not self.is_active:
            self.log_info("STOPPED: event not active")
            return False

        d = self.dungeon
        if d is None:
            self.log_info("STOPPED: no dungeon data")
            return False

        stage = d.stage

        if stage == DungeonStage.COMPLETED:
            self.log_info("STOPPED: dungeon completed")
            return False

        if stage == DungeonStage.NOT_ENTERED:
            if not self.should_start_run():
                self.log_info("STOPPED: HP too low to start run")
                return False
            self.log_info("   Action: ENTERING dungeon...")
            await self.enter_async()
            return True

        if not d.is_alive:
            if not self.is_active:
                self.log_info("STOPPED: event not active")
                return False
            healed = self.healing_pct()
            threshold = START_HP_THRESHOLD
            time_left = self.end_ts - self.session.server_time()
            if time_left < URGENT_TIME_REMAINING:
                threshold = URGENT_HP_THRESHOLD
            if healed < threshold:
                self.log_info(f"STOPPED: healing in progress ({healed:.0f}%)")
                return False
            self.log_info(f"   Action: ENTERING dungeon (healed {healed:.0f}%)...")
            await self.enter_async()
            return True

        if stage == DungeonStage.DOOR_SELECT:
            self.log_info("-" * 55)
            self.log_status()

            d0, d1 = d.doors[0], d.doors[1]
            trap0 = f" ▲{d0.trap.name}" if d0.trap else ""
            trap1 = f" ▲{d1.trap.name}" if d1.trap else ""
            self.log_info(
                f"   Choice: [LEFT] {d0.typ.name}{trap0} vs "
                f"[RIGHT] {d1.typ.name}{trap1}"
            )

            pos = self.pick_door()
            door = d.doors[pos]
            needs_key = door.typ in (DoorType.LOCKED_DOOR, DoorType.DOUBLE_LOCKED_DOOR)
            use_key = needs_key and not self.has_blessing(DungeonEffectType.LOCK_PICK)
            side = "LEFT" if pos == 0 else "RIGHT"
            key_label = " (using key)" if use_key else ""
            self.log_info(f"   Action: entering {side} ({door.typ.name}){key_label}")
            await self.pick_door_async(pos, use_key=use_key)
            return True

        if stage == DungeonStage.ROOM_ENTERED:
            await self.handle_room_entered()
            return True

        if stage == DungeonStage.ROOM_INTERACTED:
            await self.handle_room_interacted()
            return True

        if stage == DungeonStage.ROOM_SPECIAL:
            if self.available_gems:
                await self.handle_pick_gem()
                return True
            await self.continue_async()
            return True

        if stage == DungeonStage.ROOM_FINISHED:
            await self._take_loot_if_pending()
            await self.continue_async()
            return True

        logger.warning(f"Dungeon: unhandled stage {stage}")
        self.log_info(f"UNKNOWN stage: {stage}")
        return False

    async def run_async(self) -> None:
        self.log_info("=" * 60)
        self.log_info("LEGENDARY DUNGEON RUN")
        self.log_info("=" * 60)
        self.log_info(f"Theme: {self.theme.name if self.theme else 'None'}")
        self.log_info(f"Active: {self.is_active}  Enterable: {self.is_enterable}")
        self.log_info(f"Gem dmg reduction: {self.gem_monster_dmg_reduction():.1%}")
        self.log_info(f"Gem escape bonus: {self.gem_escape_chance_bonus():.1%}")
        d = self.dungeon
        if d:
            self.log_info(
                f"Starting | HP {d.current_hp}/{d.max_hp} ({self.hp_pct:.1f}%) "
                f"| Keys ({d.keys}) | Floor {d.current_floor}/{d.max_floor}"
            )
        self.log_info("")

        steps = 0
        while steps < MAX_STEPS:
            try:
                more = await self.step_async()
            except InventoryFullError:
                raise
            except Exception as exc:
                logger.warning(f"Dungeon: step error: {exc}")
                self.log_info(f"ERROR: {exc}")
                return
            if not more:
                break
            steps += 1
        else:
            logger.warning("Dungeon: hit step limit")
            self.log_info("WARNING: hit step limit")

        self.log_info("")
        self.log_info("=" * 60)
        self.log_info(f"RUN COMPLETE — {steps} steps")
        d = self.dungeon
        if d:
            self.log_info(
                f"Final | HP {self.hp_pct:.1f}% | Keys ({d.keys}) "
                f"| Floor {d.current_floor}/{d.max_floor}"
            )
        if self.run_stats:
            rs = self.run_stats
            self.log_info(
                f"Stats: items={rs.items_found} epics={rs.epics_found} "
                f"keys={rs.keys_found} silver={rs.silver_found} "
                f"attempts={rs.attempts}"
            )
        self.log_info("=" * 60)
