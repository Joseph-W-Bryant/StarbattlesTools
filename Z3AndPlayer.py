# 3starbattles_player_with_solver.py (Final Polished Version with Correct 11x11 Padding)

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
SBN_ALPHABET = {c: i for i, c in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')}
SBN_CODE_TO_DIM_MAP = {f'{char}{char}': val for char, val in SBN_ALPHABET.items() if val > 0}
BASE64_DISPLAY_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'

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
    print(f"Fetching puzzle data from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10); response.raise_for_status()
        task_match = re.search(r"var task = '([^']+)';", response.text)
        hash_match = re.search(r"hashedSolution: '([^']+)'", response.text)
        if task_match and hash_match:
            print("Successfully extracted puzzle and solution hash.")
            return {'task': task_match.group(1), 'solution_hash': hash_match.group(1)}
        print("Error: Could not find required puzzle data."); return None
    except requests.RequestException as e:
        print(f"Error: Could not fetch puzzle data. {e}"); return None

# --- MODIFIED: Implemented correct padding logic for 11x11 ---
def decode_sbn(sbn_string):
    print(f"\nDecoding SBN: {sbn_string}")
    try:
        if len(sbn_string) < 4: raise ValueError("SBN string is too short (less than 4 chars).")
        
        size_code = sbn_string[0:2]
        dim = SBN_CODE_TO_DIM_MAP.get(size_code)
        if not dim: raise ValueError(f"Unknown or invalid SBN size code '{size_code}'")
        
        stars = int(sbn_string[2])
        is_annotated = sbn_string[3] == 'e'
        print(f"Detected: {dim}x{dim} grid, {stars} stars, Annotated: {is_annotated}")

        border_bits_needed = 2 * dim * (dim - 1)
        border_chars_needed = math.ceil(border_bits_needed / 6)
        
        region_data_start_idx = 4
        region_data_end_idx = region_data_start_idx + border_chars_needed

        if len(sbn_string) < region_data_end_idx:
            raise ValueError(f"SBN string is too short for its dimension. Expected {border_chars_needed} chars for region data.")
        
        region_data_str = sbn_string[region_data_start_idx : region_data_end_idx]
        annotation_data_str = sbn_string[region_data_end_idx:]

        full_bitfield = "".join(bin(SBN_ALPHABET[char])[2:].zfill(6) for char in region_data_str)
        
        # --- THIS IS THE FIX ---
        # Handle the special case for 11x11 grid region data ordering.
        if dim == 11:
            print("Applying special 11x11 grid decoding rule (padding at start).")
            # For 11x11, there are 220 border bits, requiring 37 chars (222 bits).
            # The first 2 bits are padding and must be discarded.
            border_data = full_bitfield[2:]
        else:
            # For all other sizes, the bitfield is used as-is.
            border_data = full_bitfield
        # --- END OF FIX ---

        num_single_direction_borders = dim * (dim - 1)
        vertical_bits = border_data[0 : num_single_direction_borders]
        horizontal_bits = border_data[num_single_direction_borders : border_bits_needed]
            
        region_grid = [[0] * dim for _ in range(dim)]
        region_id = 1
        for r_start in range(dim):
            for c_start in range(dim):
                if region_grid[r_start][c_start] == 0:
                    q = deque([(r_start, c_start)])
                    region_grid[r_start][c_start] = region_id
                    while q:
                        r, c = q.popleft()
                        if c < dim - 1 and region_grid[r][c+1] == 0 and vertical_bits[r*(dim-1) + c] == '0':
                            region_grid[r][c+1] = region_id; q.append((r, c+1))
                        if c > 0 and region_grid[r][c-1] == 0 and vertical_bits[r*(dim-1) + (c-1)] == '0':
                            region_grid[r][c-1] = region_id; q.append((r, c-1))
                        if r < dim - 1 and region_grid[r+1][c] == 0 and horizontal_bits[c*(dim-1) + r] == '0':
                            region_grid[r+1][c] = region_id; q.append((r+1, c))
                        if r > 0 and region_grid[r-1][c] == 0 and horizontal_bits[c*(dim-1) + (r-1)] == '0':
                             region_grid[r-1][c] = region_id; q.append((r-1, c))
                    region_id += 1
        
        task_string = ",".join(str(cell) for row in region_grid for cell in row)
        
        decoded_player_grid = None
        if is_annotated and annotation_data_str:
            print("Decoding SBN annotations...")
            player_grid = [[STATE_EMPTY] * dim for _ in range(dim)]
            flat_indices = [(r, c) for r in range(dim) for c in range(dim)]
            sbn_to_game_state = {0: STATE_EMPTY, 1: STATE_SECONDARY_MARK, 2: STATE_STAR}
            char_cursor, cell_cursor = 0, 0
            if dim in [10, 11]:
                value = int(annotation_data_str[0])
                player_grid[0][0] = sbn_to_game_state.get(value, STATE_EMPTY)
                char_cursor += 1
                cell_cursor += 1
            while cell_cursor < dim * dim and char_cursor < len(annotation_data_str):
                char = annotation_data_str[char_cursor]
                value = SBN_ALPHABET.get(char, 0)
                states = [value // 16, (value % 16) // 4, value % 4]
                for i in range(3):
                    if cell_cursor + i < dim * dim:
                        r, c = flat_indices[cell_cursor + i]
                        player_grid[r][c] = sbn_to_game_state.get(states[i], STATE_EMPTY)
                cell_cursor += 3
                char_cursor += 1
            decoded_player_grid = player_grid
            print("Annotations decoded successfully.")

        print(f"SBN processing complete.")
        return {'task': task_string, 'solution_hash': None, 'stars': stars, 'player_grid': decoded_player_grid}
    except (KeyError, IndexError, ValueError) as e:
        print(f"--- SBN DECODING FAILED ---"); print(f"Error: {e}"); return None

def parse_and_validate_grid(task_string):
    if not task_string: return None, None
    try:
        numbers = [int(n) for n in task_string.split(',')]; total_cells = len(numbers)
        if total_cells == 0: return None, None
        dimension = int(math.sqrt(total_cells))
        if dimension * dimension != total_cells: print(f"Error: Data length ({total_cells}) is not a perfect square."); return None, None
        grid = [numbers[i*dimension:(i+1)*dimension] for i in range(dimension)]
        print(f"Successfully parsed a {dimension}x{dimension} grid.")
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
                if content_grid:
                    symbol = '★' if content_grid[r][c] == 1 else 'X'
                else:
                    symbol = BASE64_DISPLAY_ALPHABET[(region_num - 1) % len(BASE64_DISPLAY_ALPHABET)]
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
        
        if puzzle_data.get('player_grid'):
            print("Loading pre-filled grid from SBN.")
            player_grid = puzzle_data['player_grid']
        else:
            print("Creating new empty grid.")
            player_grid = [[STATE_EMPTY] * dimension for _ in range(dimension)]
            
        cell_size = GRID_AREA_WIDTH / dimension
        stars = puzzle_data.get('stars', 0)
        if stars == 0:
            for pdef in PUZZLE_DEFINITIONS:
                if pdef['dim'] == dimension: stars = pdef['stars']; break
            if stars == 0: stars = 2
        
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

# --- Drawing Functions ---
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

# --- Z3 SOLVER CODE BLOCK (UNCHANGED) ---
def format_duration(seconds):
    if seconds >= 60:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        if remaining_seconds < 0.01: return f"{minutes} min"
        return f"{minutes} min {remaining_seconds:.2f} s"
    if seconds >= 1: return f"{seconds:.3f} s"
    if seconds >= 0.001: return f"{seconds * 1000:.2f} ms"
    if seconds >= 0.000001: return f"{seconds * 1_000_000:.2f} µs"
    return f"{seconds * 1_000_000_000:.0f} ns"
def validate_solver_solution_with_hash(solution_grid, puzzle_data):
    expected_hash = puzzle_data.get('solution_hash')
    if not expected_hash: return
    yn_string = "".join(['y' if cell == 1 else 'n' for row in solution_grid for cell in row])
    string_to_hash = puzzle_data['task'] + yn_string
    calculated_hash = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()
    print("--- Hash Validation ---")
    if calculated_hash == expected_hash:
        print("\033[92m✅ Found solution MATCHES the website's expected solution.\033[0m")
    else:
        print("\033[91m❌ Found solution DOES NOT MATCH the website's expected solution.\033[0m")
class Z3StarBattleSolver:
    def __init__(self, region_grid, stars_per_region):
        self.region_grid = region_grid; self.dim = len(region_grid); self.stars_per_region = stars_per_region
    def solve(self):
        if not Z3_AVAILABLE: return [], {}
        s = Solver()
        grid_vars = [[Bool(f"cell_{r}_{c}") for c in range(self.dim)] for r in range(self.dim)]
        for i in range(self.dim):
            s.add(PbEq([(var, 1) for var in grid_vars[i]], self.stars_per_region))
            s.add(PbEq([(grid_vars[r][i], 1) for r in range(self.dim)], self.stars_per_region))
        regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim): regions[self.region_grid[r][c]].append(grid_vars[r][c])
        for region_vars in regions.values():
            s.add(PbEq([(var, 1) for var in region_vars], self.stars_per_region))
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
# --- END Z3 SOLVER CODE BLOCK ---

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Star Battle Playground")
    clock = pygame.time.Clock(); font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 24); tiny_font = pygame.font.Font(None, 18)

    current_size_selection = 5
    puzzle_data = get_puzzle_from_website(current_size_selection)
    (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = reset_game_state(puzzle_data)
    if not region_grid: sys.exit(1)
    
    b_width, b_height, b_v_margin = 200, 45, 15
    button_defs = [
        ('new', 'New Puzzle'), ('sbn', 'Load SBN'), ('clear', 'Clear Board'),
        ('find', 'Find Solution'), ('toggle', 'Mode: Xs'),
    ]
    check_button_def = ('check', 'Check Solution')
    buttons = {}
    current_y = b_v_margin
    for name, text in button_defs:
        rect = pygame.Rect(GRID_AREA_WIDTH + (PANEL_WIDTH - b_width) // 2, current_y, b_width, b_height)
        buttons[name] = {'rect': rect, 'text': text}
        current_y += b_height + b_v_margin
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
                            if b_name == 'new':
                                new_puzzle_data = get_puzzle_from_website(current_size_selection)
                                if new_puzzle_data: puzzle_data = new_puzzle_data
                                (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = reset_game_state(puzzle_data)
                                reset_feedback()
                            elif b_name == 'clear':
                                player_grid = [[STATE_EMPTY] * current_grid_dim for _ in range(current_grid_dim)]; reset_feedback()
                            elif b_name == 'toggle':
                                mark_is_x = not mark_is_x
                            elif b_name == 'sbn':
                                sbn_string = get_sbn_input_from_console()
                                screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                                pygame.display.set_caption("Star Battle Playground")
                                
                                if sbn_string:
                                    new_puzzle_data = decode_sbn(sbn_string)
                                    if new_puzzle_data:
                                        puzzle_data = new_puzzle_data
                                        (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = reset_game_state(puzzle_data)
                                        current_size_selection = -1; reset_feedback()
                            elif b_name == 'check':
                                is_correct = check_solution(player_grid, puzzle_data); solution_status = "Correct!" if is_correct else "Incorrect!"
                                feedback_overlay_color = COLOR_CORRECT if is_correct else COLOR_INCORRECT; feedback_overlay_alpha = 128
                            elif b_name == 'find':
                                print("\n" + "="*40 + "\n--- Finding solution with Z3 Solver... ---")
                                solver = Z3StarBattleSolver(region_grid, stars_per_region)
                                start_time = time.monotonic()
                                solutions, _ = solver.solve()
                                duration = time.monotonic() - start_time
                                num_solutions = len(solutions)
                                if num_solutions == 0: print("RESULT: No solution found.")
                                elif num_solutions == 1:
                                    print("RESULT: Found 1 unique solution.")
                                    validate_solver_solution_with_hash(solutions[0], puzzle_data)
                                    display_terminal_grid(region_grid, "Unique Solution", solutions[0])
                                else:
                                    print("RESULT: Multiple solutions exist. Found at least 2.")
                                    validate_solver_solution_with_hash(solutions[0], puzzle_data)
                                    display_terminal_grid(region_grid, "Solution 1", solutions[0])
                                    validate_solver_solution_with_hash(solutions[1], puzzle_data)
                                    display_terminal_grid(region_grid, "Solution 2", solutions[1])
                                print(f"Solve time: {format_duration(duration)}\n" + "="*40 + "\n")
                            elif isinstance(b_name, int):
                                current_size_selection = b_name
                                new_puzzle_data = get_puzzle_from_website(current_size_selection)
                                if new_puzzle_data: puzzle_data = new_puzzle_data
                                (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = reset_game_state(puzzle_data)
                                reset_feedback()
                            break
                    if not clicked_on_button and pos[0] < GRID_AREA_WIDTH:
                        col, row = int(pos[0] // cell_size), int(pos[1] // cell_size)
                        if 0 <= col < current_grid_dim: is_left_down, is_dragging, click_cell = True, False, (row, col)
                
                elif event.button == 3 and pos[0] < GRID_AREA_WIDTH:
                    col, row = int(pos[0] // cell_size), int(pos[1] // cell_size)
                    if 0 <= col < current_grid_dim: player_grid[row][col] = STATE_EMPTY if player_grid[row][col] == STATE_STAR else STATE_STAR; reset_feedback()
            
            elif event.type == pygame.MOUSEMOTION:
                if is_left_down:
                    is_dragging = True; col, row = int(event.pos[0] // cell_size), int(event.pos[1] // cell_size)
                    if 0 <= col < current_grid_dim and 0 <= row < current_grid_dim:
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