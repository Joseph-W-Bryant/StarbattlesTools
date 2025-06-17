# 3starbattles_solver.py (Final Confirmed Working Version)

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

# --- Global Debug Variables ---
DEBUG_MODE = False
DEBUG_LOG_FILE = None

# --- Constants & Utilities ---
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
EMPTY, STAR, ELIMINATED = 0, 1, -1

# --- Debug Helpers ---
def debug_print(message, indent_level=0):
    if DEBUG_MODE and DEBUG_LOG_FILE:
        print("  " * indent_level + message, file=DEBUG_LOG_FILE)

def debug_print_board(board, indent_level):
    if not (DEBUG_MODE and DEBUG_LOG_FILE): return
    debug_print("Board state:", indent_level)
    for r in range(len(board)):
        row_str = " ".join([f"{'S' if c == STAR else ('X' if c == ELIMINATED else '.'):>1}" for c in board[r]])
        debug_print(f"  {row_str}", indent_level)

# --- Puzzle Acquisition & Display Functions ---
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

# --- Solver Class with Definitive Fix ---
class AdvancedStarBattleSolver:
    def __init__(self, region_grid, stars_per_region):
        self.region_grid = region_grid; self.dim = len(region_grid)
        self.stars_per_region = stars_per_region; self.solutions = []
        self.max_solutions = 2; self.regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim): self.regions[self.region_grid[r][c]].append((r, c))
        self.sorted_region_keys = sorted(self.regions.keys(), key=lambda k: len(self.regions[k]))

    def solve(self):
        initial_board = [[EMPTY] * self.dim for _ in range(self.dim)]
        unsolved_regions = set(self.sorted_region_keys)
        self._backtrack(initial_board, unsolved_regions, 0)
        return self.solutions
        
    def _is_placement_valid(self, r, c, board):
        """Checks if placing a SINGLE star at (r, c) is valid given the current board state."""
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.dim and 0 <= nc < self.dim and board[nr][nc] == STAR:
                    return False
        return True

    def _propagate_constraints(self, board, depth):
        made_change = True
        while made_change:
            made_change = False
            # 1. Eliminate cells adjacent to stars
            for r in range(self.dim):
                for c in range(self.dim):
                    if board[r][c] == STAR:
                        for dr in range(-1, 2):
                            for dc in range(-1, 2):
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < self.dim and 0 <= nc < self.dim and board[nr][nc] == EMPTY:
                                    board[nr][nc] = ELIMINATED; made_change = True
            
            # 2. Eliminate cells in full rows/cols
            for i in range(self.dim):
                row_stars = sum(1 for c in range(self.dim) if board[i][c] == STAR)
                if row_stars == self.stars_per_region:
                    for c in range(self.dim):
                        if board[i][c] == EMPTY: board[i][c] = ELIMINATED; made_change = True
                elif row_stars > self.stars_per_region: return None

                col_stars = sum(1 for r in range(self.dim) if board[r][i] == STAR)
                if col_stars == self.stars_per_region:
                    for r in range(self.dim):
                        if board[r][i] == EMPTY: board[r][i] = ELIMINATED; made_change = True
                elif col_stars > self.stars_per_region: return None
            
            # 3. Handle regions (forced placements and eliminations)
            for region_id in self.regions:
                region_cells = self.regions[region_id]
                star_count = sum(1 for r, c in region_cells if board[r][c] == STAR)
                empty_cells = [(r, c) for r, c in region_cells if board[r][c] == EMPTY]
                
                if star_count > self.stars_per_region: return None
                
                if star_count == self.stars_per_region:
                    for r, c in empty_cells:
                        if board[r][c] == EMPTY: board[r][c] = ELIMINATED; made_change = True
                elif star_count + len(empty_cells) < self.stars_per_region: return None
                elif star_count + len(empty_cells) == self.stars_per_region:
                    # *** The Definitive Adjacency Fix ***
                    # Before making a forced placement, check if it's valid against the current board.
                    for r_force, c_force in empty_cells:
                        if not self._is_placement_valid(r_force, c_force, board):
                            debug_print(f"\033[91m[CONTRADICTION]\033[0m Forced move at ({r_force},{c_force}) is adjacent to an existing star.", depth+1)
                            return None # This is a contradiction, so the path is invalid.
                        board[r_force][c_force] = STAR; made_change = True
        return board
    
    def _backtrack(self, board, unsolved_regions, depth):
        debug_print(f"[ENTRY] Backtrack at depth {depth}", depth)
        
        board = self._propagate_constraints(deepcopy(board), depth)
        if board is None:
            debug_print(f"[EXIT] Contradiction found during propagation.", depth)
            return
        
        debug_print_board(board, depth)

        if not unsolved_regions:
            if sum(row.count(STAR) for row in board) == self.dim * self.stars_per_region:
                solution_board = [[(1 if cell == STAR else 0) for cell in row] for row in board]
                debug_print(f"\033[96m[SOLUTION FOUND]\033[0m", depth)
                self.solutions.append(solution_board)
            else:
                debug_print(f"[EXIT] End of line, but incorrect star count.", depth)
            return

        region_id = min(unsolved_regions, key=lambda rid: len([1 for r, c in self.regions[rid] if board[r][c] == EMPTY]))
        debug_print(f"[DECISION] Solving for region {region_id}", depth)
        
        region_cells = self.regions[region_id]
        stars_placed = sum(1 for r, c in region_cells if board[r][c] == STAR)
        stars_to_place = self.stars_per_region - stars_placed
        available_cells = [(r, c) for r, c in region_cells if board[r][c] == EMPTY]
        
        if stars_to_place < 0 or stars_to_place > len(available_cells):
            debug_print(f"[EXIT] Impossible placement: {stars_to_place} stars needed, {len(available_cells)} available.", depth)
            return
        
        for combo in combinations(available_cells, stars_to_place):
            temp_board = deepcopy(board)
            is_valid_combo = True
            
            # Incrementally build and check the combo on a temporary board
            for r_new, c_new in combo:
                if not self._is_placement_valid(r_new, c_new, temp_board):
                    is_valid_combo = False
                    break
                # If valid, place it on the temp board for the *next* check in this combo
                temp_board[r_new][c_new] = STAR
            
            if not is_valid_combo:
                debug_print(f"\033[91m[FAIL]\033[0m Combo {combo} is invalid.", depth)
                continue
            
            debug_print(f"\033[92m[PASS]\033[0m Combo {combo} is valid. Recursing.", depth)
            
            next_unsolved = unsolved_regions - {region_id}
            self._backtrack(temp_board, next_unsolved, depth + 1)
            
            if len(self.solutions) >= self.max_solutions:
                debug_print(f"[EXIT] Max solutions found. Terminating branch.", depth)
                return

