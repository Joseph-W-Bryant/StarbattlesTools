# 3starbattles_player_with_solver.py (Final Polished Version with Universal SBN Conversion and Feedback)

# --- Silence Pygame messages and warnings ---
import os
import warnings

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
warnings.filterwarnings("ignore", category=RuntimeWarning, message="Your system is avx2 capable but pygame was not built with support for it.*")
warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources is deprecated as an API.*")
# --- End of silencing code ---

import pygame
import requests
import re
import sys
import math
import hashlib
import time
from collections import deque, defaultdict

# --- Z3 Solver Integration ---
Z3_AVAILABLE = False
try:
    from z3 import Solver, Bool, PbEq, Implies, And, Not, Or, sat
    Z3_AVAILABLE = True
    print("Z3 solver library found and enabled.")
except ImportError:
    print("Warning: 'z3-solver' library not found. The 'Find Solution' button will be disabled.")
    print("To enable it, run: pip install z3-solver")

# --- UI Constants ---
GRID_AREA_WIDTH = 600; GRID_AREA_HEIGHT = 600
PANEL_WIDTH = 250; WINDOW_WIDTH = GRID_AREA_WIDTH + PANEL_WIDTH; WINDOW_HEIGHT = GRID_AREA_HEIGHT
GUTTER = 5; BORDER_NORMAL = 1; BORDER_THICK = 4

# --- Colors ---
COLOR_WHITE = (255, 255, 255); COLOR_BLACK = (0, 0, 0); COLOR_GRID_LINES = (200, 200, 200)
COLOR_STAR = (255, 200, 0); COLOR_X = (40, 40, 40); COLOR_DOT = (150, 150, 150)
COLOR_PANEL = (50, 50, 60); COLOR_BUTTON = (80, 80, 90); COLOR_BUTTON_HOVER = (110, 110, 120)
COLOR_BUTTON_TEXT = (220, 220, 220); COLOR_CORRECT = (0, 200, 0); COLOR_INCORRECT = (200, 0, 0)
COLOR_SELECTED = (100, 180, 255); COLOR_STAR_NUM = (200, 0, 0)
COLOR_DISABLED_BUTTON = (60, 60, 70); COLOR_DISABLED_TEXT = (100, 100, 110)

DIFFICULTY_COLORS = {
    'easy':   {'base': (70, 160, 70),  'hover': (90, 190, 90)},
    'medium': {'base': (180, 140, 50), 'hover': (210, 170, 70)},
    'hard':   {'base': (180, 70, 70),  'hover': (210, 90, 90)}
}

UNIFIED_COLORS_BG = [
    ("Bright Red",(255,204,204),"\033[48;2;255;204;204m\033[38;2;0;0;0m"),("Bright Green",(204,255,204),"\033[48;2;204;255;204m\033[38;2;0;0;0m"),
    ("Bright Yellow",(255,255,204),"\033[48;2;255;255;204m\033[38;2;0;0;0m"),("Bright Blue",(204,229,255),"\033[48;2;204;229;255m\033[38;2;0;0;0m"),
    ("Bright Magenta",(255,204,255),"\033[48;2;255;204;255m\033[38;2;0;0;0m"),("Bright Cyan",(204,255,255),"\033[48;2;204;255;255m\033[38;2;0;0;0m"),
    ("Light Orange",(255,229,204),"\033[48;2;255;229;204m\033[38;2;0;0;0m"),("Light Purple",(229,204,255),"\033[48;2;229;204;255m\033[38;2;0;0;0m"),
    ("Light Gray",(224,224,224),"\033[48;2;224;224;224m\033[38;2;0;0;0m"),("Mint",(210,240,210),"\033[48;2;210;240;210m\033[38;2;0;0;0m"),
    ("Peach",(255,218,185),"\033[48;2;255;218;185m\033[38;2;0;0;0m"),("Sky Blue",(173,216,230),"\033[48;2;173;216;230m\033[38;2;0;0;0m"),
]
PYGAME_UNIFIED_COLORS = [(c[0], c[1]) for c in UNIFIED_COLORS_BG]

STATE_EMPTY = 0; STATE_STAR = 1; STATE_SECONDARY_MARK = 2

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

