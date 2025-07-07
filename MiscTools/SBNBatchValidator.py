# ==================================================================================================
#
#   SBN Batch Validator for Star Battle Puzzles
#
#   Author: Isaiah Tadrous
#   Date: July 7, 2025
#   Version: 1.0.0
#
# --------------------------------------------------------------------------------------------------
#
#   Overview:
#   This script is a high-performance, parallel-processing tool designed to validate Star
#   Battle puzzles. It takes a file or directory of puzzles encoded in Star Battle
#   Notation (SBN) and efficiently determines whether each puzzle has one and only one
#   unique solution.
#
#   The core of the validation logic is handled by the Z3 SMT (Satisfiability Modulo
#   Theories) solver, a powerful theorem prover from Microsoft Research. The script sets
#   up the rules of a Star Battle puzzle as a series of logical constraints and asks Z3
#   to find solutions.
#
# --------------------------------------------------------------------------------------------------
#
#   Key Features & Technical Highlights:
#
#   - Massively Parallel Processing: Utilizes the `multiprocessing` library to
#     distribute the computational load across all available CPU cores. This allows for
#     the rapid validation of tens of thousands of puzzles.
#
#   - Efficient SBN Decoding: Implements a robust decoder for the custom SBN format,
#     capable of reconstructing a puzzle's region layout from a compact, base64-like
#     string representation.
#
#   - Z3-Solver Integration: Demonstrates expertise in using an advanced external
#     library (Z3) to solve complex logical problems. The script models the puzzle's
#     rules—such as star placement in rows, columns, and regions, and the adjacency
#     constraint—as a formal satisfiability problem.
#
#   - Uniqueness Validation: The script doesn't just find *a* solution; it proves
#     uniqueness by finding a solution, adding a constraint to block that specific
#     solution, and then asking the solver to find another. If no other solution exists,
#     the puzzle is unique.
#
#   - State Management: To prevent redundant work, the script maintains a list of
#     previously validated puzzles (`found_puzzles.txt`) and skips any puzzles that have
#     already been checked.
#
#   - Destructive Cleanup Mode: Includes a powerful `--delete-from-source` feature that,
#     when enabled, will remove all *checked* puzzles from the source files. This is
#     useful for iteratively cleaning large candidate lists.
#
#   - Robust & User-Friendly CLI: Built with `argparse` to provide a clear and flexible
#     command-line interface, including options for controlling worker processes and
#     search behavior.
#
# ==================================================================================================

import time
import multiprocessing
import os
import argparse
import math
import platform
from collections import defaultdict, deque

# External dependencies (required):
#   - Z3-Solver: The core engine for solving the puzzle constraints.
#     (pip install z3-solver)
#   - TQDM: A library for creating smart, extensible progress bars.
#     (pip install tqdm)
try:
    from z3 import Solver, Bool, PbEq, Implies, And, Not, Or, sat
    from tqdm import tqdm
    Z3_AVAILABLE = True
except ImportError:
    # If Z3 or TQDM is not installed, the script cannot function.
    # I created dummy classes and a flag to handle this gracefully.
    print("FATAL ERROR: Required libraries 'z3-solver' or 'tqdm' are not installed.")
    print("Please run: pip install z3-solver tqdm")
    Z3_AVAILABLE = False
    class Solver: pass
    def Bool(s): return None
    def PbEq(s, i): return None
    def Implies(a,b): return None
    def And(s): return None
    def Not(s): return None
    def Or(s): return None
    sat = "sat"
    def tqdm(iterable, **kwargs):
        return iterable


# --- Z3 Solver Integration (from z3_solver.py) ---

