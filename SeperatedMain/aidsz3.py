# standalone_sbn_validator.py
# Description: A self-contained script to read an SBN puzzle file,
# validate each puzzle using the Z3 solver, and output the SBNs
# for all puzzles with exactly one unique solution.

import sys
import math
import time
from collections import deque, defaultdict

# --- Z3 Solver Integration ---
# All necessary Z3 components are included here.
try:
    from z3 import Solver, Bool, PbEq, Implies, And, Not, Or, sat
    Z3_AVAILABLE = True
except ImportError:
    # If Z3 is not installed, the script will fail gracefully.
    Z3_AVAILABLE = False
    # Define dummy classes to prevent crashes during script definition
    class Solver: pass
    def Bool(s): return None
    def PbEq(s, i): return None
    def Implies(a, b): return None
    def And(s): return None
    def Not(s): return None
    def Or(s): return None
    sat = "sat"

# --- Helper Functions ---

def format_duration(seconds):
    """Formats a duration in seconds into a human-readable string."""
    if seconds >= 1: return f"{seconds:.3f} s"
    if seconds >= 0.001: return f"{seconds * 1000:.2f} ms"
    return f"{seconds * 1_000_000:.2f} µs"

# --- SBN Format Constants & Decoding Logic ---

SBN_B64_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-'
SBN_CHAR_TO_INT = {char: i for i, char in enumerate(SBN_B64_ALPHABET)}
SBN_CODE_TO_DIM_MAP = {
    '55': 5, '66': 6, '77': 7, '88': 8, '99': 9, 'AA': 10,
    'BB': 11, 'CC': 12, 'DD': 13, 'EE': 14, 'FF': 15, 'GG': 16
}

def reconstruct_grid_from_borders(dim, vertical_bits, horizontal_bits):
    """Rebuilds the region grid using a flood-fill algorithm based on border data."""
    region_grid = [[0] * dim for _ in range(dim)]
    region_id_counter = 1
    for r_start in range(dim):
        for c_start in range(dim):
            if region_grid[r_start][c_start] == 0:
                q = deque([(r_start, c_start)])
                region_grid[r_start][c_start] = region_id_counter
                while q:
                    r, c = q.popleft()
                    # Check neighbors, flooding into cells not separated by a border
                    if c < dim - 1 and region_grid[r][c+1] == 0 and vertical_bits[r*(dim-1) + c] == '0':
                        region_grid[r][c+1] = region_id_counter; q.append((r, c+1))
                    if c > 0 and region_grid[r][c-1] == 0 and vertical_bits[r*(dim-1) + (c-1)] == '0':
                        region_grid[r][c-1] = region_id_counter; q.append((r, c-1))
                    if r < dim - 1 and region_grid[r+1][c] == 0 and horizontal_bits[c*(dim-1) + r] == '0':
                        region_grid[r+1][c] = region_id_counter; q.append((r+1, c))
                    if r > 0 and region_grid[r-1][c] == 0 and horizontal_bits[c*(dim-1) + (r-1)] == '0':
                        region_grid[r-1][c] = region_id_counter; q.append((r-1, c))
                region_id_counter += 1
    return region_grid

def decode_sbn_string(sbn_string):
    """
    Decodes a single SBN string into a region grid and star count.
    Returns a tuple: (region_grid, stars_per_region) or (None, None).
    """
    sbn_string = sbn_string.strip()
    if len(sbn_string) < 4: return None, None
        
    try:
        size_code = sbn_string[0:2]
        dim = SBN_CODE_TO_DIM_MAP.get(size_code)
        if not dim: return None, None
        
        stars = int(sbn_string[2])
        border_bits_needed = 2 * dim * (dim - 1)
        border_chars_needed = math.ceil(border_bits_needed / 6)
        
        region_data_str = sbn_string[4 : 4 + border_chars_needed]
        
        full_bitfield = "".join(bin(SBN_CHAR_TO_INT.get(char, 0))[2:].zfill(6) for char in region_data_str)
        border_data = full_bitfield[len(full_bitfield) - border_bits_needed:]
        
        v_bits = border_data[0 : dim * (dim - 1)]
        h_bits = border_data[dim * (dim - 1) : border_bits_needed]
        
        region_grid = reconstruct_grid_from_borders(dim, v_bits, h_bits)
        return region_grid, stars
    except (KeyError, IndexError, ValueError) as e:
        print(f"\n\033[93mWarning: Failed to parse SBN: '{sbn_string[:20]}...'. Error: {e}\033[0m", file=sys.stderr)
        return None, None

# --- Z3 Solver Class ---