PUZZLE_DEFINITIONS = [
    {'dim': 5,  'stars': 1, 'difficulty': 'easy'},   {'dim': 6,  'stars': 1, 'difficulty': 'easy'},
    {'dim': 6,  'stars': 1, 'difficulty': 'medium'}, {'dim': 8,  'stars': 1, 'difficulty': 'medium'},
    {'dim': 8,  'stars': 1, 'difficulty': 'hard'},   {'dim': 10, 'stars': 2, 'difficulty': 'medium'},
    {'dim': 10, 'stars': 2, 'difficulty': 'hard'},   {'dim': 14, 'stars': 3, 'difficulty': 'medium'},
    {'dim': 14, 'stars': 3, 'difficulty': 'hard'},   {'dim': 17, 'stars': 4, 'difficulty': 'hard'},
    {'dim': 21, 'stars': 5, 'difficulty': 'hard'},   {'dim': 25, 'stars': 6, 'difficulty': 'hard'}
]
WEBSITE_SIZE_IDS = list(range(12))

def get_puzzle_from_website(size_selection):
    url = "https://www.puzzle-star-battle.com/"
    website_size_id = WEBSITE_SIZE_IDS[size_selection]
    if website_size_id != 0: url += f"?size={website_size_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    print(f"\nFetching puzzle data from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10); response.raise_for_status()
        task_match = re.search(r"var task = '([^']+)';", response.text)
        hash_match = re.search(r"hashedSolution: '([^']+)'", response.text)
        if task_match and hash_match:
            print("Successfully extracted puzzle data.")
            return {'task': task_match.group(1), 'solution_hash': hash_match.group(1)}
        print("Error: Could not find required puzzle data."); return None
    except requests.RequestException as e:
        print(f"Error: Could not fetch puzzle data. {e}"); return None

def reconstruct_grid_from_borders(dim, vertical_bits, horizontal_bits):
    region_grid = [[0] * dim for _ in range(dim)]
    region_id = 1
    for r_start in range(dim):
        for c_start in range(dim):
            if region_grid[r_start][c_start] == 0:
                q = deque([(r_start, c_start)])
                region_grid[r_start][c_start] = region_id
                while q:
                    r, c = q.popleft()
                    if c < dim - 1 and region_grid[r][c+1] == 0 and vertical_bits[r*(dim-1) + c] == '0': region_grid[r][c+1] = region_id; q.append((r, c+1))
                    if c > 0 and region_grid[r][c-1] == 0 and vertical_bits[r*(dim-1) + (c-1)] == '0': region_grid[r][c-1] = region_id; q.append((r, c-1))
                    if r < dim - 1 and region_grid[r+1][c] == 0 and horizontal_bits[c*(dim-1) + r] == '0': region_grid[r+1][c] = region_id; q.append((r+1, c))
                    if r > 0 and region_grid[r-1][c] == 0 and horizontal_bits[c*(dim-1) + (r-1)] == '0': region_grid[r-1][c] = region_id; q.append((r-1, c))
                region_id += 1
    return region_grid

