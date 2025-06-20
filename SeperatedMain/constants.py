# constants.py
# Description: Contains all the static constants for the Star Battle application.

# --- UI Constants ---
GRID_AREA_WIDTH = 600
GRID_AREA_HEIGHT = 600
PANEL_WIDTH = 250
WINDOW_WIDTH = GRID_AREA_WIDTH + PANEL_WIDTH
WINDOW_HEIGHT = GRID_AREA_HEIGHT
GUTTER = 5
BORDER_NORMAL = 1
BORDER_THICK = 4

# --- Colors ---
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRID_LINES = (200, 200, 200)
COLOR_STAR = (255, 200, 0)
COLOR_X = (40, 40, 40)
COLOR_DOT = (150, 150, 150)
COLOR_PANEL = (50, 50, 60)
COLOR_BUTTON = (80, 80, 90)
COLOR_BUTTON_HOVER = (110, 110, 120)
COLOR_BUTTON_TEXT = (220, 220, 220)
COLOR_CORRECT = (0, 200, 0)
COLOR_INCORRECT = (200, 0, 0)
COLOR_SELECTED = (100, 180, 255)
COLOR_STAR_NUM = (200, 0, 0)
COLOR_DISABLED_BUTTON = (60, 60, 70)
COLOR_DISABLED_TEXT = (100, 100, 110)

DIFFICULTY_COLORS = {
    'easy':   {'base': (70, 160, 70),  'hover': (90, 190, 90)},
    'medium': {'base': (180, 140, 50), 'hover': (210, 170, 70)},
    'hard':   {'base': (180, 70, 70),  'hover': (210, 90, 90)}
}

# --- Data Constants ---
UNIFIED_COLORS_BG = [
    ("Bright Red",(255,204,204),"\033[48;2;255;204;204m\033[38;2;0;0;0m"),("Bright Green",(204,255,204),"\033[48;2;204;255;204m\033[38;2;0;0;0m"),
    ("Bright Yellow",(255,255,204),"\033[48;2;255;255;204m\033[38;2;0;0;0m"),("Bright Blue",(204,229,255),"\033[48;2;204;229;255m\033[38;2;0;0;0m"),
    ("Bright Magenta",(255,204,255),"\033[48;2;255;204;255m\033[38;2;0;0;0m"),("Bright Cyan",(204,255,255),"\033[48;2;204;255;255m\033[38;2;0;0;0m"),
    ("Light Orange",(255,229,204),"\033[48;2;255;229;204m\033[38;2;0;0;0m"),("Light Purple",(229,204,255),"\033[48;2;229;204;255m\033[38;2;0;0;0m"),
    ("Light Gray",(224,224,224),"\033[48;2;224;224;224m\033[38;2;0;0;0m"),("Mint",(210,240,210),"\033[48;2;210;240;210m\033[38;2;0;0;0m"),
    ("Peach",(255,218,185),"\033[48;2;255;218;185m\033[38;2;0;0;0m"),("Sky Blue",(173,216,230),"\033[48;2;173;216;230m\033[38;2;0;0;0m"),
]
PYGAME_UNIFIED_COLORS = [(c[0], c[1]) for c in UNIFIED_COLORS_BG]

# --- Game State Constants ---
STATE_EMPTY = 0
STATE_STAR = 1
STATE_SECONDARY_MARK = 2

# --- Universal SBN Conversion Constants ---
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

# --- Website Puzzle Definitions ---
PUZZLE_DEFINITIONS = [
    {'dim': 5,  'stars': 1, 'difficulty': 'easy'},   {'dim': 6,  'stars': 1, 'difficulty': 'easy'},
    {'dim': 6,  'stars': 1, 'difficulty': 'medium'}, {'dim': 8,  'stars': 1, 'difficulty': 'medium'},
    {'dim': 8,  'stars': 1, 'difficulty': 'hard'},   {'dim': 10, 'stars': 2, 'difficulty': 'medium'},
    {'dim': 10, 'stars': 2, 'difficulty': 'hard'},   {'dim': 14, 'stars': 3, 'difficulty': 'medium'},
    {'dim': 14, 'stars': 3, 'difficulty': 'hard'},   {'dim': 17, 'stars': 4, 'difficulty': 'hard'},
    {'dim': 21, 'stars': 5, 'difficulty': 'hard'},   {'dim': 25, 'stars': 6, 'difficulty': 'hard'}
]
WEBSITE_SIZE_IDS = list(range(12))