class Z3StarBattleSolver:
    """
    A class to solve Star Battle puzzles using the Z3 SMT solver.

    This class encapsulates the entire logic for translating a puzzle's grid and rules
    into a formal set of constraints that the Z3 solver can understand and process.
    """
    def __init__(self, region_grid, stars_per_region):
        """
        Initializes the solver with the puzzle's structure.

        Args:
            region_grid (list[list[int]]): A 2D list representing the puzzle, where each
                                           cell contains an integer ID for its region.
            stars_per_region (int): The number of stars required per region, row, and column.
        """
        self.region_grid = region_grid
        self.dim = len(region_grid)
        self.stars_per_region = stars_per_region
        self.solver = Solver()

        # Create a 2D grid of Z3 Boolean variables. Each variable `X[r][c]`
        # represents the statement "there is a star at row r, column c".
        self.X = [[Bool(f"star_{r}_{c}") for c in range(self.dim)] for r in range(self.dim)]

    def _add_constraints(self):
        """Encodes the rules of Star Battle into Z3 constraints."""

        # Rule 1: Each row must contain exactly `stars_per_region` stars.
        for r in range(self.dim):
            # PbEq (Pseudo-Boolean Equals) is a powerful constraint that states
            # the sum of the variables (where True=1, False=0) must equal a value.
            self.solver.add(PbEq([(self.X[r][c], 1) for c in range(self.dim)], self.stars_per_region))

        # Rule 2: Each column must contain exactly `stars_per_region` stars.
        for c in range(self.dim):
            self.solver.add(PbEq([(self.X[r][c], 1) for r in range(self.dim)], self.stars_per_region))

        # Rule 3: Each region must contain exactly `stars_per_region` stars.
        regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim):
                regions[self.region_grid[r][c]].append(self.X[r][c])

        for region_vars in regions.values():
            self.solver.add(PbEq([(var, 1) for var in region_vars], self.stars_per_region))

        # Rule 4: Stars cannot be adjacent, including diagonally.
        for r in range(self.dim):
            for c in range(self.dim):
                neighbors = []
                # Iterate through all 8 neighboring cells.
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue  # Skip the cell itself.
                        nr, nc = r + dr, c + dc
                        # Check if the neighbor is within the grid boundaries.
                        if 0 <= nr < self.dim and 0 <= nc < self.dim:
                            neighbors.append(self.X[nr][nc])
                
                # Implies(A, B) means "if A is true, then B must be true".
                # Here, if a star is at (r,c), then all its neighbors must NOT be stars.
                if neighbors:
                    self.solver.add(Implies(self.X[r][c], And([Not(n) for n in neighbors])))

    def solve(self):
        """
        Runs the Z3 solver to find up to two unique solutions for the puzzle.

        Returns:
            A tuple containing:
            - list: A list of solutions found. Each solution is a 2D grid.
            - dict: A dictionary for metadata (currently unused).
        """
        if not Z3_AVAILABLE:
            return [], {}
        
        # Add all the defined rules to the solver instance.
        self._add_constraints()

        solutions = []
        # It is only necessary to find a maximum of two solutions to determine uniqueness.
        while len(solutions) < 2 and self.solver.check() == sat:
            model = self.solver.model()
            # Reconstruct the solution board from the Z3 model.
            solution_board = [[(1 if model.evaluate(self.X[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
            solutions.append(solution_board)

            # To find a *different* solution, I added a new constraint that blocks the
            # current solution. This forces the solver to find an alternative model.
            blocking_clause = Or([
                cell if value == 0 else Not(cell)
                for r, row in enumerate(self.X)
                for c, cell in enumerate(row)
                if (value := solution_board[r][c]) is not None
            ])
            self.solver.add(blocking_clause)

        return solutions, {}


# --- Constants & SBN Puzzle Functions ---

OUTPUT_FILE = "found_puzzles.txt"
SBN_B64_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_' #
SBN_CHAR_TO_INT = {c: i for i, c in enumerate(SBN_B64_ALPHABET)} #
SBN_CODE_TO_DIM_MAP = {
    '55': 5,  '66': 6,  '77': 7,  '88': 8,  '99': 9, 'AA': 10, 'BB': 11, 'CC': 12, 'DD': 13,
    'EE': 14, 'FF': 15, 'GG': 16, 'HH': 17, 'II': 18, 'JJ': 19, 'KK': 20, 'LL': 21, 'MM': 22,
    'NN': 23, 'OO': 24, 'PP': 25
} #

def decode_sbn(sbn_string):
    """
    Decodes an SBN string into its constituent puzzle data.

    The SBN format encodes the puzzle grid's borders into a compact string. This
    function parses that string, reconstructs the borders, and then uses a flood-fill
    algorithm to regenerate the region layout.

    Args:
        sbn_string (str): The SBN puzzle string.

    Returns:
        dict: A dictionary containing the puzzle task and star count, or None if parsing fails.
    """
    try:
        # The SBN header contains the size code (e.g., 'B0' for 10x10).
        size_code = sbn_string[0:2]
        dim = SBN_CODE_TO_DIM_MAP.get(size_code)
        if not dim: return None

        stars = int(sbn_string[2])
        
        # Calculate the number of characters needed to represent the grid borders.
        border_bits_needed = 2 * dim * (dim - 1)
        border_chars_needed = math.ceil(border_bits_needed / 6)
        
        region_data_str = sbn_string[4 : 4 + border_chars_needed]

        # Convert the base64-like characters back into a bitfield.
        full_bitfield = "".join(bin(SBN_CHAR_TO_INT.get(char, 0))[2:].zfill(6) for char in region_data_str)
        
        # Extract the actual border data, ignoring any padding bits.
        padding_bits = len(full_bitfield) - border_bits_needed
        border_data = full_bitfield[padding_bits:]
        
        num_single_direction_borders = dim * (dim - 1)
        vertical_bits = border_data[:num_single_direction_borders]
        horizontal_bits = border_data[num_single_direction_borders:]

        # Reconstruct the grid regions from the border information.
        region_grid = reconstruct_grid_from_borders(dim, vertical_bits, horizontal_bits)
        task_string = ",".join(str(cell) for row in region_grid for cell in row)
        
        return {'task': task_string, 'stars': stars}
    except (KeyError, IndexError, ValueError):
        return None

def reconstruct_grid_from_borders(dim, vertical_bits, horizontal_bits):
    """
    Rebuilds the region grid using a flood-fill algorithm based on border data.
    This is a classic graph traversal problem.
    """
    region_grid = [[0] * dim for _ in range(dim)]
    region_id = 1
    for r_start in range(dim):
        for c_start in range(dim):
            if region_grid[r_start][c_start] == 0: # If the cell hasn't been visited
                q = deque([(r_start, c_start)])
                region_grid[r_start][c_start] = region_id
                while q:
                    r, c = q.popleft()
                    # Explore neighbors if there is no border between them.
                    if c < dim - 1 and region_grid[r][c+1] == 0 and vertical_bits[r*(dim-1) + c] == '0':
                        region_grid[r][c+1] = region_id; q.append((r, c+1))
                    if c > 0 and region_grid[r][c-1] == 0 and vertical_bits[r*(dim-1) + (c-1)] == '0':
                        region_grid[r][c-1] = region_id; q.append((r, c-1))
                    if r < dim - 1 and region_grid[r+1][c] == 0 and horizontal_bits[c*(dim-1) + r] == '0':
                        region_grid[r+1][c] = region_id; q.append((r+1, c))
                    if r > 0 and region_grid[r-1][c] == 0 and horizontal_bits[c*(dim-1) + (r-1)] == '0':
                        region_grid[r-1][c] = region_id; q.append((r-1, c))
                region_id += 1
    return region_grid

def parse_and_validate_grid(task_string):
    """Parses a comma-separated task string into a 2D grid."""
    try:
        numbers = [int(n) for n in task_string.split(',')]
        total_cells = len(numbers)
        if total_cells == 0: return None, None
        dimension = math.isqrt(total_cells)
        if dimension * dimension != total_cells: return None, None # Must be a square grid.
        return [numbers[i*dimension:(i+1)*dimension] for i in range(dimension)], dimension
    except (ValueError, TypeError):
        return None, None


# --- File I/O ---

def read_sbn_by_file(path):
    """
    Reads SBN lines from a given file or directory and maps them to their source file.
    """
    sbn_map = defaultdict(list)
    if os.path.isdir(path):
        for filename in sorted(os.listdir(path)):
            filepath = os.path.join(path, filename)
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'r') as f:
                        for line in f:
                            stripped_line = line.strip()
                            if stripped_line:
                                sbn_map[filepath].append(stripped_line)
                except Exception as e:
                    print(f"Warning: Could not read file {filepath}: {e}")
    elif os.path.isfile(path):
        with open(path, 'r') as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line:
                    sbn_map[path].append(stripped_line)
    else:
        raise FileNotFoundError(f"Path '{path}' is not a valid file or directory")
    return sbn_map

def load_found_puzzles(filepath):
    """Loads existing puzzles from the output file to avoid re-processing."""
    if not os.path.exists(filepath):
        return set()
    with open(filepath, 'r') as f:
        return {line.strip() for line in f if line.strip()}


# --- Worker Process ---

def solve_sbn_worker(sbn_tuple):
    """
    This is the core function executed by each worker process in the pool.
    It takes a single puzzle, decodes it, solves it, and returns the result.
    """
    sbn, filepath = sbn_tuple
    try:
        puzzle_data = decode_sbn(sbn)
        if not puzzle_data: return None

        region_grid, _ = parse_and_validate_grid(puzzle_data['task'])
        stars = puzzle_data.get('stars', 1)
        if not region_grid: return None

        # Instantiate and run the solver. This is the most computationally
        # intensive part of the process.
        solver = Z3StarBattleSolver(region_grid, stars)
        solutions, _ = solver.solve()

        # A puzzle is unique if and only if exactly one solution was found.
        is_unique = len(solutions) == 1
        return sbn, filepath, is_unique

    except Exception:
        # Catch any catastrophic failures during processing to prevent a worker from crashing.
        return None


# --- Main Execution ---

def main(input_path, workers, stop_after_first, delete_from_source):
    """Main function to set up and run the puzzle processing pipeline."""
    start_time = time.time()
    
    # Enable color support for Windows terminals, if applicable.
    if platform.system() == "Windows":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, mode)

    existing_puzzles = load_found_puzzles(OUTPUT_FILE)
    print(f"Loaded {len(existing_puzzles)} previously found puzzles from '{OUTPUT_FILE}'.")

    sbn_map = read_sbn_by_file(input_path)

    # Filter out puzzles that have already been checked in previous runs.
    puzzles_to_process = []
    for filepath, sbn_list in sbn_map.items():
        for sbn in list(dict.fromkeys(sbn_list)): # Unique SBNs per file
            if sbn not in existing_puzzles:
                puzzles_to_process.append((sbn, filepath))

    if not puzzles_to_process:
        print("\033[92m[OK]\033[0m No new puzzles to process. All SBNs have been checked.")
        return

    print(f"Found {len(puzzles_to_process)} new puzzles to check across all files.")

    if stop_after_first:
        print("\033[94m[INFO]\033[0m 'Find-first' mode enabled. Reversing list to check newest puzzles first.")
        puzzles_to_process.reverse()

    newly_found_tuples = []
    all_checked_puzzles = []
    
    # This is the core of the parallel processing. A pool of worker processes is
    # created, and the list of puzzles is distributed among them.
    with multiprocessing.Pool(processes=workers) as pool:
        # `imap_unordered` is used for efficiency. It returns results as soon as they
        # are completed, rather than waiting for the entire batch.
        results_iterator = pool.imap_unordered(solve_sbn_worker, puzzles_to_process)

        try:
            # Wrap the iterator with tqdm to display a live progress bar.
            for result_tuple in tqdm(results_iterator, total=len(puzzles_to_process), desc="Processing Puzzles"):
                if result_tuple:
                    sbn, filepath, is_unique = result_tuple
                    all_checked_puzzles.append((sbn, filepath))
                    if is_unique:
                        newly_found_tuples.append((sbn, filepath))
                        if stop_after_first:
                            print("\n\033[92m[FOUND]\033[0m First unique puzzle found. Terminating workers...")
                            pool.terminate()
                            break
        except KeyboardInterrupt:
            print("\n\033[94m[INFO]\033[0m User interrupt received. Terminating workers...")
            pool.terminate()

    # --- Step 4: Report, save, and optionally delete ---
    total_elapsed = time.time() - start_time
    print("\n" + "="*50)
    print("\033[95m*** COMPLETED ***\033[0m")

    if newly_found_tuples:
        unique_newly_found = {sbn: path for sbn, path in reversed(newly_found_tuples)}
        print(f"Found {len(unique_newly_found)} new unique puzzles.")
        with open(OUTPUT_FILE, "a") as f:
            for sbn in sorted(unique_newly_found.keys()):
                f.write(sbn + "\n")
        print(f"\033[96m[SAVED]\033[0m Saved {len(unique_newly_found)} puzzles to '{OUTPUT_FILE}'.")
    else:
        print("\033[91m[FAIL]\033[0m No new unique puzzles were found in this run.")

    if delete_from_source:
        print(f"\n--delete-from-source enabled. Removing {len(all_checked_puzzles)} checked puzzles from input files.")
        if all_checked_puzzles:
            to_delete_map = defaultdict(set)
            for sbn, filepath in all_checked_puzzles:
                to_delete_map[filepath].add(sbn)
            for filepath, sbns_to_delete in to_delete_map.items():
                try:
                    with open(filepath, 'r') as f:
                        original_lines = f.readlines()
                    updated_lines = [line for line in original_lines if line.strip() not in sbns_to_delete]
                    with open(filepath, 'w') as f:
                        f.writelines(updated_lines)
                    print(f"✅ Removed {len(sbns_to_delete)} puzzles from: {os.path.basename(filepath)}")
                except Exception as e:
                    print(f"\033[93m[WARN]\033[0m Error updating file {filepath}: {e}")
    elif newly_found_tuples:
        print("\n(Skipping deletion from source files. Use --delete-from-source to enable.)")

    print(f"\033[90m[TIME]\033[0m Total elapsed time: {total_elapsed:.2f} seconds")
    print("="*50)

# The `if __name__ == "__main__"` block is crucial for multiprocessing. It ensures
# that the main script logic is not executed again inside the worker processes.
if __name__ == "__main__":
    # `freeze_support` is necessary for creating frozen executables (e.g., with PyInstaller).
    multiprocessing.freeze_support()

    if not Z3_AVAILABLE:
        # Exit gracefully if the core dependencies are missing.
        exit(1)

    parser = argparse.ArgumentParser(
        description="Validate SBN puzzles from a file or folder using multiple workers.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_path", help="Path to the input file or folder containing SBN strings.")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help=f"Number of parallel worker processes (default: all available cores).")
    parser.add_argument("--find-all", action='store_true', help="Continue searching even after the first puzzle is found.")
    parser.add_argument(
        "--delete-from-source",
        action='store_true',
        help="DANGER: Permanently delete ALL CHECKED puzzles (good or bad)\nfrom their original input files. Use with caution."
    )

    args = parser.parse_args()

    main(
        args.input_path,
        workers=args.workers,
        stop_after_first=not args.find_all,
        delete_from_source=args.delete_from_source
    )