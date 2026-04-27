# --- Pet limits ---
PETS_PER_HABITAT = 20
PET_TOTAL_COUNT = 100
PET_FEED_LIMIT_NORMAL = 3
PET_FEED_LIMIT_EVENT = 9

# --- Pet feeding priority (0-based position within habitat) ---
# CHRONOLOGICAL STRATEGY:
# 1. Start with Index 0/1 (Starter)
# 2. Unlock & Switch to Bridge Pet
# 3. Unlock & Switch to Final Boss Killer (Index 17-19)
PET_HABITAT_PRIORITY: dict[int, list[int]] = {
    # Shadow: Toothey (2) -> Cuckooly (11) -> Luchtablong (16) -> Poisnake (19)
    0: [2, 11, 16, 19],
    # Light: Jellclops (1) -> Birdychirp (12) -> Knilight (17) -> Unikor (19)
    1: [1, 12, 17, 19],
    # Earth: Smaponyck (2) -> Redwoofox (12) -> Armoruck (16) -> Mouthrexor (19)
    2: [2, 12, 16, 19],
    # Fire: Pyrophibus (2) -> Matchlit (10) -> Mantiflame (15) -> Devastor (19)
    3: [2, 10, 15, 19],
    # Water: Ocodile (2) -> Ewilgryn (9) -> Watnake (15) -> Hydrospir (19)
    4: [2, 9, 15, 19],
}
# Per-habitat feed priority for phase 2 (to level 200).
# Used when ALL pets are unlocked — feed from strongest to weakest.
PET_HABITAT_PRIORITY_200: list[int] = list(range(19, -1, -1))
