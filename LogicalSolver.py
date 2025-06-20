import pygame
import requests
import re
import sys
import math
from collections import defaultdict
import os
import warnings

# --- Silence Pygame messages and warnings ---
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
warnings.filterwarnings("ignore", category=RuntimeWarning, message="Your system is avx2 capable but pygame was not built with support for it.*")
warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources is deprecated as an API.*")

# --- Pygame and UI Constants ---
GRID_AREA_WIDTH = 600
GRID_AREA_HEIGHT = 600
PANEL_WIDTH = 250
WINDOW_WIDTH = GRID_AREA_WIDTH + PANEL_WIDTH
WINDOW_HEIGHT = GRID_AREA_HEIGHT
GUTTER = 5
BORDER_NORMAL = 1
BORDER_THICK = 3
LINE_WIDTH_X = 4

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
COLOR_SELECTED = (100, 180, 255)
DIFFICULTY_COLORS = {
    'easy':   {'base': (70, 160, 70),  'hover': (90, 190, 90)},
    'medium': {'base': (180, 140, 50), 'hover': (210, 170, 70)},
    'hard':   {'base': (180, 70, 70),  'hover': (210, 90, 90)}
}
# Full color definitions for both GUI and Terminal
UNIFIED_COLORS_BG_GUI = [
    (255,204,204), (204,255,204), (255,255,204), (204,229,255),
    (255,204,255), (204,255,255), (255,229,204), (229,204,255),
    (224,224,224), (210,240,210), (255,218,185), (173,216,230),
]
UNIFIED_COLORS_BG_TERMINAL = [
    ("Bright Red",(255,204,204),"\033[48;2;255;204;204m\033[38;2;0;0;0m"),("Bright Green",(204,255,204),"\033[48;2;204;255;204m\033[38;2;0;0;0m"),
    ("Bright Yellow",(255,255,204),"\033[48;2;255;255;204m\033[38;2;0;0;0m"),("Bright Blue",(204,229,255),"\033[48;2;204;229;255m\033[38;2;0;0;0m"),
    ("Bright Magenta",(255,204,255),"\033[48;2;255;204;255m\033[38;2;0;0;0m"),("Bright Cyan",(204,255,255),"\033[48;2;204;255;255m\033[38;2;0;0;0m"),
    ("Light Orange",(255,229,204),"\033[48;2;255;229;204m\033[38;2;0;0;0m"),("Light Purple",(229,204,255),"\033[48;2;229;204;255m\033[38;2;0;0;0m"),
    ("Light Gray",(224,224,224),"\033[48;2;224;224;224m\033[38;2;0;0;0m"),("Mint",(210,240,210),"\033[48;2;210;240;210m\033[38;2;0;0;0m"),
    ("Peach",(255,218,185),"\033[48;2;255;218;185m\033[38;2;0;0;0m"),("Sky Blue",(173,216,230),"\033[48;2;173;216;230m\033[38;2;0;0;0m"),
]
BASE64_DISPLAY_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'


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

# --- Difficulty Scoring Configuration ---
TECHNIQUE_SCORES = {
    1: 1, 2: 5, 3: 25, 4: 100
}
BREAK_IN_BONUS = {
    3: 50, 4: 150
}

# --- Puzzle State Constants ---
EMPTY = 0
STAR = 1
SECONDARY_MARK = 2 # This can be an X or a Dot

class Puzzle:
    def __init__(self, grid_size, stars_per, regions):
        self.grid_size = grid_size
        self.stars_per = stars_per
        self.regions = regions
        self.grid = [[EMPTY for _ in range(grid_size)] for _ in range(grid_size)]

    def place_star(self, r, c):
        if self.grid[r][c] != EMPTY: return 0
        self.grid[r][c] = STAR
        dots_placed = 0
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size and self.grid[nr][nc] == EMPTY:
                    self.grid[nr][nc] = SECONDARY_MARK
                    dots_placed += 1
        return 1 + dots_placed

    def place_secondary_mark(self, r, c):
        if self.grid[r][c] == EMPTY:
            self.grid[r][c] = SECONDARY_MARK
            return 1
        return 0

    def clear_grid(self):
        self.grid = [[EMPTY for _ in range(self.grid_size)] for _ in range(self.grid_size)]

