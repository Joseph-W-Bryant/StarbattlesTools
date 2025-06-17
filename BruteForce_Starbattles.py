# 3starbattles_solver.py

import requests
import re
import sys
import math
import time
import argparse
from collections import deque, defaultdict
from copy import deepcopy

# --- Constants & Utilities (reused from player script) ---

# Terminal Colors
RESET = "\033[0m"

UNIFIED_COLORS = [
    ("Bright Red",(255,204,204),"\033[48;2;255;204;204m\033[38;2;0;0;0m"),
    ("Bright Green",(204,255,204),"\033[48;2;204;255;204m\033[38;2;0;0;0m"),
    ("Bright Yellow",(255,255,204),"\033[48;2;255;255;204m\033[38;2;0;0;0m"),
    ("Bright Blue",(204,229,255),"\033[48;2;204;229;255m\033[38;2;0;0;0m"),
    ("Bright Magenta",(255,204,255),"\033[48;2;255;204;255m\033[38;2;0;0;0m"),
    ("Bright Cyan",(204,255,255),"\033[48;2;204;255;255m\033[38;2;0;0;0m"),
    ("Light Orange",(255,229,204),"\033[48;2;255;229;204m\033[38;2;0;0;0m"),
    ("Light Purple",(229,204,255),"\033[48;2;229;204;255m\033[38;2;0;0;0m"),
    ("Light Gray",(224,224,224),"\033[48;2;224;224;224m\033[38;2;0;0;0m"),
    ("Mint",(210,240,210),"\033[48;2;210;240;210m\033[38;2;0;0;0m"),
    ("Peach",(255,218,185),"\033[48;2;255;218;185m\033[38;2;0;0;0m"),
    ("Sky Blue",(173,216,230),"\033[48;2;173;216;230m\033[38;2;0;0;0m"),
]

SBN_ALPHABET = {c: i for i, c in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')}
SBN_CODE_TO_DIM_MAP = {'99': 9, 'AA': 10, 'BB': 12, 'CC': 14, 'DD': 16, 'EE': 17, 'FF': 18, 'GG': 20, 'HH': 21, 'LL': 25}
BASE64_DISPLAY_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'

PUZZLE_DEFINITIONS = [
    {'dim': 5,  'stars': 1, 'difficulty': 'easy'},   # 0
    {'dim': 6,  'stars': 1, 'difficulty': 'easy'},   # 1
    {'dim': 6,  'stars': 1, 'difficulty': 'medium'}, # 2
    {'dim': 8,  'stars': 2, 'difficulty': 'medium'}, # 3
    {'dim': 8,  'stars': 2, 'difficulty': 'hard'},   # 4
    {'dim': 10, 'stars': 2, 'difficulty': 'medium'}, # 5
    {'dim': 10, 'stars': 2, 'difficulty': 'hard'},   # 6
    {'dim': 14, 'stars': 3, 'difficulty': 'medium'}, # 7
    {'dim': 14, 'stars': 3, 'difficulty': 'hard'},   # 8
    {'dim': 17, 'stars': 4, 'difficulty': 'hard'},   # 9
    {'dim': 21, 'stars': 5, 'difficulty': 'hard'},   # 10
    {'dim': 25, 'stars': 6, 'difficulty': 'hard'}    # 11
]
WEBSITE_SIZE_IDS = list(range(12))

# --- Puzzle Acquisition Functions ---

def get_puzzle_from_website(size_selection):
    url = "https://www.puzzle-star-battle.com/"
    website_size_id = WEBSITE_SIZE_IDS[size_selection]
    if website_size_id != 0: url += f"?size={website_size_id}"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    print(f"Fetching puzzle data from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        task_match = re.search(r"var task = '([^']+)';", response.text)
        if task_match:
            print("Successfully extracted puzzle task.")
            stars = PUZZLE_DEFINITIONS[size_selection]['stars']
            return {'task': task_match.group(1), 'stars': stars}
        print("Error: Could not find required puzzle data.")
        return None
    except requests.RequestException as e:
        print(f"Error: Could not fetch puzzle data. {e}")
        return None

