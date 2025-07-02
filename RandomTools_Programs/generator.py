# starbattle_generator.py
#
# Author: Gemini
# Date: Today's Date
#
# Description:
# A command-line tool for generating unique Star Battle puzzles.
# It uses a backtracking algorithm to create a valid solution, then
# partitions the grid into regions using a randomized merging algorithm.
# Each generated puzzle is validated using a Z3 SMT solver to ensure
# it has exactly one unique solution. Finally, its difficulty is
# estimated by a simple logical solver.
#
# Usage:
# python starbattle_generator.py [dim] [stars]
#
# Example:
# python starbattle_generator.py 10 2
#
# If no arguments are provided, it defaults to an 8x8, 1-star puzzle.

import sys
import random
import time
import math
from collections import deque, defaultdict

# --- Z3 Solver Integration ---
Z3_AVAILABLE = False
try:
    from z3 import Solver, Bool, PbEq, Implies, And, Not, Or, sat
    Z3_AVAILABLE = True
except ImportError:
    print("Warning: 'z3-solver' library not found. The generator requires Z3 to verify puzzles.")
    print("To install it, run: pip install z3-solver")
    sys.exit(1)

# --- Constants for Display and SBN Encoding (from original player) ---
UNIFIED_COLORS_BG = [
    ("Bright Red",(255,204,204),"\033[48;2;255;204;204m\033[38;2;0;0;0m"),("Bright Green",(204,255,204),"\033[48;2;204;255;204m\033[38;2;0;0;0m"),
    ("Bright Yellow",(255,255,204),"\033[48;2;255;255;204m\033[38;2;0;0;0m"),("Bright Blue",(204,229,255),"\033[48;2;204;229;255m\033[38;2;0;0;0m"),
    ("Bright Magenta",(255,204,255),"\033[48;2;255;204;255m\033[38;2;0;0;0m"),("Bright Cyan",(204,255,255),"\033[48;2;204;255;255m\033[38;2;0;0;0m"),
    ("Light Orange",(255,229,204),"\033[48;2;255;229;204m\033[38;2;0;0;0m"),("Light Purple",(229,204,255),"\033[48;2;229;204;255m\033[38;2;0;0;0m"),
    ("Light Gray",(224,224,224),"\033[48;2;224;224;224m\033[38;2;0;0;0m"),("Mint",(210,240,210),"\033[48;2;210;240;210m\033[38;2;0;0;0m"),
    ("Peach",(255,218,185),"\033[48;2;255;218;185m\033[38;2;0;0;0m"),("Sky Blue",(173,216,230),"\033[48;2;173;216;230m\033[38;2;0;0;0m"),
]
SBN_B64_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
SBN_INT_TO_CHAR = {i: c for i, c in enumerate(SBN_B64_ALPHABET)}
BASE64_DISPLAY_ALPHABET = SBN_B64_ALPHABET
DIM_TO_SBN_CODE_MAP = {
    5: '55', 6: '66', 7: '77', 8: '88', 9: '99', 10: 'AA', 11: 'BB', 12: 'CC', 13: 'DD',
    14: 'EE', 15: 'FF', 16: 'GG', 17: 'HH', 18: 'II', 19: 'JJ', 20: 'KK', 21: 'LL', 22: 'MM',
    23: 'NN', 24: 'OO', 25: 'PP'
}

