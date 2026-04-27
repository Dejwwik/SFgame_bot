from sfbot.constants import (
    ITEM_FIELD_COUNT,
    ITEM_FIELD_ENCHANTMENT,
    ITEM_FIELD_TYPE,
    VALUES_DELIMITER,
    CompanionClass,
    Enchantment,
    EquipmentSlot,
)
from sfbot.exceptions import APIError
from sfbot.logging import get_main_logger
from sfbot.session import GameSession

ENCHANT_SLOT: dict[Enchantment, EquipmentSlot] = {
    Enchantment.ARCHAEOLOGICAL_AURA: EquipmentSlot.HAT,
    Enchantment.MARIOS_BEARD: EquipmentSlot.BREASTPLATE,
    Enchantment.SHADOW_OF_COWBOY: EquipmentSlot.GLOVES,
    Enchantment.MANY_FEET_BOOTS: EquipmentSlot.FOOTWEAR,
    Enchantment.UNHOLY_ACQUISITIVENESS: EquipmentSlot.AMULET,
    Enchantment.THIRSTY_WANDERER: EquipmentSlot.BELT,
    Enchantment.GRAVE_ROBBERS_PRAYER: EquipmentSlot.RING,
    Enchantment.ROBBER_BARON_RITUAL: EquipmentSlot.TALISMAN,
    Enchantment.SWORD_OF_VENGEANCE: EquipmentSlot.WEAPON,
}

SLOT_ENCHANT: dict[EquipmentSlot, Enchantment] = {v: k for k, v in ENCHANT_SLOT.items()}


def read_slot_enchant(vals: list[int], slot_idx: int) -> int | None:
    """Read enchantment ID at slot_idx. Returns None if slot is empty (no item)."""
    off = slot_idx * ITEM_FIELD_COUNT
    if off + ITEM_FIELD_COUNT > len(vals):
        return None
    item_type = vals[off + ITEM_FIELD_TYPE] & 0xFF
    if item_type == 0:
        return None
    return vals[off + ITEM_FIELD_ENCHANTMENT]


class Witch:
    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.parse()

    def parse(self) -> None:
        data = self.session.login_data.get("witchshop", "").split(VALUES_DELIMITER)
        vals = [int(x) for x in data if x]

        self.enchantment_price: int = vals[35] if len(vals) > 35 else 0
        self.enchant_count: int = vals[4] if len(vals) > 4 else 0

        self.available_enchants: dict[Enchantment, int] = {}
        for i in range(self.enchant_count):
            idx = 6 + 3 * i
            if idx < len(vals):
                self.available_enchants[Enchantment(vals[idx])] = i + 1

    def refresh(self) -> None:
        self.parse()

    def missing_enchantments(
        self,
    ) -> list[tuple[Enchantment, EquipmentSlot, int, CompanionClass | None]]:
        raw_main = self.session.login_data.get("ownplayersaveequipment", "").split(
            VALUES_DELIMITER
        )
        main_vals = [int(x) for x in raw_main if x]

        raw_comp = self.session.login_data.get("companionequipment", "").split(
            VALUES_DELIMITER
        )
        comp_vals = [int(x) for x in raw_comp if x]

        missing: list[
            tuple[Enchantment, EquipmentSlot, int, CompanionClass | None]
        ] = []

        # Main character: all 9 enchantments
        for enchant, equip_slot in ENCHANT_SLOT.items():
            if enchant not in self.available_enchants:
                continue
            eid = read_slot_enchant(main_vals, equip_slot.value - 1)
            if eid is None:
                continue
            if eid != 0:
                continue
            missing.append(
                (enchant, equip_slot, self.available_enchants[enchant], None)
            )

        # Companions: weapon + gloves
        companion_enchants: dict[Enchantment, EquipmentSlot] = {
            Enchantment.SWORD_OF_VENGEANCE: EquipmentSlot.WEAPON,
            Enchantment.SHADOW_OF_COWBOY: EquipmentSlot.GLOVES,
        }
        for companion in CompanionClass:
            base = companion.value * len(EquipmentSlot)
            for enchant, equip_slot in companion_enchants.items():
                if enchant not in self.available_enchants:
                    continue
                slot_idx = base + equip_slot.value - 1
                eid = read_slot_enchant(comp_vals, slot_idx)
                if eid is None:
                    continue
                if eid != 0:
                    continue
                missing.append(
                    (
                        enchant,
                        equip_slot,
                        self.available_enchants[enchant],
                        companion,
                    )
                )

        return missing

    @property
    def is_completed(self) -> bool:
        return not self.missing_enchantments()

    async def buy_all_missing_async(self) -> None:
        logger = get_main_logger()
        for enchant, equip_slot, ident, companion in self.missing_enchantments():
            section = companion.wire_section if companion is not None else 1
            try:
                await self.session.request_and_update_async(
                    "PlayerWitchEnchantItem", f"{ident}/{section}"
                )
                self.refresh()
                suffix = (
                    companion.display_name
                    if companion is not None
                    else self.session.player_name
                )
                logger.info(
                    f"Enchant: bought {enchant.name} ({equip_slot.name}) for {suffix}"
                )
            except APIError as exc:
                logger.warning(f"Enchant: {enchant.name} failed: {exc}")
                return

    def status(self) -> None:
        print("\n=== Witch Shop ===")
        print(f"  Enchantment price: {self.enchantment_price:,}")
        print(f"  Available enchantments: {self.enchant_count}")

        missing = self.missing_enchantments()
        missing_enchants = {(m[0], m[3]) for m in missing}
        for enchant, equip_slot in ENCHANT_SLOT.items():
            if (enchant, None) in missing_enchants:
                status = "MISSING"
            elif enchant in self.available_enchants:
                status = "OWNED"
            else:
                status = "Locked"
            print(f"    {enchant.name} ({equip_slot.name}): {status}")
