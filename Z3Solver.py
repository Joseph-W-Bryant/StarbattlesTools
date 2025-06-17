# 3starbattles_solver.py (Z3-Powered Final Version)

import requests
import re
import sys
import math
import time
import argparse
import hashlib
from collections import deque, defaultdict
from copy import deepcopy
from itertools import combinations

# Z3 is a required external library
try:
    from z3 import Solver, Bool, PbEq, Implies, And, Not, Or, sat, unsat
except ImportError:
    print("Error: The 'z3-solver' library is required for this solver.")
    print("Please install it using: pip install z3-solver")
    sys.exit(1)


# --- All helper functions (get_puzzle, display, etc.) remain unchanged ---
# ... (omitted for brevity, they are the same as the previous version) ...
RESET = "\033[0m"
UNIFIED_COLORS = [
    ("Bright Red",(255,204,204),"\033[48;2;255;204;204m\033[38;2;0;0;0m"),("Bright Green",(204,255,204),"\033[48;2;204;255;204m\033[38;2;0;0;0m"),
    ("Bright Yellow",(255,255,204),"\033[48;2;255;255;204m\033[38;2;0;0;0m"),("Bright Blue",(204,229,255),"\033[48;2;204;229;255m\033[38;2;0;0;0m"),
    ("Bright Magenta",(255,204,255),"\033[48;2;255;204;255m\033[38;2;0;0;0m"),("Bright Cyan",(204,255,255),"\033[48;2;204;255;255m\033[38;2;0;0;0m"),
    ("Light Orange",(255,229,204),"\033[48;2;255;229;204m\033[38;2;0;0;0m"),("Light Purple",(229,204,255),"\033[48;2;229;204;255m\033[38;2;0;0;0m"),
    ("Light Gray",(224,224,224),"\033[48;2;224;224;224m\033[38;2;0;0;0m"),("Mint",(210,240,210),"\033[48;2;210;240;210m\033[38;2;0;0;0m"),
    ("Peach",(255,218,185),"\033[48;2;255;218;185m\033[38;2;0;0;0m"),("Sky Blue",(173,216,230),"\033[48;2;173;216;230m\033[38;2;0;0;0m"),
]
SBN_ALPHABET = {c: i for i, c in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')}
SBN_CODE_TO_DIM_MAP = {'99': 9, 'AA': 10, 'BB': 12, 'CC': 14, 'DD': 16, 'EE': 17, 'FF': 18, 'GG': 20, 'HH': 21, 'LL': 25}
BASE64_DISPLAY_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
PUZZLE_DEFINITIONS = [{'dim': 5, 'stars': 1}, {'dim': 6, 'stars': 1}, {'dim': 6, 'stars': 1}, {'dim': 8, 'stars': 2}, {'dim': 8, 'stars': 2}, {'dim': 10, 'stars': 2}, {'dim': 10, 'stars': 2}, {'dim': 14, 'stars': 3}, {'dim': 14, 'stars': 3}, {'dim': 17, 'stars': 4}, {'dim': 21, 'stars': 5}, {'dim': 25, 'stars': 6}]
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
            stars = PUZZLE_DEFINITIONS[size_selection]['stars']
            return {'task': task_match.group(1), 'stars': stars, 'solution_hash': hash_match.group(1)}
        print("Error: Could not find required puzzle data on the page."); return None
    except requests.RequestException as e: print(f"Error: Could not fetch puzzle data. {e}"); return None
def decode_sbn(sbn_string):
    print(f"Decoding SBN: {sbn_string}")
    try:
        size_code = sbn_string[0:2]; dim = SBN_CODE_TO_DIM_MAP.get(size_code)
        if not dim: print(f"Error: Unknown SBN size code '{size_code}'"); return None
        stars = int(sbn_string[2]); region_data = sbn_string[4:]
        bitfield = "".join(bin(SBN_ALPHABET[char])[2:].zfill(6) for char in region_data)
        num_borders = dim * (dim - 1); vertical_bits = bitfield[:num_borders]; horizontal_bits = bitfield[num_borders : num_borders * 2]
        region_grid = [[0] * dim for _ in range(dim)]; region_id = 1
        for r_start in range(dim):
            for c_start in range(dim):
                if region_grid[r_start][c_start] == 0:
                    q = deque([(r_start, c_start)]); region_grid[r_start][c_start] = region_id
                    while q:
                        r, c = q.popleft()
                        if r > 0 and region_grid[r-1][c] == 0 and horizontal_bits[c*(dim-1) + (r-1)] == '0': region_grid[r-1][c] = region_id; q.append((r-1, c))
                        if r < dim - 1 and region_grid[r+1][c] == 0 and horizontal_bits[c*(dim-1) + r] == '0': region_grid[r+1][c] = region_id; q.append((r+1, c))
                        if c > 0 and region_grid[r][c-1] == 0 and vertical_bits[r*(dim-1) + (c-1)] == '0': region_grid[r][c-1] = region_id; q.append((r, c-1))
                        if c < dim - 1 and region_grid[r][c+1] == 0 and vertical_bits[r*(dim-1) + c] == '0': region_grid[r][c+1] = region_id; q.append((r, c+1))
                    region_id += 1
        task_string = ",".join(str(cell) for row in region_grid for cell in row)
        print(f"SBN decoded successfully to a {dim}x{dim} grid with {stars} stars.")
        return {'task': task_string, 'stars': stars, 'solution_hash': None}
    except (KeyError, IndexError, ValueError) as e: print(f"Error decoding SBN: Invalid format. {e}"); return None
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
def display_grid_as_symbols(grid, title="--- Puzzle Regions ---"):
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
def validate_solution_with_hash(solution_grid, puzzle_data):
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

class Z3StarBattleSolver:
    def __init__(self, region_grid, stars_per_region):
        self.region_grid = region_grid
        self.dim = len(region_grid)
        self.stars_per_region = stars_per_region

    def solve(self):
        s = Solver()
        
        # 1. Create a boolean variable for each cell
        grid_vars = [[Bool(f"cell_{r}_{c}") for c in range(self.dim)] for r in range(self.dim)]

        # 2. Add Row and Column constraints
        # "Exactly N stars per row/column"
        for i in range(self.dim):
            s.add(PbEq([(var, 1) for var in grid_vars[i]], self.stars_per_region)) # Row
            s.add(PbEq([(grid_vars[r][i], 1) for r in range(self.dim)], self.stars_per_region)) # Column

        # 3. Add Region constraints
        regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim):
                regions[self.region_grid[r][c]].append(grid_vars[r][c])
        
        for region_vars in regions.values():
            s.add(PbEq([(var, 1) for var in region_vars], self.stars_per_region))

        # 4. Add Adjacency constraints
        # "If a cell is a star, its neighbors are not"
        for r in range(self.dim):
            for c in range(self.dim):
                neighbors = []
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0: continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.dim and 0 <= nc < self.dim:
                            neighbors.append(Not(grid_vars[nr][nc]))
                s.add(Implies(grid_vars[r][c], And(neighbors)))

        solutions = []
        
        # --- First Solve Attempt ---
        if s.check() == sat:
            model = s.model()
            solution_board = [[(1 if model.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
            solutions.append(solution_board)

            # --- Second Solve Attempt (for uniqueness) ---
            # Create a "blocking clause" that forbids the exact solution we just found
            blocking_clause = []
            for r in range(self.dim):
                for c in range(self.dim):
                    if solution_board[r][c] == 1:
                        blocking_clause.append(Not(grid_vars[r][c]))
                    else:
                        blocking_clause.append(grid_vars[r][c])
            s.add(Or(blocking_clause))
            
            # Check for a second, different solution
            if s.check() == sat:
                model = s.model()
                solution_board_2 = [[(1 if model.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
                solutions.append(solution_board_2)

        return solutions, {} # Return empty dict for stats, as they aren't applicable

def main():
    parser = argparse.ArgumentParser(description="A command-line Star Battle solver and uniqueness checker.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--size", type=int, choices=range(12), help="Puzzle size index (0-11).")
    group.add_argument("-sbn", type=str, help="A Star Battle Notation (SBN) string.")
    args = parser.parse_args()

    puzzle_data = get_puzzle_from_website(args.size) if args.size is not None else decode_sbn(args.sbn)
    if not puzzle_data or 'task' not in puzzle_data or 'stars' not in puzzle_data:
        print("\nFailed to load a valid puzzle. Exiting."); sys.exit(1)
        
    region_grid, dimension = parse_and_validate_grid(puzzle_data['task'])
    if not region_grid:
        print("\nFailed to parse puzzle grid. Exiting."); sys.exit(1)
    stars_per_region = puzzle_data['stars']
    
    display_grid_as_symbols(region_grid)
    print(f"Solving for {stars_per_region} stars per region, row, and column.")
    print("Please wait, using Z3 SMT solver...")
    
    # --- Using the Z3 Solver ---
    solver = Z3StarBattleSolver(region_grid, stars_per_region)
    start_time = time.monotonic()
    solutions, _ = solver.solve() # Stats are not generated by this solver
    end_time = time.monotonic()
    duration = end_time - start_time
    num_solutions = len(solutions)
    
    print("\n" + "="*40)
    print("              ANALYSIS COMPLETE")
    print("="*40)
    
    if num_solutions == 0:
        print(f"RESULT: No solution found.")
    elif num_solutions == 1:
        print(f"RESULT: Found 1 unique solution.")
        validate_solution_with_hash(solutions[0], puzzle_data)
        display_solution(solutions[0], region_grid, "Unique Solution")
    else:
        print(f"RESULT: Multiple solutions exist. Found at least 2.")
        print("-" * 20)
        validate_solution_with_hash(solutions[0], puzzle_data)
        display_solution(solutions[0], region_grid, "Solution 1")
        print("-" * 20)
        validate_solution_with_hash(solutions[1], puzzle_data)
        display_solution(solutions[1], region_grid, "Solution 2")
    
    print("--- Solver Statistics ---")
    search_status = "Search completed" if num_solutions < 2 else "Search stopped (multiple solutions found)"
    print(f"{'Status':<25}: {search_status}")
    print(f"{'Total solve time':<25}: {format_duration(duration)}")
    print("="*40)

if __name__ == "__main__":
    main()