class LogicalSolver:
    def __init__(self, puzzle):
        self.puzzle = puzzle
        self.technique_log = defaultdict(int)
        self.difficulty_score = 0
        self.is_solved = False
        self._bonus_applied = set()

    def solve(self):
        print("\n" + "="*50)
        print("--- Starting Logical Solver ---")
        display_terminal_grid(self.puzzle.regions, "Initial Puzzle State", self.puzzle.grid)

        while True:
            progress_made_this_iteration = 0
            # --- TECHNIQUE APPLICATION STAGE GOES HERE ---
            
            if progress_made_this_iteration == 0:
                print("\n--- No more logical deductions can be made. ---")
                break
        
        print("\n--- Solver Finished ---")
        self.calculate_difficulty()
        self.check_if_solved()
        display_terminal_grid(self.puzzle.regions, "Final Puzzle State", self.puzzle.grid)
        self.print_results()
        print("="*50 + "\n")

    def apply_technique(self, tech_name, tier, count=1):
        if count > 0:
            print(f"LOG: Applying Tier {tier} technique: '{tech_name}' ({count} time(s))")
            self.technique_log[f"T{tier}_{tech_name}"] += count

    def calculate_difficulty(self):
        score = 0
        for tech, count in self.technique_log.items():
            tier = int(tech.split('_')[0][1:])
            score += TECHNIQUE_SCORES.get(tier, 0) * count
            if tier in BREAK_IN_BONUS and tier not in self._bonus_applied:
                score += BREAK_IN_BONUS[tier]
                self._bonus_applied.add(tier)
        self.difficulty_score = score

    def check_if_solved(self):
        self.is_solved = False # Placeholder
        # TODO: Add full validation logic

    def print_results(self):
        print("\n--- Solver Results ---")
        print(f"Puzzle Solved: {self.is_solved}")
        print(f"Final Difficulty Score: {self.difficulty_score}")
        if not self.technique_log:
            print("Technique Log: (No techniques were applied)")
            return
        print("\nTechnique Breakdown:")
        sorted_log = sorted(self.technique_log.items())
        for tech, count in sorted_log:
            tier_str, name = tech.split('_', 1)
            tier = int(tier_str[1:])
            points = TECHNIQUE_SCORES.get(tier, 0)
            print(f"  - {name:<20} (Tier {tier}): {count:>3} uses x {points:>3} pts = {count * points:>5}")
        
        if self._bonus_applied:
            print("\nBonuses Applied:")
            for tier in sorted(self._bonus_applied):
                print(f"  - Tier {tier} Break-in Bonus: +{BREAK_IN_BONUS[tier]} pts")


# --- GUI and Terminal Drawing Functions ---
def display_terminal_grid(region_grid, title, content_grid=None):
    """
    Prints a colorized representation of the grid to the terminal,
    matching the style of the original program.
    """
    if not region_grid: return
    RESET = "\033[0m"
    print(f"\n--- {title} ---")
    dim = len(region_grid)
    for r in range(dim):
        colored_chars = []
        for c in range(dim):
            region_num = region_grid[r][c]
            if region_num > 0:
                color_ansi = UNIFIED_COLORS_BG_TERMINAL[(region_num - 1) % len(UNIFIED_COLORS_BG_TERMINAL)][2]
                symbol = BASE64_DISPLAY_ALPHABET[(region_num - 1) % len(BASE64_DISPLAY_ALPHABET)]
                if content_grid:
                    state = content_grid[r][c]
                    if state == STAR:
                        symbol = '★'
                    elif state == SECONDARY_MARK:
                        symbol = 'X'
                colored_chars.append(f"{color_ansi} {symbol} {RESET}")
            else:
                colored_chars.append(" ? ")
        print("".join(colored_chars))
    print("-----------------\n")

def draw_background_colors(screen, puzzle, cell_size):
    for r in range(puzzle.grid_size):
        for c in range(puzzle.grid_size):
            rect = pygame.Rect(c * cell_size, r * cell_size, cell_size, cell_size)
            region_num = puzzle.regions[r][c]
            color = UNIFIED_COLORS_BG_GUI[(region_num - 1) % len(UNIFIED_COLORS_BG_GUI)]
            pygame.draw.rect(screen, color, rect)

def draw_grid_lines(screen, puzzle, cell_size):
    # Draw thin grid lines for all cells
    for i in range(puzzle.grid_size + 1):
        pygame.draw.line(screen, COLOR_GRID_LINES, (i * cell_size, 0), (i * cell_size, GRID_AREA_HEIGHT), BORDER_NORMAL)
        pygame.draw.line(screen, COLOR_GRID_LINES, (0, i * cell_size), (GRID_AREA_WIDTH, i * cell_size), BORDER_NORMAL)

    # Draw thick region borders
    for r in range(puzzle.grid_size):
        for c in range(puzzle.grid_size):
            if c < puzzle.grid_size - 1 and puzzle.regions[r][c] != puzzle.regions[r][c+1]:
                pygame.draw.line(screen, COLOR_BLACK, ((c + 1) * cell_size, r * cell_size), ((c + 1) * cell_size, (r + 1) * cell_size), BORDER_THICK)
            if r < puzzle.grid_size - 1 and puzzle.regions[r][c] != puzzle.regions[r+1][c]:
                pygame.draw.line(screen, COLOR_BLACK, (c * cell_size, (r + 1) * cell_size), ((c + 1) * cell_size, (r + 1) * cell_size), BORDER_THICK)
    
    # Draw outer border
    pygame.draw.rect(screen, COLOR_BLACK, (0, 0, GRID_AREA_WIDTH, GRID_AREA_HEIGHT), BORDER_THICK)

