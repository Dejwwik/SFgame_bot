from dataclasses import dataclass
from datetime import datetime

from sfbot.constants import (
    CHARACTER_ARMOR_INDEX,
    CHARACTER_ATTR_COUNT,
    CHARACTER_BASE_ATTR_INDEX,
    CHARACTER_BONUS_ATTR_INDEX,
    CHARACTER_BOUGHT_ATTR_INDEX,
    CHARACTER_CLASS_INDEX,
    CHARACTER_HONOR_INDEX,
    CHARACTER_LEVEL_INDEX,
    CHARACTER_MAX_DAMAGE_INDEX,
    CHARACTER_MIN_DAMAGE_INDEX,
    CHARACTER_MOUNT_END_INDEX,
    CHARACTER_MOUNT_INDEX,
    CHARACTER_PORTAL_DMG_BONUS_INDEX,
    CHARACTER_PORTAL_HP_BONUS_INDEX,
    CHARACTER_RACE_INDEX,
    CHARACTER_RANK_INDEX,
    CHARACTER_XP_INDEX,
    CHARACTER_XP_NEXT_INDEX,
    COMPANION_ARMOR_OFFSET,
    COMPANION_BASE_ATTR_OFFSET,
    COMPANION_BONUS_ATTR_OFFSET,
    COMPANION_MAX_DMG_OFFSET,
    COMPANION_MIN_DMG_OFFSET,
    COMPANION_TOWER_FIRST,
    COMPANION_TOWER_STRIDE,
    GLADIATOR_TRAINER_INDEX,
    POTION_EXPIRY_START_INDEX,
    POTION_ID_START_INDEX,
    POTION_SLOT_COUNT,
    VALUES_DELIMITER,
    WINGS_MODEL_ID,
    Attribute,
    CharClass,
    CompanionClass,
    Enchantment,
    EquipmentSlot,
    Mount,
    PotionAttributeType,
    PotionSize,
    Race,
    RuneType,
)
from sfbot.items.comparison import companion_equipped_items, equipped_items
from sfbot.items.items import Item
from sfbot.logging import get_main_logger
from sfbot.potions import ActivePotion, Potion, calc_dungeon_potion_credits
from sfbot.session import GameSession

ATTR_WIRE_ORDER: list[Attribute] = [
    Attribute.STRENGTH,
    Attribute.DEXTERITY,
    Attribute.INTELLIGENCE,
    Attribute.CONSTITUTION,
    Attribute.LUCK,
]


@dataclass(slots=True)
class EquipmentRunes:
    """Aggregated rune stats from all equipped items."""

    fire_resistance: int = 0
    cold_resistance: int = 0
    lightning_resistance: int = 0
    rune_health: int = 0
    weapon_rune_type: RuneType | None = None
    weapon_rune_value: int = 0
    has_sword_of_vengeance: bool = False
    has_shadow_of_cowboy: bool = False


@dataclass(slots=True)
class CompanionInfo:
    """Pre-parsed companion data for simulation and display."""

    companion_class: CompanionClass
    char_class: CharClass
    level: int
    total_attrs: dict[Attribute, int]
    armor: int
    min_dmg: int
    max_dmg: int
    runes: EquipmentRunes