def decode_sbn(sbn_string):
    print(f"Decoding SBN: {sbn_string}")
    try:
        size_code = sbn_string[0:2]
        dim = SBN_CODE_TO_DIM_MAP.get(size_code)
        if not dim:
            print(f"Error: Unknown SBN size code '{size_code}'")
            return None
        
        stars = int(sbn_string[2])
        region_data = sbn_string[4:]
        bitfield = "".join(bin(SBN_ALPHABET[char])[2:].zfill(6) for char in region_data)
        
        num_borders = dim * (dim - 1)
        vertical_bits = bitfield[:num_borders]
        horizontal_bits = bitfield[num_borders : num_borders * 2]
        
        region_grid = [[0] * dim for _ in range(dim)]
        region_id = 1
        for r_start in range(dim):
            for c_start in range(dim):
                if region_grid[r_start][c_start] == 0:
                    q = deque([(r_start, c_start)])
                    region_grid[r_start][c_start] = region_id
                    while q:
                        r, c = q.popleft()
                        # Check neighbors
                        if r > 0 and region_grid[r-1][c] == 0 and horizontal_bits[c*(dim-1) + (r-1)] == '0':
                            region_grid[r-1][c] = region_id
                            q.append((r-1, c))
                        if r < dim - 1 and region_grid[r+1][c] == 0 and horizontal_bits[c*(dim-1) + r] == '0':
                            region_grid[r+1][c] = region_id
                            q.append((r+1, c))
                        if c > 0 and region_grid[r][c-1] == 0 and vertical_bits[r*(dim-1) + (c-1)] == '0':
                            region_grid[r][c-1] = region_id
                            q.append((r, c-1))
                        if c < dim - 1 and region_grid[r][c+1] == 0 and vertical_bits[r*(dim-1) + c] == '0':
                            region_grid[r][c+1] = region_id
                            q.append((r, c+1))
                    region_id += 1
        
        task_string = ",".join(str(cell) for row in region_grid for cell in row)
        print(f"SBN decoded successfully to a {dim}x{dim} grid with {stars} stars.")
        return {'task': task_string, 'stars': stars}

    except (KeyError, IndexError, ValueError) as e:
        print(f"Error decoding SBN: Invalid format. {e}")
        return None

def parse_and_validate_grid(task_string):
    if not task_string: return None, None
    try:
        numbers = [int(n) for n in task_string.split(',')]
        total_cells = len(numbers)
        if total_cells == 0: return None, None
        dimension = int(math.sqrt(total_cells))
        if dimension * dimension != total_cells:
            print(f"Error: Data length ({total_cells}) is not a perfect square.")
            return None, None
        grid = [numbers[i*dimension:(i+1)*dimension] for i in range(dimension)]
        print(f"Successfully parsed a {dimension}x{dimension} grid.")
        return grid, dimension
    except (ValueError, TypeError):
        return None, None

# --- Display Functions ---

def display_grid_as_symbols(grid, title="--- Puzzle Regions ---"):
    """Displays the grid using a single, colored Base64 character per region."""
    if not grid: return
    print(f"\n{title}")
    for row in grid:
        colored_chars = []
        for cell_num in row:
            symbol = BASE64_DISPLAY_ALPHABET[cell_num - 1] if 0 < cell_num <= len(BASE64_DISPLAY_ALPHABET) else '?'
            color_ansi = UNIFIED_COLORS[(cell_num - 1) % len(UNIFIED_COLORS)][2]
            colored_chars.append(f"{color_ansi} {symbol} {RESET}")
        print("".join(colored_chars))
    print("-" * (len(title)) + "\n")
    
def display_solution(solution_board, region_grid, title="Solution"):
    """Displays a found solution with colored backgrounds, stars, and Xs."""
    print(f"\n--- {title} ---")
    dim = len(solution_board)
    for r in range(dim):
        colored_chars = []
        for c in range(dim):
            region_num = region_grid[r][c]
            color_ansi = UNIFIED_COLORS[(region_num - 1) % len(UNIFIED_COLORS)][2]
            symbol = '★' if solution_board[r][c] == 1 else 'X'
            colored_chars.append(f"{color_ansi} {symbol} {RESET}")
        print("".join(colored_chars))
    print("------------------\n")

# --- Solver Class ---