def decode_sbn(sbn_string):
    try:
        size_code = sbn_string[0:2]
        dim = SBN_CODE_TO_DIM_MAP.get(size_code)
        if not dim: raise ValueError(f"Unknown SBN size code '{size_code}'")
        stars = int(sbn_string[2])
        is_annotated = sbn_string[3] == 'e'
        
        border_bits_needed = 2 * dim * (dim - 1)
        padding_bits = (math.ceil(border_bits_needed / 6) * 6) - border_bits_needed
        border_chars_needed = math.ceil(border_bits_needed / 6)
        region_data_str = sbn_string[4 : 4 + border_chars_needed]
        
        full_bitfield = "".join(bin(SBN_CHAR_TO_INT[char])[2:].zfill(6) for char in region_data_str)
        border_data = full_bitfield[padding_bits:]

        num_single_direction_borders = dim * (dim - 1)
        vertical_bits = border_data[0 : num_single_direction_borders]
        horizontal_bits = border_data[num_single_direction_borders : border_bits_needed]
            
        region_grid = reconstruct_grid_from_borders(dim, vertical_bits, horizontal_bits)
        task_string = ",".join(str(cell) for row in region_grid for cell in row)
        
        decoded_player_grid = None
        if is_annotated:
            annotation_data_str = sbn_string[4 + border_chars_needed:]
            if annotation_data_str:
                player_grid = [[STATE_EMPTY] * dim for _ in range(dim)]
                flat_indices = [(r, c) for r in range(dim) for c in range(dim)]
                sbn_to_game_state = {0: STATE_EMPTY, 1: STATE_SECONDARY_MARK, 2: STATE_STAR}
                char_cursor, cell_cursor = 0, 0
                if dim in [10, 11]:
                    value = int(annotation_data_str[0])
                    player_grid[0][0] = sbn_to_game_state.get(value, STATE_EMPTY)
                    char_cursor, cell_cursor = 1, 1
                while cell_cursor < dim * dim and char_cursor < len(annotation_data_str):
                    char = annotation_data_str[char_cursor]
                    value = SBN_CHAR_TO_INT.get(char, 0)
                    states = [value // 16, (value % 16) // 4, value % 4]
                    for i in range(3):
                        if cell_cursor + i < dim * dim:
                            r, c = flat_indices[cell_cursor + i]
                            player_grid[r][c] = sbn_to_game_state.get(states[i], STATE_EMPTY)
                    cell_cursor += 3
                    char_cursor += 1
                decoded_player_grid = player_grid
        return {'task': task_string, 'solution_hash': None, 'stars': stars, 'player_grid': decoded_player_grid}
    except (KeyError, IndexError, ValueError) as e:
        print(f"--- SBN DECODING FAILED ---"); print(f"Error: {e}"); return None

# --- UPGRADED: SBN Encoder now supports annotations ---
def encode_to_sbn(region_grid, stars, player_grid=None):
    """
    Encodes a grid to SBN. If player_grid is provided, it includes annotations.
    """
    dim = len(region_grid)
    sbn_code = DIM_TO_SBN_CODE_MAP.get(dim)
    if not sbn_code: return None

    # Part 1: Encode Region Data (same as before)
    vertical_bits = ['1' if region_grid[r][c] != region_grid[r][c+1] else '0' for r in range(dim) for c in range(dim - 1)]
    horizontal_bits = ['1' if region_grid[r][c] != region_grid[r+1][c] else '0' for c in range(dim) for r in range(dim - 1)]
    clean_bitfield = "".join(vertical_bits) + "".join(horizontal_bits)
    
    total_bits_needed = len(clean_bitfield)
    padding_bits = (math.ceil(total_bits_needed / 6) * 6) - total_bits_needed
    padded_bitfield = ('0' * padding_bits) + clean_bitfield
    
    region_data_chars = [SBN_INT_TO_CHAR[int(padded_bitfield[i:i+6], 2)] for i in range(0, len(padded_bitfield), 6)]
    region_data = "".join(region_data_chars)

    # Part 2: Encode Annotation Data (if player_grid is provided)
    annotation_data = ""
    flag = 'W'
    if player_grid:
        flag = 'e'
        game_to_sbn_state = {STATE_EMPTY: 0, STATE_SECONDARY_MARK: 1, STATE_STAR: 2}
        flat_states = [game_to_sbn_state.get(player_grid[r][c], 0) for r in range(dim) for c in range(dim)]
        
        sbn_states = []
        if dim in [10, 11]: # Handle special case
            sbn_states.append(str(flat_states[0]))
            flat_states = flat_states[1:]

        for i in range(0, len(flat_states), 3):
            chunk = flat_states[i:i+3]
            while len(chunk) < 3: chunk.append(0) # Pad with empty state
            s1, s2, s3 = chunk
            value = s1 * 16 + s2 * 4 + s3
            sbn_states.append(SBN_INT_TO_CHAR[value])
        annotation_data = "".join(sbn_states)

    return f"{sbn_code}{stars}{flag}{region_data}{annotation_data}"

def parse_and_validate_grid(task_string):
    if not task_string: return None, None
    try:
        numbers = [int(n) for n in task_string.split(',')]; total_cells = len(numbers)
        if total_cells == 0: return None, None
        dimension = int(math.sqrt(total_cells))
        if dimension * dimension != total_cells: return None, None
        grid = [numbers[i*dimension:(i+1)*dimension] for i in range(dimension)]
        return grid, dimension
    except (ValueError, TypeError): return None, None

def display_terminal_grid(grid, title, content_grid=None):
    if not grid: return
    RESET = "\033[0m"; print(f"\n--- {title} ---")
    dim = len(grid)
    for r in range(dim):
        colored_chars = []
        for c in range(dim):
            region_num = grid[r][c]
            if region_num > 0:
                color_ansi = UNIFIED_COLORS_BG[(region_num - 1) % len(UNIFIED_COLORS_BG)][2]
                symbol = '★' if content_grid and content_grid[r][c] == 1 else ('X' if content_grid and content_grid[r][c] == 2 else BASE64_DISPLAY_ALPHABET[(region_num - 1) % len(BASE64_DISPLAY_ALPHABET)])
                colored_chars.append(f"{color_ansi} {symbol} {RESET}")
            else:
                colored_chars.append(" ? ")
        print("".join(colored_chars))
    print("-----------------\n")

def reset_game_state(puzzle_data):
    if not puzzle_data or 'task' not in puzzle_data: return None, None, None, None, None, None
    region_grid, dimension = parse_and_validate_grid(puzzle_data['task'])
    if region_grid:
        display_terminal_grid(region_grid, "Terminal Symbol Display")
        stars = puzzle_data.get('stars', 1)
        if puzzle_data.get('player_grid'):
            player_grid = puzzle_data['player_grid']
        else:
            player_grid = [[STATE_EMPTY] * dimension for _ in range(dimension)]
        cell_size = GRID_AREA_WIDTH / dimension
        return region_grid, puzzle_data, player_grid, dimension, cell_size, stars
    return None, None, None, None, None, None

def calculate_star_points(center_x, center_y, outer_radius, inner_radius):
    points = [];
    for i in range(10):
        angle = math.pi / 5 * i - math.pi / 2; radius = outer_radius if i % 2 == 0 else inner_radius
        points.append((center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
    return points

def check_solution(player_grid, puzzle_data):
    if not puzzle_data or 'solution_hash' not in puzzle_data or not puzzle_data['solution_hash']: return False
    yn_string = "".join(['y' if cell == STATE_STAR else 'n' for row in player_grid for cell in row])
    string_to_hash = puzzle_data['task'] + yn_string
    calculated_hash = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()
    is_correct = calculated_hash == puzzle_data['solution_hash']
    print(f"Calculated Hash: {calculated_hash}\nExpected Hash:   {puzzle_data['solution_hash']}")
    if is_correct: print("\033[92m--> Solution is CORRECT!\033[0m")
    else: print("\033[91m--> Solution is INCORRECT.\033[0m")
    return is_correct

# Drawing functions remain unchanged
def draw_background_colors(screen, region_grid, cell_size):
    dim = len(region_grid)
    for r in range(dim):
        for c in range(dim):
            rect = pygame.Rect(c * cell_size, r * cell_size, cell_size, cell_size)
            if region_grid[r][c] > 0:
                pygame.draw.rect(screen, PYGAME_UNIFIED_COLORS[(region_grid[r][c] - 1) % len(PYGAME_UNIFIED_COLORS)][1], rect)
def draw_grid_lines(screen, region_grid, cell_size):
    dim = len(region_grid)
    for i in range(dim + 1):
        pygame.draw.line(screen, COLOR_GRID_LINES, (i * cell_size, 0), (i * cell_size, GRID_AREA_HEIGHT), BORDER_NORMAL)
        pygame.draw.line(screen, COLOR_GRID_LINES, (0, i * cell_size), (GRID_AREA_WIDTH, i * cell_size), BORDER_NORMAL)
    for r in range(dim):
        for c in range(dim):
            if c < dim - 1 and region_grid[r][c] > 0 and region_grid[r][c+1] > 0 and region_grid[r][c] != region_grid[r][c+1]:
                pygame.draw.line(screen, COLOR_BLACK, ((c + 1) * cell_size, r * cell_size), ((c + 1) * cell_size, (r + 1) * cell_size), BORDER_THICK)
            if r < dim - 1 and region_grid[r][c] > 0 and region_grid[r+1][c] > 0 and region_grid[r][c] != region_grid[r+1][c]:
                pygame.draw.line(screen, COLOR_BLACK, (c * cell_size, (r + 1) * cell_size), ((c + 1) * cell_size, (r + 1) * cell_size), BORDER_THICK)
    pygame.draw.rect(screen, COLOR_BLACK, (0, 0, GRID_AREA_WIDTH, GRID_AREA_HEIGHT), BORDER_THICK)
def draw_player_marks(screen, player_grid, mark_is_x, cell_size):
    dim = len(player_grid)
    for r in range(dim):
        for c in range(dim):
            cell_state = player_grid[r][c]; center_x = c * cell_size + cell_size // 2; center_y = r * cell_size + cell_size // 2
            if cell_state == STATE_STAR:
                outer_rad = cell_size / 2 - GUTTER * 1.5; inner_rad = outer_rad / 2
                pygame.draw.polygon(screen, COLOR_STAR, calculate_star_points(center_x, center_y, outer_rad, inner_rad))
            elif cell_state == STATE_SECONDARY_MARK:
                if mark_is_x:
                    margin = GUTTER * 2.5; line_width = max(1, int(cell_size / 15))
                    pygame.draw.line(screen, COLOR_X, (c * cell_size + margin, r * cell_size + margin), ((c+1) * cell_size - margin, (r+1) * cell_size - margin), line_width)
                    pygame.draw.line(screen, COLOR_X, ((c+1) * cell_size - margin, r * cell_size + margin), (c * cell_size + margin, (r+1) * cell_size - margin), line_width)
                else:
                    pygame.draw.circle(screen, COLOR_DOT, (center_x, center_y), cell_size / 6)
def draw_star_indicator(screen, rect, count, font):
    star_radius = 12
    center_x = rect.right - star_radius + 5; center_y = rect.top + star_radius - 8
    star_points = calculate_star_points(center_x, center_y, star_radius, star_radius/2)
    pygame.draw.polygon(screen, COLOR_STAR, star_points)
    num_surf = font.render(str(count), True, COLOR_STAR_NUM)
    screen.blit(num_surf, num_surf.get_rect(center=(center_x, center_y + 1)))
def draw_control_panel(screen, font, small_font, tiny_font, buttons, size_buttons, current_size_selection, mark_is_x, solution_status, puzzle_data_exists, last_button_y):
    pygame.draw.rect(screen, COLOR_PANEL, (GRID_AREA_WIDTH, 0, PANEL_WIDTH, WINDOW_HEIGHT))
    mouse_pos = pygame.mouse.get_pos()
    buttons['toggle']['text'] = "Mode: Xs" if mark_is_x else "Mode: Dots"
    for name, b in buttons.items():
        is_disabled = (name == 'check' and not puzzle_data_exists) or \
                      (name == 'find' and not Z3_AVAILABLE)
        color = COLOR_DISABLED_BUTTON if is_disabled else (COLOR_BUTTON_HOVER if b['rect'].collidepoint(mouse_pos) else COLOR_BUTTON)
        pygame.draw.rect(screen, color, b['rect'], border_radius=8)
        text_color = COLOR_DISABLED_TEXT if is_disabled else COLOR_BUTTON_TEXT
        text_surf = font.render(b['text'], True, text_color)
        screen.blit(text_surf, text_surf.get_rect(center=b['rect'].center))
    
    title_y = last_button_y + 40
    title_surf = font.render("Board Size", True, COLOR_BUTTON_TEXT)
    screen.blit(title_surf, title_surf.get_rect(center=(GRID_AREA_WIDTH + PANEL_WIDTH // 2, title_y)))
    
    for size_id, b in size_buttons.items():
        puzzle_def = PUZZLE_DEFINITIONS[size_id]
        diff_colors = DIFFICULTY_COLORS[puzzle_def['difficulty']]
        color = diff_colors['hover'] if b['rect'].collidepoint(mouse_pos) else diff_colors['base']
        pygame.draw.circle(screen, color, b['rect'].center, b['radius'])
        if size_id == current_size_selection: pygame.draw.circle(screen, COLOR_SELECTED, b['rect'].center, b['radius'], 3)
        num_surf = small_font.render(str(puzzle_def['dim']), True, COLOR_BUTTON_TEXT)
        screen.blit(num_surf, num_surf.get_rect(center=b['rect'].center))
        draw_star_indicator(screen, b['rect'], puzzle_def['stars'], tiny_font)
    if solution_status:
        color = COLOR_CORRECT if solution_status == "Correct!" else COLOR_INCORRECT
        status_surf = font.render(solution_status, True, color)
        status_rect = status_surf.get_rect(center=(GRID_AREA_WIDTH + PANEL_WIDTH // 2, buttons['check']['rect'].top - 30))
        screen.blit(status_surf, status_rect)
def draw_feedback_overlay(screen, color, alpha):
    if alpha > 0:
        overlay = pygame.Surface((GRID_AREA_WIDTH, GRID_AREA_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*color, alpha)); screen.blit(overlay, (0, 0))
def get_sbn_input_from_console():
    pygame.display.iconify()
    sbn_string = input("\n--- PASTE SBN STRING AND PRESS ENTER ---\n> ")
    return sbn_string.strip()

# Z3 Solver block is unchanged
def format_duration(seconds):
    if seconds >= 60:
        minutes = int(seconds // 60); remaining_seconds = seconds % 60
        if remaining_seconds < 0.01: return f"{minutes} min"
        return f"{minutes} min {remaining_seconds:.2f} s"
    if seconds >= 1: return f"{seconds:.3f} s"
    if seconds >= 0.001: return f"{seconds * 1000:.2f} ms"
    return f"{seconds * 1_000_000:.2f} µs"
def validate_solver_solution_with_hash(solution_grid, puzzle_data):
    expected_hash = puzzle_data.get('solution_hash')
    if not expected_hash: return
    yn_string = "".join(['y' if cell == 1 else 'n' for row in solution_grid for cell in row])
    string_to_hash = puzzle_data['task'] + yn_string
    calculated_hash = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()
    print("--- Hash Validation ---")
    if calculated_hash == expected_hash: print("\033[92m✅ Found solution MATCHES the website's expected solution.\033[0m")
    else: print("\033[91m❌ Found solution DOES NOT MATCH the website's expected solution.\033[0m")
class Z3StarBattleSolver:
    def __init__(self, region_grid, stars_per_region):
        self.region_grid = region_grid; self.dim = len(region_grid); self.stars_per_region = stars_per_region
    def solve(self):
        if not Z3_AVAILABLE: return [], {}
        s = Solver(); grid_vars = [[Bool(f"cell_{r}_{c}") for c in range(self.dim)] for r in range(self.dim)]
        for i in range(self.dim):
            s.add(PbEq([(var, 1) for var in grid_vars[i]], self.stars_per_region))
            s.add(PbEq([(grid_vars[r][i], 1) for r in range(self.dim)], self.stars_per_region))
        regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim): regions[self.region_grid[r][c]].append(grid_vars[r][c])
        for region_vars in regions.values(): s.add(PbEq([(var, 1) for var in region_vars], self.stars_per_region))
        for r in range(self.dim):
            for c in range(self.dim):
                neighbors = [Not(grid_vars[nr][nc]) for dr in range(-1,2) for dc in range(-1,2) if not(dr==0 and dc==0) and 0<=(nr:=r+dr)<self.dim and 0<=(nc:=c+dc)<self.dim]
                s.add(Implies(grid_vars[r][c], And(neighbors)))
        solutions = []
        if s.check() == sat:
            model = s.model()
            solution_board = [[(1 if model.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
            solutions.append(solution_board)
            blocking_clause = Or([grid_vars[r][c] if solution_board[r][c] == 0 else Not(grid_vars[r][c]) for r in range(self.dim) for c in range(self.dim)])
            s.add(blocking_clause)
            if s.check() == sat:
                model = s.model()
                solution_board_2 = [[(1 if model.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
                solutions.append(solution_board_2)
        return solutions, {}

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Star Battle Playground")
    clock = pygame.time.Clock(); font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 24); tiny_font = pygame.font.Font(None, 18)

    # --- INITIAL PUZZLE LOAD WITH CONVERSION FEEDBACK ---
    current_size_selection = 5
    puzzle_data = get_puzzle_from_website(current_size_selection)
    if puzzle_data:
        p_def = PUZZLE_DEFINITIONS[current_size_selection]
        grid, _ = parse_and_validate_grid(puzzle_data['task'])
        sbn_eq = encode_to_sbn(grid, p_def['stars'])
        print("\n" + "="*50)
        print("PUZZLE LOADED: FROM WEBSITE")
        print(f"  -> Web Task (Original): {puzzle_data['task']}")
        print(f"  -> SBN Equivalent:      {sbn_eq}")
        print("="*50)
    # --- END INITIAL LOAD ---
    
    (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = reset_game_state(puzzle_data)
    if not region_grid: sys.exit(1)
    
    b_width, b_height, b_v_margin = 200, 45, 15
    button_defs = [('new', 'New Puzzle'), ('sbn', 'Load SBN'), ('clear', 'Clear Board'), ('find', 'Find Solution'), ('toggle', 'Mode: Xs')]
    check_button_def = ('check', 'Check Solution')
    buttons = {}; current_y = b_v_margin
    for name, text in button_defs:
        rect = pygame.Rect(GRID_AREA_WIDTH + (PANEL_WIDTH - b_width) // 2, current_y, b_width, b_height)
        buttons[name] = {'rect': rect, 'text': text}; current_y += b_height + b_v_margin
    last_button_y = current_y - b_v_margin
    check_rect = pygame.Rect(GRID_AREA_WIDTH + (PANEL_WIDTH - b_width) // 2, WINDOW_HEIGHT - b_height - b_v_margin, b_width, b_height)
    buttons[check_button_def[0]] = {'rect': check_rect, 'text': check_button_def[1]}

    size_buttons = {}
    s_radius, s_cols, s_padding = 22, 4, (PANEL_WIDTH - (4 * 22 * 2)) // 5
    size_buttons_start_y = last_button_y + 80
    for i in range(12):
        row, col = divmod(i, s_cols)
        y = size_buttons_start_y + row * (s_radius * 2 + s_padding)
        x = GRID_AREA_WIDTH + s_padding + col * (s_radius * 2 + s_padding) + s_radius
        size_buttons[i] = {'rect': pygame.Rect(x-s_radius, y-s_radius, s_radius*2, s_radius*2), 'radius': s_radius}
    
    mark_is_x, solution_status = True, None
    is_left_down, is_dragging, click_cell = False, False, None
    feedback_overlay_alpha, feedback_overlay_color = 0, COLOR_CORRECT; FADE_SPEED = 4

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            def reset_feedback(): nonlocal solution_status, feedback_overlay_alpha; solution_status, feedback_overlay_alpha = None, 0
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                if event.button == 1: # Left Click
                    clicked_on_button = False
                    for b_name, b_data in {**buttons, **size_buttons}.items():
                        is_disabled = (b_name == 'check' and (not puzzle_data or not puzzle_data.get('solution_hash'))) or \
                                      (b_name == 'find' and not Z3_AVAILABLE)
                        if b_data['rect'].collidepoint(pos) and not is_disabled:
                            clicked_on_button = True
                            # --- MODIFIED: Handle Web Puzzle Loading and Conversion ---
                            if b_name == 'new' or isinstance(b_name, int):
                                if isinstance(b_name, int): current_size_selection = b_name
                                new_puzzle_data = get_puzzle_from_website(current_size_selection)
                                if new_puzzle_data:
                                    p_def = PUZZLE_DEFINITIONS[current_size_selection]
                                    grid, _ = parse_and_validate_grid(new_puzzle_data['task'])
                                    sbn_eq = encode_to_sbn(grid, p_def['stars'])
                                    print("\n" + "="*50)
                                    print("PUZZLE LOADED: FROM WEBSITE")
                                    print(f"  -> Web Task (Original): {new_puzzle_data['task']}")
                                    print(f"  -> SBN Equivalent:      {sbn_eq}")
                                    print("="*50)
                                    puzzle_data = new_puzzle_data
                                (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = reset_game_state(puzzle_data)
                                reset_feedback()
                            # --- MODIFIED: Handle SBN Loading and Conversion ---
                            elif b_name == 'sbn':
                                sbn_string = get_sbn_input_from_console()
                                screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                                pygame.display.set_caption("Star Battle Playground")
                                if sbn_string:
                                    new_puzzle_data = decode_sbn(sbn_string)
                                    if new_puzzle_data:
                                        print("\n" + "="*50)
                                        print("PUZZLE LOADED: FROM SBN")
                                        print(f"  -> SBN String (Original): {sbn_string}")
                                        print(f"  -> Web Task Equivalent: {new_puzzle_data['task']}")
                                        print("="*50)
                                        puzzle_data = new_puzzle_data
                                        (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = reset_game_state(puzzle_data)
                                        current_size_selection = -1
                                        reset_feedback()
                            elif b_name == 'clear':
                                player_grid = [[STATE_EMPTY] * current_grid_dim for _ in range(current_grid_dim)]; reset_feedback()
                            elif b_name == 'toggle':
                                mark_is_x = not mark_is_x
                            elif b_name == 'check':
                                is_correct = check_solution(player_grid, puzzle_data); solution_status = "Correct!" if is_correct else "Incorrect!"
                                feedback_overlay_color = COLOR_CORRECT if is_correct else COLOR_INCORRECT; feedback_overlay_alpha = 128
                            elif b_name == 'find':
                                solver = Z3StarBattleSolver(region_grid, stars_per_region)
                                start_time = time.monotonic()
                                solutions, _ = solver.solve()
                                duration = time.monotonic() - start_time
                                print(f"Solve time: {format_duration(duration)}")
                                if len(solutions) > 0:
                                    validate_solver_solution_with_hash(solutions[0], puzzle_data)
                                    display_terminal_grid(region_grid, "Found Solution", solutions[0])
                            break
                    if not clicked_on_button and pos[0] < GRID_AREA_WIDTH:
                        col, row = int(pos[0] // cell_size), int(pos[1] // cell_size)
                        if 0 <= row < current_grid_dim and 0 <= col < current_grid_dim:
                             is_left_down, is_dragging, click_cell = True, False, (row, col)
                elif event.button == 3 and pos[0] < GRID_AREA_WIDTH:
                    col, row = int(pos[0] // cell_size), int(pos[1] // cell_size)
                    if 0 <= row < current_grid_dim and 0 <= col < current_grid_dim:
                        player_grid[row][col] = STATE_EMPTY if player_grid[row][col] == STATE_STAR else STATE_STAR; reset_feedback()
            elif event.type == pygame.MOUSEMOTION:
                if is_left_down:
                    is_dragging = True; col, row = int(event.pos[0] // cell_size), int(event.pos[1] // cell_size)
                    if 0 <= row < current_grid_dim and 0 <= col < current_grid_dim:
                        if player_grid[row][col] != STATE_SECONDARY_MARK: player_grid[row][col] = STATE_SECONDARY_MARK; reset_feedback()
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if not is_dragging and click_cell:
                        row, col = click_cell; state = player_grid[row][col]
                        if state == STATE_EMPTY: player_grid[row][col] = STATE_SECONDARY_MARK
                        elif state == STATE_SECONDARY_MARK: player_grid[row][col] = STATE_STAR
                        elif state == STATE_STAR: player_grid[row][col] = STATE_EMPTY
                        reset_feedback()
                    is_left_down, is_dragging, click_cell = False, False, None
        
        screen.fill(COLOR_PANEL)
        if region_grid:
            draw_background_colors(screen, region_grid, cell_size)
            draw_player_marks(screen, player_grid, mark_is_x, cell_size)
            draw_grid_lines(screen, region_grid, cell_size)
            draw_feedback_overlay(screen, feedback_overlay_color, feedback_overlay_alpha)
        if feedback_overlay_alpha > 0: feedback_overlay_alpha = max(0, feedback_overlay_alpha - FADE_SPEED)
        draw_control_panel(screen, font, small_font, tiny_font, buttons, size_buttons, current_size_selection, mark_is_x, solution_status, bool(puzzle_data and puzzle_data.get('solution_hash')), last_button_y)
        pygame.display.set_caption(f"Star Battle ({stars_per_region} Stars)")
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