def collect_runes(
    equipment: dict[EquipmentSlot, Item | None],
    char_class: CharClass,
) -> EquipmentRunes:
    """Aggregate rune stats from all equipped items."""
    fire_resistance = 0
    cold_resistance = 0
    lightning_resistance = 0
    rune_health = 0
    weapon_rune_type: RuneType | None = None
    weapon_rune_value = 0
    has_sword_of_vengeance = False
    has_shadow_of_cowboy = False

    weapon_slots = [EquipmentSlot.WEAPON]
    if char_class == CharClass.ASSASSIN:
        weapon_slots.append(EquipmentSlot.SHIELD)

    rune_totals: dict[RuneType, int] = {}
    for slot in weapon_slots:
        weapon = equipment[slot]
        if weapon is None:
            continue
        if weapon.enchantment == Enchantment.SWORD_OF_VENGEANCE:
            has_sword_of_vengeance = True
        for rune in weapon.runes:
            if rune.rune_type in (
                RuneType.FIRE_DMG,
                RuneType.COLD_DMG,
                RuneType.LIGHTNING_DMG,
            ):
                rune_totals[rune.rune_type] = (
                    rune_totals.get(rune.rune_type, 0) + rune.value
                )

    if rune_totals:
        weapon_rune_type = max(rune_totals, key=lambda r: rune_totals[r])
        weapon_rune_value = rune_totals[weapon_rune_type]

    gloves = equipment[EquipmentSlot.GLOVES]
    if gloves is not None and gloves.enchantment == Enchantment.SHADOW_OF_COWBOY:
        has_shadow_of_cowboy = True

    for item in equipment.values():
        if item is None:
            continue
        for rune in item.runes:
            match rune.rune_type:
                case RuneType.FIRE_RES:
                    fire_resistance += rune.value
                case RuneType.COLD_RES:
                    cold_resistance += rune.value
                case RuneType.LIGHTNING_RES:
                    lightning_resistance += rune.value
                case RuneType.TOTAL_RES:
                    fire_resistance += rune.value
                    cold_resistance += rune.value
                    lightning_resistance += rune.value
                case RuneType.EXTRA_HP:
                    rune_health += rune.value

    return EquipmentRunes(
        fire_resistance=fire_resistance,
        cold_resistance=cold_resistance,
        lightning_resistance=lightning_resistance,
        rune_health=rune_health,
        weapon_rune_type=weapon_rune_type,
        weapon_rune_value=weapon_rune_value,
        has_sword_of_vengeance=has_sword_of_vengeance,
        has_shadow_of_cowboy=has_shadow_of_cowboy,
    )


