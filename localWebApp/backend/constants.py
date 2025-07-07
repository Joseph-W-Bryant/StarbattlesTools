
# --- File: backend/constants.py ---
# Description: Contains all the static DATA constants for the Star Battle application.
STATE_EMPTY = 0
STATE_STAR = 1
STATE_SECONDARY_MARK = 2

SBN_B64_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
SBN_CHAR_TO_INT = {c: i for i, c in enumerate(SBN_B64_ALPHABET)}
SBN_INT_TO_CHAR = {i: c for i, c in enumerate(SBN_B64_ALPHABET)}
SBN_CODE_TO_DIM_MAP = {
    '55': 5,  '66': 6,  '77': 7,  '88': 8,  '99': 9, 'AA': 10, 'BB': 11, 'CC': 12, 'DD': 13,
    'EE': 14, 'FF': 15, 'GG': 16, 'HH': 17, 'II': 18, 'JJ': 19, 'KK': 20, 'LL': 21, 'MM': 22,
    'NN': 23, 'OO': 24, 'PP': 25
}
DIM_TO_SBN_CODE_MAP = {v: k for k, v in SBN_CODE_TO_DIM_MAP.items()}
BASE64_DISPLAY_ALPHABET = SBN_B64_ALPHABET

PUZZLE_DEFINITIONS = [
    {'dim': 5,  'stars': 1, 'difficulty': 'easy'},   # 0
    {'dim': 6,  'stars': 1, 'difficulty': 'easy'},   # 1
    {'dim': 6,  'stars': 1, 'difficulty': 'medium'}, # 2
    {'dim': 8,  'stars': 1, 'difficulty': 'medium'}, # 3
    {'dim': 8,  'stars': 1, 'difficulty': 'hard'},   # 4
    {'dim': 10, 'stars': 2, 'difficulty': 'medium'}, # 5
    {'dim': 10, 'stars': 2, 'difficulty': 'hard'},   # 6
    {'dim': 14, 'stars': 3, 'difficulty': 'medium'}, # 7
    {'dim': 14, 'stars': 3, 'difficulty': 'hard'},   # 8
    {'dim': 17, 'stars': 4, 'difficulty': 'hard'},   # 9
    {'dim': 21, 'stars': 5, 'difficulty': 'hard'},   # 10
    {'dim': 25, 'stars': 6, 'difficulty': 'hard'}    # 11
]
WEBSITE_SIZE_IDS = list(range(12))

UNIFIED_COLORS_BG = [
    ("Bright Red", (255, 204, 204)), ("Bright Green", (204, 255, 204)),
    ("Bright Yellow", (255, 255, 204)), ("Bright Blue", (204, 229, 255)),
    ("Bright Magenta", (255, 204, 255)), ("Bright Cyan", (204, 255, 255)),
    ("Light Orange", (255, 229, 204)), ("Light Purple", (229, 204, 255)),
    ("Light Gray", (224, 224, 224)), ("Mint", (210, 240, 210)),
]
