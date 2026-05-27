# ── gttime ───────────────────────────────────────────────────────────────────
GT_TIME_START_INDEX = 0
GT_TIME_END_INDEX = 1   # overall event end (e.g. 4-day window)

# ── gtraidfights ─────────────────────────────────────────────────────────────
GT_RAID_DAILY_START_INDEX = 0
GT_RAID_DAILY_END_INDEX = 1

# ── gtsave ───────────────────────────────────────────────────────────────────
GT_CARDS_AVAILABLE_INDEX = 0
GT_FLOOR_INDEX = 3
GT_JOIN_TS_INDEX = 5

# ── gtdailyreward / gtdailyrewardyesterday ───────────────────────────────────
# Format: [tier_start][tier_end][item0_qty][item1_qty]...[item7_qty]
# First two fields are tier indices; items start at index 2.
# Reward is claimable when any item value in [2:10] is non-zero.
DAILY_REWARD_ITEMS_START = 2
DAILY_REWARD_ITEMS_END = 10