class Character:
    """Player character attributes, info, active potions, and companions."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.parse()

    def parse(self) -> None:
        data = self.session.login_data
        raw = data["ownplayersavecharacter"].split(VALUES_DELIMITER)
        character_values: list[int] = [int(x) for x in raw if x]

        self.level: int = character_values[CHARACTER_LEVEL_INDEX] & 0xFFFF
        self.xp: int = character_values[CHARACTER_XP_INDEX]
        self.xp_next: int = character_values[CHARACTER_XP_NEXT_INDEX]
        self.honor: int = character_values[CHARACTER_HONOR_INDEX]
        self.rank: int = character_values[CHARACTER_RANK_INDEX]
        self.race: str = Race(character_values[CHARACTER_RACE_INDEX]).name
        self.class_id: int = character_values[CHARACTER_CLASS_INDEX]
        self.class_name: str = CharClass(
            character_values[CHARACTER_CLASS_INDEX] - 1
        ).name
        self.char_class: CharClass = CharClass(
            character_values[CHARACTER_CLASS_INDEX] - 1
        )

        self.mount_id: int = character_values[CHARACTER_MOUNT_INDEX] & 0xFF
        self.mount: str = Mount(self.mount_id).name
        self.mount_end: int = (
            character_values[CHARACTER_MOUNT_END_INDEX]
            if len(character_values) > CHARACTER_MOUNT_END_INDEX
            else 0
        )
        self.armor: int = character_values[CHARACTER_ARMOR_INDEX]
        self.min_dmg: int = character_values[CHARACTER_MIN_DAMAGE_INDEX]
        self.max_dmg: int = character_values[CHARACTER_MAX_DAMAGE_INDEX]
        self.portal_dmg_bonus: int = (
            character_values[CHARACTER_PORTAL_DMG_BONUS_INDEX]
            if len(character_values) > CHARACTER_PORTAL_DMG_BONUS_INDEX
            else 0
        )
        self.portal_hp_bonus: int = (
            character_values[CHARACTER_PORTAL_HP_BONUS_INDEX]
            if len(character_values) > CHARACTER_PORTAL_HP_BONUS_INDEX
            else 0
        )

        raw_base = character_values[
            CHARACTER_BASE_ATTR_INDEX : CHARACTER_BASE_ATTR_INDEX + CHARACTER_ATTR_COUNT
        ]
        raw_bonus = character_values[
            CHARACTER_BONUS_ATTR_INDEX : CHARACTER_BONUS_ATTR_INDEX
            + CHARACTER_ATTR_COUNT
        ]
        raw_bought = character_values[
            CHARACTER_BOUGHT_ATTR_INDEX : CHARACTER_BOUGHT_ATTR_INDEX
            + CHARACTER_ATTR_COUNT
        ]
        self.base_attrs: dict[Attribute, int] = {
            attr: raw_base[i] for i, attr in enumerate(ATTR_WIRE_ORDER)
        }
        self.bonus_attrs: dict[Attribute, int] = {
            attr: raw_bonus[i] for i, attr in enumerate(ATTR_WIRE_ORDER)
        }
        self.bought_attrs: dict[Attribute, int] = {
            attr: raw_bought[i] for i, attr in enumerate(ATTR_WIRE_ORDER)
        }

        potion_raw = data["ownplayersavepotions"].split(VALUES_DELIMITER)
        potion_values: list[int] = [int(x) for x in potion_raw if x]
        self.potions: list[ActivePotion] = []
        for i in range(POTION_SLOT_COUNT):
            potion_id = (
                potion_values[POTION_ID_START_INDEX + i]
                if len(potion_values) > POTION_ID_START_INDEX + i
                else 0
            )
            expiry_timestamp = (
                potion_values[POTION_EXPIRY_START_INDEX + i]
                if len(potion_values) > POTION_EXPIRY_START_INDEX + i
                else 0
            )
            if potion_id == 0 or expiry_timestamp == 0:
                continue
            if potion_id == WINGS_MODEL_ID:
                attr, size = PotionAttributeType.HP, None
            else:
                attr = PotionAttributeType(potion_id % 5)
                size = PotionSize((potion_id - 1) // 5 + 1)
            self.potions.append(
                ActivePotion(
                    potion=Potion(attr=attr, size=size),
                    expires=expiry_timestamp,
                    slot=i + 1,
                )
            )

        # --- Player equipment runes ---
        player_equipment = equipped_items(self.session)
        self.runes: EquipmentRunes = collect_runes(player_equipment, self.char_class)

        # --- Assassin second weapon damage ---
        self.min_dmg2: int = 0
        self.max_dmg2: int = 0
        if self.char_class == CharClass.ASSASSIN:
            offhand = player_equipment[EquipmentSlot.SHIELD]
            if offhand is not None:
                self.min_dmg2 = offhand.min_dmg  # type: ignore
                self.max_dmg2 = offhand.max_dmg  # type: ignore

        # --- Tower data (gladiator + companions) ---
        tower_raw = data.get("owntower.towerSave", "").split(VALUES_DELIMITER)
        tower_values = [int(x) for x in tower_raw if x]

        self.gladiator: int = (
            tower_values[GLADIATOR_TRAINER_INDEX]
            if len(tower_values) > GLADIATOR_TRAINER_INDEX
            else 0
        )

        # --- Companions ---
        self.companions: dict[CompanionClass, CompanionInfo] = {}
        if self.has_unlocked_companions and tower_values:
            for companion_class in CompanionClass:
                comp_start = (
                    COMPANION_TOWER_FIRST
                    + companion_class.value * COMPANION_TOWER_STRIDE
                )

                if comp_start + COMPANION_MAX_DMG_OFFSET >= len(tower_values):
                    continue

                comp_level = tower_values[comp_start]
                base_start = comp_start + COMPANION_BASE_ATTR_OFFSET
                bonus_start = comp_start + COMPANION_BONUS_ATTR_OFFSET
                total_attrs: dict[Attribute, int] = {}
                for i, a in enumerate(ATTR_WIRE_ORDER):
                    total_attrs[a] = (
                        tower_values[base_start + i] + tower_values[bonus_start + i]
                    )

                comp_armor = tower_values[comp_start + COMPANION_ARMOR_OFFSET]
                comp_min_dmg = tower_values[comp_start + COMPANION_MIN_DMG_OFFSET]
                comp_max_dmg = tower_values[comp_start + COMPANION_MAX_DMG_OFFSET]

                comp_equipment = companion_equipped_items(self.session, companion_class)
                comp_runes = collect_runes(comp_equipment, companion_class.char_class)

                self.companions[companion_class] = CompanionInfo(
                    companion_class=companion_class,
                    char_class=companion_class.char_class,
                    level=comp_level,
                    total_attrs=total_attrs,
                    armor=comp_armor,
                    min_dmg=comp_min_dmg,
                    max_dmg=comp_max_dmg,
                    runes=comp_runes,
                )

    @property
    def total_attrs(self) -> dict[Attribute, int]:
        return {
            attr: self.base_attrs[attr] + self.bonus_attrs[attr] for attr in Attribute
        }

    @property
    def main_attr(self) -> Attribute:
        return self.char_class.main_attr

    @property
    def has_unlocked_companions(self) -> bool:
        return bool(self.session.login_data.get("companionequipment", ""))

    @property
    def has_life_potion(self) -> bool:
        return PotionAttributeType.HP in self.active_potion_attrs

    @property
    def is_dungeon_ready(self) -> bool:
        sizes = self.active_potion_sizes
        main_potion = PotionAttributeType(self.main_attr.value)
        return (
            self.has_life_potion
            and sizes.get(PotionAttributeType.CONSTITUTION) == PotionSize.LARGE
            and sizes.get(main_potion) == PotionSize.LARGE
        )

    @property
    def dungeon_potion_credits(self) -> dict[PotionAttributeType, int]:
        return calc_dungeon_potion_credits(
            self.potions,
            PotionAttributeType(self.main_attr.value),
            self.is_dungeon_ready,
            self.session.server_time(),
        )

    @property
    def potion_slots_full(self) -> bool:
        """True if all 3 potion buff slots are occupied."""
        return len(self.potions) == POTION_SLOT_COUNT

    @property
    def active_potion_attrs(self) -> set[PotionAttributeType]:
        """Set of Atribute for currently active (non-expired) potions."""
        return {p.potion.attr for p in self.potions}

    @property
    def active_potion_sizes(self) -> dict[PotionAttributeType, PotionSize | None]:
        """Map of active potion attr to its size."""
        return {p.potion.attr: p.potion.size for p in self.potions}

    def refresh(self) -> None:
        self.parse()

    async def kill_potion_async(self, slot: int) -> None:
        await self.session.request_and_update_async("PlayerPotionKill", str(slot))
        self.refresh()
        get_main_logger().info(f"Elixir: killed slot {slot}")

    async def ensure_potion_slot_async(
        self, main_potion_attr: PotionAttributeType
    ) -> bool:
        """Ensure there is a free potion buff slot by killing a useless one.

        Returns True if a slot is free (or was freed), or if all slots are
        essential (main/CON/HP) — same-attr replacement will work.
        """
        if not self.potion_slots_full:
            return True

        victim = self._pick_potion_to_kill(main_potion_attr)
        if not victim:
            return True

        logger = get_main_logger()
        logger.info(f"Elixir: killing {victim.potion.attr.name} slot {victim.slot}")
        await self.kill_potion_async(victim.slot)
        return True

    def _pick_potion_to_kill(
        self, main_potion_attr: PotionAttributeType
    ) -> ActivePotion | None:
        """Pick the least useful active potion to kill.

        Returns the first potion that isn't main/CON/HP, or None.
        """
        keep = {
            main_potion_attr,
            PotionAttributeType.CONSTITUTION,
            PotionAttributeType.HP,
        }
        for p in self.potions:
            if p.potion.attr not in keep:
                return p
        return None

    def show(self) -> None:
        print("=== Character Info ===")
        print(f"  Name: {self.session.player_name}")
        print(f"  Level: {self.level}")
        print(f"  Race: {self.race}")
        print(f"  Class: {self.class_name}")
        xp_pct = self.xp * 100 // self.xp_next if self.xp_next else 0
        print(f"  XP: {self.xp:,} / {self.xp_next:,} ({xp_pct}%)")
        print(f"  Honor: {self.honor:,}")
        print(f"  Rank: {self.rank:,}")
        print(f"  Armor: {self.armor:,}")
        print(f"  Damage: {self.min_dmg:,} - {self.max_dmg:,}")
        print(f"  Portal HP: {self.portal_hp_bonus}%")
        print(f"  Portal DMG: {self.portal_dmg_bonus}%")
        print(f"  Gladiator: {self.gladiator}")
        print(f"  Life potion: {self.has_life_potion}")
        mount_str = self.mount
        if self.mount_end > 0:
            local_ts = self.mount_end - self.session.server_time_diff
            mount_str += f" (until {datetime.fromtimestamp(local_ts)})"
        print(f"  Mount: {mount_str}")

        print("\n=== Attributes ===")
        for attr in ATTR_WIRE_ORDER:
            b = self.base_attrs[attr]
            bn = self.bonus_attrs[attr]
            bought = self.bought_attrs[attr]
            print(
                f"  {attr.name:<13s}: {b + bn:>7,} (base {b:>6,} + bonus {bn:>6,}) [bought {bought:,}x]"
            )

        print("\n=== Equipment Runes ===")
        r = self.runes
        if r.weapon_rune_type is not None and r.weapon_rune_value > 0:
            print(f"  Weapon: {r.weapon_rune_type.name}:{r.weapon_rune_value}")
        if r.fire_resistance:
            print(f"  {RuneType.FIRE_RES.name}:{r.fire_resistance}")
        if r.cold_resistance:
            print(f"  {RuneType.COLD_RES.name}:{r.cold_resistance}")
        if r.lightning_resistance:
            print(f"  {RuneType.LIGHTNING_RES.name}:{r.lightning_resistance}")
        if r.rune_health:
            print(f"  {RuneType.EXTRA_HP.name}:{r.rune_health}")
        if r.has_sword_of_vengeance:
            print("  Enchantment: SWORD_OF_VENGEANCE")
        if r.has_shadow_of_cowboy:
            print("  Enchantment: SHADOW_OF_COWBOY")

        print("\n=== Potions ===")
        if not self.potions:
            print("  (none)")
        for i, p in enumerate(self.potions):
            local_ts = p.expires - self.session.server_time_diff
            exp = f" (expires {datetime.fromtimestamp(local_ts)})"
            print(
                f"  Slot {i + 1}: {p.potion.attr.name}{p.potion.size.name if p.potion.size else ''} {exp}"
            )

        if self.companions:
            print("\n=== Companions ===")
            for comp in self.companions.values():
                main_attr = comp.char_class.main_attr
                main_val = comp.total_attrs[main_attr]
                con_val = comp.total_attrs[Attribute.CONSTITUTION]
                print(
                    f"  {comp.companion_class.display_name:<10s} "
                    f"({comp.char_class.name}) Lvl {comp.level}  "
                    f"{main_attr.name}={main_val:,}  CON={con_val:,}  "
                    f"Armor={comp.armor:,}  DMG={comp.min_dmg:,}-{comp.max_dmg:,}"
                )
                cr = comp.runes
                rune_parts: list[str] = []
                if cr.weapon_rune_type is not None and cr.weapon_rune_value > 0:
                    rune_parts.append(
                        f"{cr.weapon_rune_type.name}:{cr.weapon_rune_value}"
                    )
                if cr.fire_resistance:
                    rune_parts.append(f"FIRE_RES:{cr.fire_resistance}")
                if cr.cold_resistance:
                    rune_parts.append(f"COLD_RES:{cr.cold_resistance}")
                if cr.lightning_resistance:
                    rune_parts.append(f"LIGHTNING_RES:{cr.lightning_resistance}")
                if cr.rune_health:
                    rune_parts.append(f"EXTRA_HP:{cr.rune_health}")
                if cr.has_sword_of_vengeance:
                    rune_parts.append("SWORD_OF_VENGEANCE")
                if cr.has_shadow_of_cowboy:
                    rune_parts.append("SHADOW_OF_COWBOY")
                if rune_parts:
                    print(f"             Runes: {', '.join(rune_parts)}")