class Z3StarBattleSolver:
    """A class to solve Star Battle puzzles using the Z3 SMT solver."""
    def __init__(self, region_grid, stars_per_region):
        self.region_grid = region_grid
        self.dim = len(region_grid)
        self.stars_per_region = stars_per_region

    def solve(self):
        """Sets up and runs the Z3 solver to find up to two solutions."""
        if not Z3_AVAILABLE: return []
        
        s = Solver()
        grid_vars = [[Bool(f"cell_{r}_{c}") for c in range(self.dim)] for r in range(self.dim)]
        
        # Rule 1: Exactly N stars per row and N stars per column
        for i in range(self.dim):
            s.add(PbEq([(var, 1) for var in grid_vars[i]], self.stars_per_region))
            s.add(PbEq([(grid_vars[r][i], 1) for r in range(self.dim)], self.stars_per_region))
            
        # Rule 2: Exactly N stars per region
        regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim):
                regions[self.region_grid[r][c]].append(grid_vars[r][c])
        for region_vars in regions.values():
            s.add(PbEq([(var, 1) for var in region_vars], self.stars_per_region))
            
        # Rule 3: Stars cannot be adjacent (including diagonally)
        for r in range(self.dim):
            for c in range(self.dim):
                neighbors = []
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0: continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.dim and 0 <= nc < self.dim:
                            neighbors.append(Not(grid_vars[nr][nc]))
                s.add(Implies(grid_vars[r][c], And(neighbors)))
        
        solutions = []
        if s.check() == sat:
            # First solution found
            m1 = s.model()
            sol1 = [[(1 if m1.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
            solutions.append(sol1)
            
            # Block the first solution to check for a second one
            block_clause = Or([grid_vars[r][c] if sol1[r][c] == 0 else Not(grid_vars[r][c]) for r in range(self.dim) for c in range(self.dim)])
            s.add(block_clause)
            
            if s.check() == sat:
                # Second solution found, puzzle is not unique
                m2 = s.model()
                sol2 = [[(1 if m2.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
                solutions.append(sol2)
                
        return solutions

# --- Main Execution Block ---

def main(filename):
    """
    Main function to read a file of SBNs, solve them, and report results.
    """
    if not Z3_AVAILABLE:
        print("\033[91mFatal Error: Z3 Solver library is not installed.\033[0m", file=sys.stderr)
        print("Please install it by running: pip install z3-solver", file=sys.stderr)
        return

    try:
        with open(filename, 'r') as f:
            puzzles = f.readlines()
    except FileNotFoundError:
        print(f"\033[91mError: The file '{filename}' was not found.\033[0m", file=sys.stderr)
        return

    print(f"Found {len(puzzles)} puzzles in '{filename}'. Starting analysis...\n")
    
    total_start_time = time.perf_counter()
    results = {0: 0, 1: 0, 2: 0, "error": 0}
    single_solution_puzzles = []

    for i, sbn_line in enumerate(puzzles):
        sbn_string = sbn_line.strip()
        if not sbn_string: continue

        progress = f"Testing Puzzle #{i+1}/{len(puzzles)}..."
        print(f"\r{progress:<30}", end="")
        
        region_grid, stars = decode_sbn_string(sbn_string)
        
        if not region_grid:
            results["error"] += 1
            continue

        solver = Z3StarBattleSolver(region_grid, stars)
        solutions = solver.solve()
        num_solutions = len(solutions)

        if num_solutions == 1:
            results[1] += 1
            single_solution_puzzles.append(sbn_string)
        elif num_solutions == 0:
            results[0] += 1
        else: # 2 or more solutions
            results[2] += 1
    
    total_end_time = time.perf_counter()
    total_duration_str = format_duration(total_end_time - total_start_time)
    
    # --- Final Summary ---
    print(f"\r{'Analysis Complete!':<30}") # Clear progress line
    print("\n" + "="*40)
    print("           Validation Summary")
    print("="*40)
    print(f"Total time taken: {total_duration_str}")
    print(f"Puzzles with 1 solution (Valid):   {results[1]}")
    print(f"Puzzles with 2+ solutions (Ambiguous): {results[2]}")
    print(f"Puzzles with 0 solutions (Unsolvable):  {results[0]}")
    if results["error"] > 0:
        print(f"Puzzles that failed to parse: {results['error']}")
    print("="*40)
    
    # --- Export Single-Solution Puzzles ---
    if single_solution_puzzles:
        print("\n" + "="*40)
        print("     SBN Codes of Valid Puzzles (1 Solution)")
        print("="*40)
        for sbn_str in single_solution_puzzles:
            print(sbn_str)
        print("="*40)
    else:
        print("\nNo puzzles with a unique solution were found in the provided file.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\033[91mUsage: python standalone_sbn_validator.py <path_to_sbn_file>\033[0m", file=sys.stderr)
        print("Example: python standalone_sbn_validator.py aids.txt", file=sys.stderr)
        sys.exit(1)
    
    input_filename = sys.argv[1]
    main(input_filename)