def calculate_star_points(center_x, center_y, outer_radius, inner_radius):
    points = []
    for i in range(10):
        angle = math.pi / 5 * i - math.pi / 2
        radius = outer_radius if i % 2 == 0 else inner_radius
        points.append((center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
    return points

def draw_player_marks(screen, puzzle, cell_size, mark_is_x):
    for r in range(puzzle.grid_size):
        for c in range(puzzle.grid_size):
            cell_state = puzzle.grid[r][c]
            center_x, center_y = c * cell_size + cell_size / 2, r * cell_size + cell_size / 2
            if cell_state == STAR:
                outer_rad = cell_size / 2 - GUTTER * 1.5
                pygame.draw.polygon(screen, COLOR_STAR, calculate_star_points(center_x, center_y, outer_rad, outer_rad / 2))
            elif cell_state == SECONDARY_MARK:
                if mark_is_x:
                    margin = GUTTER * 2.5
                    pygame.draw.line(screen, COLOR_X, (c * cell_size + margin, r * cell_size + margin), ((c+1) * cell_size - margin, (r+1) * cell_size - margin), LINE_WIDTH_X)
                    pygame.draw.line(screen, COLOR_X, ((c+1) * cell_size - margin, r * cell_size + margin), (c * cell_size + margin, (r+1) * cell_size - margin), LINE_WIDTH_X)
                else: # Draw dot
                    pygame.draw.circle(screen, COLOR_DOT, (center_x, center_y), cell_size / 6)

def draw_control_panel(screen, font, small_font, buttons, size_buttons, current_selection, mark_is_x):
    pygame.draw.rect(screen, COLOR_PANEL, (GRID_AREA_WIDTH, 0, PANEL_WIDTH, WINDOW_HEIGHT))
    mouse_pos = pygame.mouse.get_pos()
    
    buttons['toggle']['text'] = "Mode: Xs" if mark_is_x else "Mode: Dots"

    for name, b in buttons.items():
        color = COLOR_BUTTON_HOVER if b['rect'].collidepoint(mouse_pos) else COLOR_BUTTON
        pygame.draw.rect(screen, color, b['rect'], border_radius=8)
        text_surf = font.render(b['text'], True, COLOR_BUTTON_TEXT)
        screen.blit(text_surf, text_surf.get_rect(center=b['rect'].center))

    last_button_y = buttons['solve']['rect'].bottom
    title_y = last_button_y + 40
    title_surf = font.render("New Puzzle", True, COLOR_BUTTON_TEXT)
    screen.blit(title_surf, title_surf.get_rect(center=(GRID_AREA_WIDTH + PANEL_WIDTH // 2, title_y)))

    for size_id, b in size_buttons.items():
        puzzle_def = PUZZLE_DEFINITIONS[size_id]
        diff_colors = DIFFICULTY_COLORS[puzzle_def['difficulty']]
        color = diff_colors['hover'] if b['rect'].collidepoint(mouse_pos) else diff_colors['base']
        pygame.draw.circle(screen, color, b['rect'].center, b['radius'])
        if size_id == current_selection:
            pygame.draw.circle(screen, COLOR_SELECTED, b['rect'].center, b['radius'], 3)
        num_surf = small_font.render(str(puzzle_def['dim']), True, COLOR_BUTTON_TEXT)
        screen.blit(num_surf, num_surf.get_rect(center=b['rect'].center))

# --- Data and Game State Functions ---
def parse_web_task(task_string):
    try:
        numbers = [int(n) for n in task_string.split(',')]
        dim = int(math.sqrt(len(numbers)))
        if dim * dim != len(numbers): return None, None
        grid = [numbers[i*dim:(i+1)*dim] for i in range(dim)]
        return grid, dim
    except (ValueError, TypeError): return None, None

def get_puzzle_from_website(size_selection):
    url = "https://www.puzzle-star-battle.com/"
    website_size_id = WEBSITE_SIZE_IDS[size_selection]
    if website_size_id != 0: url += f"?size={website_size_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"\nFetching puzzle data from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        task_match = re.search(r"var task = '([^']+)';", response.text)
        if task_match:
            print("Successfully extracted puzzle data.")
            return task_match.group(1)
        print("Error: Could not find required puzzle data."); return None
    except requests.RequestException as e:
        print(f"Error: Could not fetch puzzle data. {e}"); return None

# --- Main Application ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Star Battle Logical Solver")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 24)

    current_size_selection = 5
    puzzle_task = get_puzzle_from_website(current_size_selection)
    if not puzzle_task: sys.exit("Failed to load initial puzzle.")

    puzzle_def = PUZZLE_DEFINITIONS[current_size_selection]
    regions, dim = parse_web_task(puzzle_task)
    puzzle = Puzzle(dim, puzzle_def['stars'], regions)
    cell_size = GRID_AREA_WIDTH / dim

    # --- Setup Buttons ---
    buttons = {}
    b_width, b_height, b_margin = 200, 45, 15
    button_defs = [('clear', 'Clear Board'), ('toggle', 'Mode: Xs'), ('solve', 'Solve with Logic')]
    current_y = b_margin
    for name, text in button_defs:
        buttons[name] = {'rect': pygame.Rect(GRID_AREA_WIDTH + (PANEL_WIDTH - b_width) // 2, current_y, b_width, b_height), 'text': text}
        current_y += b_height + b_margin
    
    size_buttons = {}
    s_radius, s_cols, s_padding = 22, 4, (PANEL_WIDTH - (4 * 22 * 2)) // 5
    size_buttons_start_y = buttons['solve']['rect'].bottom + 80
    for i in range(12):
        row, col = divmod(i, s_cols)
        y = size_buttons_start_y + row * (s_radius * 2 + s_padding)
        x = GRID_AREA_WIDTH + s_padding + col * (s_radius * 2 + s_padding) + s_radius
        size_buttons[i] = {'rect': pygame.Rect(x - s_radius, y - s_radius, s_radius * 2, s_radius * 2), 'radius': s_radius}
    
    mark_is_x = True
    is_left_down, is_dragging, click_cell = False, False, None
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- Event Handling ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                if event.button == 1: # Left Click
                    clicked_on_button = False
                    # --- Button Click Handling ---
                    for b_name, b_data in {**buttons, **size_buttons}.items():
                        if b_data['rect'].collidepoint(pos):
                            clicked_on_button = True
                            if b_name == 'clear':
                                puzzle.clear_grid()
                            elif b_name == 'toggle':
                                mark_is_x = not mark_is_x
                            elif b_name == 'solve':
                                solver = LogicalSolver(puzzle)
                                solver.solve()
                            elif isinstance(b_name, int):
                                current_size_selection = b_name
                                new_task = get_puzzle_from_website(current_size_selection)
                                if new_task:
                                    puzzle_def = PUZZLE_DEFINITIONS[current_size_selection]
                                    regions, dim = parse_web_task(new_task)
                                    puzzle = Puzzle(dim, puzzle_def['stars'], regions)
                                    cell_size = GRID_AREA_WIDTH / dim
                            break # Prevent grid interaction if a button was clicked
                    
                    # --- Grid Click Handling ---
                    if not clicked_on_button and pos[0] < GRID_AREA_WIDTH:
                        c, r = int(pos[0] // cell_size), int(pos[1] // cell_size)
                        if 0 <= r < puzzle.grid_size and 0 <= c < puzzle.grid_size:
                             is_left_down, is_dragging, click_cell = True, False, (r, c)

                elif event.button == 3: # Right Click for Star
                     if pos[0] < GRID_AREA_WIDTH:
                        c, r = int(pos[0] // cell_size), int(pos[1] // cell_size)
                        if 0 <= r < puzzle.grid_size and 0 <= c < puzzle.grid_size:
                            puzzle.grid[r][c] = STAR if puzzle.grid[r][c] != STAR else EMPTY
            
            elif event.type == pygame.MOUSEMOTION:
                if is_left_down:
                    is_dragging = True
                    c, r = int(event.pos[0] // cell_size), int(event.pos[1] // cell_size)
                    if 0 <= r < puzzle.grid_size and 0 <= c < puzzle.grid_size:
                        if puzzle.grid[r][c] == EMPTY:
                            puzzle.place_secondary_mark(r, c)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if not is_dragging and click_cell: # Handle a simple click
                        r, c = click_cell
                        state = puzzle.grid[r][c]
                        if state == EMPTY: puzzle.grid[r][c] = SECONDARY_MARK
                        elif state == SECONDARY_MARK: puzzle.grid[r][c] = STAR
                        elif state == STAR: puzzle.grid[r][c] = EMPTY
                    is_left_down, is_dragging, click_cell = False, False, None

        # --- Drawing ---
        screen.fill(COLOR_WHITE)
        draw_background_colors(screen, puzzle, cell_size)
        draw_player_marks(screen, puzzle, cell_size, mark_is_x)
        draw_grid_lines(screen, puzzle, cell_size)
        draw_control_panel(screen, font, small_font, buttons, size_buttons, current_size_selection, mark_is_x)
        pygame.display.set_caption(f"Star Battle ({puzzle.stars_per} Stars)")
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