# --- Z3 SOLVER (Adapted from Z3AndPlayer.py) ---
class Z3StarBattleSolver:
    """A class to solve Star Battle puzzles using the Z3 SMT solver."""
    def __init__(self, region_grid, stars_per_region):
        self.region_grid = region_grid
        self.dim = len(region_grid)
        self.stars_per_region = stars_per_region

    def solve_and_count(self):
        s = Solver()
        grid_vars = [[Bool(f"cell_{r}_{c}") for c in range(self.dim)] for r in range(self.dim)]

        for i in range(self.dim):
            s.add(PbEq([(var, 1) for var in grid_vars[i]], self.stars_per_region))
            s.add(PbEq([(grid_vars[r][i], 1) for r in range(self.dim)], self.stars_per_region))

        regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim):
                regions[self.region_grid[r][c]].append(grid_vars[r][c])
        for region_vars in regions.values():
            s.add(PbEq([(var, 1) for var in region_vars], self.stars_per_region))

        for r in range(self.dim):
            for c in range(self.dim):
                neighbors = [Not(grid_vars[nr][nc]) for dr in [-1, 0, 1] for dc in [-1, 0, 1] if not (dr == 0 and dc == 0) and 0 <= (nr := r + dr) < self.dim and 0 <= (nc := c + dc) < self.dim]
                s.add(Implies(grid_vars[r][c], And(neighbors)))

        solutions, count = [], 0
        while s.check() == sat and count < 2:
            count += 1
            model = s.model()
            solution_board = [[(1 if model.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
            solutions.append(solution_board)
            blocking_clause = Or([grid_vars[r][c] != bool(val) for r, row in enumerate(solution_board) for c, val in enumerate(row)])
            s.add(blocking_clause)

        return count, solutions[0] if solutions else None

# --- SOLUTION GRID GENERATOR ---
def generate_solution_grid(dim, stars_per_row_col):
    grid = [[0] * dim for _ in range(dim)]
    row_counts, col_counts = [0] * dim, [0] * dim

    def is_valid(r, c):
        if row_counts[r] >= stars_per_row_col or col_counts[c] >= stars_per_row_col: return False
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < dim and 0 <= nc < dim and grid[nr][nc] == 1: return False
        return True
    
    def solve_deterministic(cell_index=0):
        if cell_index == dim*dim:
            return sum(row_counts) == dim * stars_per_row_col

        r,c = divmod(cell_index, dim)
        
        # Try placing a star
        if is_valid(r,c):
            grid[r][c] = 1
            row_counts[r] += 1; col_counts[c] += 1
            if solve_deterministic(cell_index + 1): return True
            grid[r][c] = 0 # backtrack
            row_counts[r] -= 1; col_counts[c] -= 1

        # Try not placing a star
        if solve_deterministic(cell_index+1): return True
        return False

    if solve_deterministic(): return grid
    return None

# --- REGION GENERATOR ---
def generate_regions(solution_grid, stars_per_region):
    dim = len(solution_grid)
    region_grid = [[(r * dim + c) + 1 for c in range(dim)] for r in range(dim)]
    star_counts = defaultdict(int)

    for r in range(dim):
        for c in range(dim):
            if solution_grid[r][c] == 1:
                star_counts[region_grid[r][c]] = 1

    borders = []
    for r in range(dim):
        for c in range(dim):
            if r < dim - 1: borders.append(((r, c), (r + 1, c)))
            if c < dim - 1: borders.append(((r, c), (r, c + 1)))
    random.shuffle(borders)

    parent = {i + 1: i + 1 for i in range(dim * dim)}
    def find_root(cell_id):
        if parent[cell_id] == cell_id: return cell_id
        parent[cell_id] = find_root(parent[cell_id])
        return parent[cell_id]

    for (r1, c1), (r2, c2) in borders:
        id1, id2 = region_grid[r1][c1], region_grid[r2][c2]
        root1, root2 = find_root(id1), find_root(id2)
        if root1 != root2 and star_counts[root1] + star_counts[root2] <= stars_per_region:
            parent[root2] = root1
            star_counts[root1] += star_counts[root2]
            star_counts[root2] = 0

    final_regions, final_id = {}, 1
    final_region_grid = [[0] * dim for _ in range(dim)]
    for r in range(dim):
        for c in range(dim):
            root = find_root(region_grid[r][c])
            if root not in final_regions:
                final_regions[root] = final_id
                final_id += 1
            final_region_grid[r][c] = final_regions[root]
    return final_region_grid

# --- DIFFICULTY ESTIMATOR ---
def estimate_difficulty(region_grid, stars_per_region):
    dim = len(region_grid)
    board = [[0] * dim for _ in range(dim)] # 0: unknown, 1: star, 2: empty/X
    
    determined_cells = 0
    while True:
        newly_determined = 0
        for r in range(dim):
            for c in range(dim):
                if board[r][c] == 1:
                    for dr in [-1,0,1]:
                        for dc in [-1,0,1]:
                            nr, nc = r+dr, c+dc
                            if 0 <= nr < dim and 0 <= nc < dim and board[nr][nc] == 0:
                                board[nr][nc] = 2; newly_determined += 1
        
        row_stars, col_stars = [0]*dim, [0]*dim
        region_stars = defaultdict(int)
        row_unknown, col_unknown = [0]*dim, [0]*dim
        region_unknown = defaultdict(int)
        regions = defaultdict(list)

        for r in range(dim):
            for c in range(dim):
                regions[region_grid[r][c]].append((r,c))
                if board[r][c] == 1:
                    row_stars[r] += 1; col_stars[c] += 1; region_stars[region_grid[r][c]] += 1
                elif board[r][c] == 0:
                    row_unknown[r] += 1; col_unknown[c] += 1; region_unknown[region_grid[r][c]] += 1

        for i in range(dim):
            if row_stars[i] == stars_per_region:
                for c in range(dim):
                    if board[i][c] == 0: board[i][c] = 2; newly_determined += 1
            if col_stars[i] == stars_per_region:
                for r in range(dim):
                    if board[r][c] == 0: board[r][c] = 2; newly_determined += 1
        for rid, cells in regions.items():
            if region_stars[rid] == stars_per_region:
                for r_cell,c_cell in cells:
                    if board[r_cell][c_cell] == 0: board[r_cell][c_cell] = 2; newly_determined += 1
        
        for i in range(dim):
            if row_stars[i] + row_unknown[i] == stars_per_region and row_unknown[i] > 0:
                for c in range(dim):
                    if board[i][c] == 0: board[i][c] = 1; newly_determined += 1
            if col_stars[i] + col_unknown[i] == stars_per_region and col_unknown[i] > 0:
                for r in range(dim):
                    if board[r][c] == 0: board[r][c] = 1; newly_determined += 1
        for rid, cells in regions.items():
            if region_stars[rid] + region_unknown[rid] == stars_per_region and region_unknown[rid] > 0:
                for r_cell,c_cell in cells:
                    if board[r_cell][c_cell] == 0: board[r_cell][c_cell] = 1; newly_determined += 1

        if newly_determined == 0: break
        determined_cells += newly_determined
        
    score = (dim * dim - determined_cells) / (dim * dim)
    if score < 0.1: return "Very Easy"
    if score < 0.25: return "Easy"
    if score < 0.4: return "Medium"
    if score < 0.6: return "Hard"
    return "Very Hard"

# --- EXPORT AND DISPLAY ---
def encode_to_sbn(region_grid, stars):
    dim = len(region_grid)
    sbn_code = DIM_TO_SBN_CODE_MAP.get(dim)
    if not sbn_code: return "N/A"

    vertical_bits = ['1' if region_grid[r][c] != region_grid[r][c+1] else '0' for r in range(dim) for c in range(dim - 1)]
    horizontal_bits = ['1' if region_grid[r][c] != region_grid[r+1][c] else '0' for c in range(dim) for r in range(dim - 1)]
    clean_bitfield = "".join(vertical_bits) + "".join(horizontal_bits)
    
    padding_bits = (6 - (len(clean_bitfield) % 6)) % 6
    padded_bitfield = ('0' * padding_bits) + clean_bitfield
    
    region_data_chars = [SBN_INT_TO_CHAR[int(padded_bitfield[i:i+6], 2)] for i in range(0, len(padded_bitfield), 6)]
    region_data = "".join(region_data_chars)
    
    return f"{sbn_code}{stars}W{region_data}"

def display_terminal_grid(grid, title, content_grid=None):
    """Prints a colorized representation of the grid to the terminal."""
    if not grid: return
    RESET = "\033[0m"; print(f"\n--- {title} ---")
    dim = len(grid)
    for r in range(dim):
        colored_chars = []
        for c in range(dim):
            region_num = grid[r][c]
            color_ansi = UNIFIED_COLORS_BG[(region_num - 1) % len(UNIFIED_COLORS_BG)][2]
            symbol = '★' if content_grid and content_grid[r][c] == 1 else BASE64_DISPLAY_ALPHABET[(region_num - 1) % len(BASE64_DISPLAY_ALPHABET)]
            colored_chars.append(f"{color_ansi} {symbol} {RESET}")
        print("".join(colored_chars))
    print("-" * (dim * 4))

# --- MAIN GENERATION ORCHESTRATOR ---
def generate_puzzle(dim, stars):
    print(f"Attempting to generate a {dim}x{dim} puzzle with {stars} stars...")
    start_time = time.time()
    
    solution = generate_solution_grid(dim, stars)
    if not solution:
        print("Failed to generate an initial solution grid.")
        return None
    
    attempts = 0
    while True:
        attempts += 1
        if attempts > 100:
            print("\nCould not generate a unique puzzle after 100 attempts. Retrying with a new solution grid...")
            solution = generate_solution_grid(dim, stars)
            if not solution:
                print("Failed to generate a new solution grid. Aborting.")
                return None
            attempts = 1
        
        print(f"Generation Attempt #{attempts}...")
        regions = generate_regions(solution, stars)
        solver = Z3StarBattleSolver(regions, stars)
        num_solutions, first_solution = solver.solve_and_count()
        
        if num_solutions == 1:
            print(f"SUCCESS! Found a unique puzzle after {attempts} attempts.")
            end_time = time.time()
            difficulty = estimate_difficulty(regions, stars)
            print(f"Generation took {end_time - start_time:.2f} seconds.")
            return regions, solution, difficulty
        else:
            print(f"  > Discarding puzzle. Found {num_solutions} solutions.")

def main():
    if len(sys.argv) == 3:
        try:
            dim, stars = int(sys.argv[1]), int(sys.argv[2])
        except ValueError:
            print("Invalid arguments. Please provide integers."); sys.exit(1)
    else:
        print("Usage: python starbattle_generator.py [dim] [stars]\nDefaulting to 8x8, 1-star puzzle.")
        dim, stars = 8, 1

    result = generate_puzzle(dim, stars)
    
    if result:
        region_grid, solution_grid, difficulty = result
        display_terminal_grid(region_grid, "Generated Puzzle Regions")
        display_terminal_grid(region_grid, "Unique Solution", content_grid=solution_grid)
        
        web_task_string = ",".join(str(cell) for row in region_grid for cell in row)
        sbn_string = encode_to_sbn(region_grid, stars)
        
        print(f"\nEstimated Difficulty: {difficulty}")
        print("\n--- EXPORT FORMATS ---")
        print(f"Web Task String: {web_task_string}")
        print(f"SBN String:      {sbn_string}")

if __name__ == "__main__":
    main()

