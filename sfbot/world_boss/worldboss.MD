# World Boss

Timed server event where all players cooperate to damage a world boss. The boss fights
automatically — the player's role is managing the catapult (temporary, breaks after N hours),
buying upgrades, loading projectiles, and collecting reward chests.

Currency: **catalysts** (earned from attacks, used for catapult + projectiles).

## Wire Data Keys

| Key | Description |
|---|---|
| `eventstatus` | Event schedule: type, theme, start_ts, end_ts, extra_end_ts |
| `wbcharacter` | Player's WB state: catalysts, segment, battle reward chests, etc. |
| `wbupgrade` | Catapult break timestamp + 4 upgrade slots (4 fields each) |
| `wbupgradestore` | 3 catapult upgrade offers (7 fields each) |
| `wbammostore` | 3 projectile offers with small/large options (6 fields each) |
| `wbammo` | Currently loaded projectile (type, amount, extra_dmg) |
| `wbtower` | Tower segments: boss HP, hero rankings per segment |
| `wbdailychests` | Daily chest availability (4 values) |
| `wbrankingworldmax` | Max world ranking entries |
| `wbrankingfightermax` | Max fighter ranking entries |
| `wbrankinginternationalmax` | Max international ranking entries |

## eventstatus Layout

```
eventstatus:event_type/theme/event_start/event_end/extra_end
```

| Index | Field |
|---|---|
| 0 | Event type (1=LegendaryDungeon, 2=Hellevator, 4=TravelingCircus, **6=WorldBoss**) |
| 1 | Theme (WorldBoss: 1=Normal, 2=Winter) |
| 2 | Event start timestamp |
| 3 | Event end timestamp |
| 4 | Extra end / next event timestamp |

`is_active` checks `event_start <= now < event_end` from `eventstatus`.

## wbcharacter Layout

```
wbcharacter:catalysts/medals/rank/segment/unk4/attack_timer/dmg_per_atk/unk7/unk8/dmg_per_hour/loot_per_hour/dmg_comparative/battle_chests/unk13/next_loot_issued
```

| Index | Field |
|---|---|
| 0 | Catalysts (currency for catapult + projectiles) |
| 3 | Current segment (1=Top, 2=Middle, 3=Bottom) |
| 5 | Attack timer timestamp |
| 6 | Damage per attack |
| 9 | Damage per hour |
| 12 | Battle reward chests (uncollected) |
| 14 | Next battle loot issued timestamp |

## wbupgrade Layout

```
wbupgrade:break_ts/typ1/restrict1/amount1/effect1/typ2/restrict2/amount2/effect2/...
```

| Index | Field |
|---|---|
| 0 | Catapult break timestamp (0 = no catapult) |
| 1-4 | Upgrade slot 1: type, restriction, amount (0-10), effect |
| 5-8 | Upgrade slot 2 |
| 9-12 | Upgrade slot 3 |
| 13-16 | Upgrade slot 4 |

Upgrade types: 1=Motor (damage), 2=Thread (shot speed), 3=AimingDevice (crit chance), 4=Bowl (crit damage).
Restriction: tower segment the upgrade applies to (0 = all segments).

Catapult is **temporary** — it breaks after a timer. Buy a new one with `WorldBossUpgradeUnlock:{hours}` (1-10h, costs catalysts = hours).

## wbupgradestore Layout

3 items × 7 fields each:

| Field offset | Description |
|---|---|
| 0 | Upgrade type (1=Motor, 2=Thread, 3=AimingDevice, 4=Bowl) |
| 1 | Segment restriction (0 = none) |
| 2 | Effect value |
| 3 | Raw main currency price (scales with remaining catapult time) |
| 4 | Currency type |
| 5 | Raw catalyst price (scales with remaining catapult time) |
| 6 | Raw mushroom price |

## wbammostore Layout

3 items × 6 fields each:

| Field offset | Description |
|---|---|
| 0 | Projectile type (1=Impacting, 2=Biting, 3=Mangling) |
| 1 | Small purchase amount |
| 2 | Large purchase amount |
| 3 | Effect value (extra damage %) |
| 4 | Small purchase catalyst price |
| 5 | Large purchase catalyst price |

## wbammo Layout

```
wbammo:type/amount/extra_dmg
```

Single currently loaded projectile (not an array of counts).

## Wire Commands

| Command | Params | Description |
|---|---|---|
| `WorldBossEnter` | (none) | Enter WB screen, loads all WB data |
| `WorldBossEventPoll` | (none) | Poll/update attack state |
| `WorldBossOpenChest` | `0` or `1` | `0` = collect battle rewards, `1` = collect daily chests |
| `WorldBossChangeLevel` | `segment` (1/2/3) | Switch segment: 1=Top, 2=Middle, 3=Bottom |
| `WorldBossUpgradeUnlock` | `hours` (1-10) | Buy catapult (costs catalysts = hours) |
| `WorldBossUpgradeDestroy` | (none) | Destroy current catapult |
| `WorldBossUpgradeBuy` | `slot/payment` | Buy upgrade (slot 1-3, payment: 1=main, 2=mushrooms) |
| `WorldBossAmmoBuy` | `slot/size` | Buy projectile (slot 1-3, size: 1=small, 2=large) |
| `WorldBossRankingWorldRewards` | (none) | View world ranking rewards (read-only) |
| `WorldBossLogDayInfos` | `day` (0-based) | View attack log for a day (read-only) |

## Bot Task Flow

1. First cycle: `WorldBossEnter` — discovers if event is active
2. If event not active → skip all future cycles until next login
3. Subsequent cycles: check `is_active` first, then `WorldBossEnter` to refresh
4. Collect daily chests (`WorldBossOpenChest:1`) if any available
5. Collect battle reward chests (`WorldBossOpenChest:0`) if any pending
6. Buy catapult if missing/broken (`WorldBossUpgradeUnlock:{hours}`, max affordable)
7. Buy all 3 upgrade store slots if catapult active (`WorldBossUpgradeBuy`)
8. Buy projectile if none equipped (`WorldBossAmmoBuy`)
9. Boss fights automatically — no player action needed

**Note**: `wbcharacter` and `eventstatus` may not be in the normal login response.
The bot enters once per login session to discover event data, then uses cached
`event_end` for subsequent `should_run` checks.