# --- Main Execution ---
def main():
    global DEBUG_MODE, DEBUG_LOG_FILE
    parser = argparse.ArgumentParser(description="A command-line Star Battle solver and uniqueness checker.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--size", type=int, choices=range(12), help="Puzzle size index (0-11).")
    group.add_argument("-sbn", type=str, help="A Star Battle Notation (SBN) string.")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging to debug_log.txt.")
    args = parser.parse_args()

    original_stdout = sys.stdout
    if args.debug:
        DEBUG_MODE = True
        try:
            DEBUG_LOG_FILE = open("debug_log.txt", "w")
            print("Debug mode enabled. Logging to debug_log.txt", file=original_stdout)
        except IOError as e:
            print(f"Error: Could not open debug_log.txt for writing: {e}", file=original_stdout)
            sys.exit(1)

    try:
        puzzle_data = get_puzzle_from_website(args.size) if args.size is not None else decode_sbn(args.sbn)
        if not puzzle_data or 'task' not in puzzle_data or 'stars' not in puzzle_data:
            print("\nFailed to load a valid puzzle. Exiting.", file=original_stdout); sys.exit(1)
        region_grid, dimension = parse_and_validate_grid(puzzle_data['task'])
        if not region_grid: print("\nFailed to parse puzzle grid. Exiting.", file=original_stdout); sys.exit(1)
        stars_per_region = puzzle_data['stars']
        
        display_grid_as_symbols(region_grid)
        print(f"Solving for {stars_per_region} stars per region, row, and column.", file=original_stdout)
        if not DEBUG_MODE: print("Please wait, this may take a moment for larger puzzles...", file=original_stdout)
        
        solver = AdvancedStarBattleSolver(region_grid, stars_per_region)
        start_time = time.monotonic()
        solutions = solver.solve()
        end_time = time.monotonic()
        duration = end_time - start_time
        num_solutions = len(solutions)
        
        print("\n" + "="*40, file=original_stdout)
        print("              ANALYSIS COMPLETE", file=original_stdout)
        print("="*40, file=original_stdout)
        
        if num_solutions == 0:
            print(f"RESULT: No solution found.", file=original_stdout)
        elif num_solutions == 1:
            print(f"RESULT: Found 1 unique solution.", file=original_stdout)
            validate_solution_with_hash(solutions[0], puzzle_data)
            display_solution(solutions[0], region_grid, "Unique Solution")
        else:
            print(f"RESULT: Multiple solutions exist. Found at least 2.", file=original_stdout)
            print("-" * 20, file=original_stdout)
            validate_solution_with_hash(solutions[0], puzzle_data)
            display_solution(solutions[0], region_grid, "Solution 1")
            print("-" * 20, file=original_stdout)
            validate_solution_with_hash(solutions[1], puzzle_data)
            display_solution(solutions[1], region_grid, "Solution 2")
        
        time_msg = f"(Search stopped in {duration:.4f} seconds)" if num_solutions >= 2 else f"(Search completed in {duration:.4f} seconds)"
        print(time_msg, file=original_stdout)
        print("="*40, file=original_stdout)

    finally:
        if DEBUG_LOG_FILE:
            DEBUG_LOG_FILE.close()

if __name__ == "__main__":
    main()