class StarBattleSolver:
    def __init__(self, region_grid, stars_per_region):
        self.region_grid = region_grid
        self.dim = len(region_grid)
        self.stars_per_region = stars_per_region
        self.max_solutions = 2  # Stop after finding 2 solutions
        
        # Pre-process regions for efficient lookup
        self.regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim):
                self.regions[self.region_grid[r][c]].append((r, c))

        # Solver state
        self.board = [[0] * self.dim for _ in range(self.dim)]
        self.solutions = []
        self.row_counts = [0] * self.dim
        self.col_counts = [0] * self.dim
        self.region_counts = defaultdict(int)

    def solve(self):
        """Public method to start the solving process."""
        self._backtrack(0, 0)
        return self.solutions

    def _is_valid_placement(self, r, c):
        """Checks if placing a star at (r, c) violates any constraints."""
        # 1. Row, Column, and Region count constraints
        if self.row_counts[r] >= self.stars_per_region: return False
        if self.col_counts[c] >= self.stars_per_region: return False
        if self.region_counts[self.region_grid[r][c]] >= self.stars_per_region: return False
        
        # 2. Adjacency constraint
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.dim and 0 <= nc < self.dim and self.board[nr][nc] == 1:
                    return False
        return True

    def _place_star(self, r, c):
        """Places a star and updates counts."""
        self.board[r][c] = 1
        self.row_counts[r] += 1
        self.col_counts[c] += 1
        self.region_counts[self.region_grid[r][c]] += 1
    
    def _remove_star(self, r, c):
        """Removes a star and reverts counts."""
        self.board[r][c] = 0
        self.row_counts[r] -= 1
        self.col_counts[c] -= 1
        self.region_counts[self.region_grid[r][c]] -= 1

    def _backtrack(self, r, c):
        """Recursive backtracking solver."""
        if len(self.solutions) >= self.max_solutions:
            return True # Found enough solutions, terminate search

        # Base case: if we've gone past the last cell, we have a valid solution
        if r == self.dim:
            # Deepcopy is crucial to save an independent snapshot of the solution
            self.solutions.append(deepcopy(self.board))
            return len(self.solutions) >= self.max_solutions
        
        # Calculate next cell coordinates
        next_r, next_c = (r, c + 1) if c + 1 < self.dim else (r + 1, 0)

        # --- Try placing a star at (r, c) ---
        if self._is_valid_placement(r, c):
            self._place_star(r, c)
            if self._backtrack(next_r, next_c):
                return True # Propagate termination signal
            self._remove_star(r, c) # Backtrack

        # --- Try leaving (r, c) empty ---
        # Pruning: if we skip placing a star here, can we still complete the puzzle?
        # This check prevents searching dead-end paths.
        stars_placed_in_row = self.row_counts[r]
        stars_needed_in_row = self.stars_per_region - stars_placed_in_row
        remaining_cells_in_row = self.dim - (c + 1)
        
        if stars_needed_in_row <= remaining_cells_in_row:
            if self._backtrack(next_r, next_c):
                return True # Propagate termination signal

        return False # This path did not lead to a solution

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="A command-line Star Battle solver and uniqueness checker.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--size", type=int, choices=range(12), help="Puzzle size index (0-11) to fetch from the website.")
    group.add_argument("-sbn", type=str, help="A Star Battle Notation (SBN) string to solve.")
    args = parser.parse_args()

    puzzle_data = None
    if args.size is not None:
        puzzle_data = get_puzzle_from_website(args.size)
    elif args.sbn:
        puzzle_data = decode_sbn(args.sbn)
    
    if not puzzle_data or 'task' not in puzzle_data or 'stars' not in puzzle_data:
        print("\nFailed to load a valid puzzle. Exiting.")
        sys.exit(1)

    region_grid, dimension = parse_and_validate_grid(puzzle_data['task'])
    if not region_grid:
        print("\nFailed to parse puzzle grid. Exiting.")
        sys.exit(1)
        
    stars_per_region = puzzle_data['stars']
    
    display_grid_as_symbols(region_grid)
    print(f"Solving for {stars_per_region} stars per region, row, and column.")
    print("Please wait, this may take a moment for larger puzzles...")

    # --- Start Solving ---
    solver = StarBattleSolver(region_grid, stars_per_region)
    start_time = time.monotonic()
    solutions = solver.solve()
    end_time = time.monotonic()
    duration = end_time - start_time
    # --- End Solving ---

    num_solutions = len(solutions)
    
    print("\n" + "="*40)
    print("              ANALYSIS COMPLETE")
    print("="*40)
    
    if num_solutions == 0:
        print(f"RESULT: No solution found.")
    elif num_solutions == 1:
        print(f"RESULT: Found 1 unique solution.")
        display_solution(solutions[0], region_grid, "Unique Solution")
    else: # num_solutions >= 2
        print(f"RESULT: Multiple solutions exist. Found at least 2.")
        display_solution(solutions[0], region_grid, "Solution 1")
        display_solution(solutions[1], region_grid, "Solution 2")

    time_message = f"(Search stopped in {duration:.4f} seconds)" if num_solutions >= 2 else f"(Search completed in {duration:.4f} seconds)"
    print(time_message)
    print("="*40)


if __name__ == "__main__":
    main()
