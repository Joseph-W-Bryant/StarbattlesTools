# z3_solver.py
# Description: Contains the Z3StarBattleSolver class and related functions.

import hashlib
import time
from collections import defaultdict

# For simplicity, we check availability and import here.
try:
    from z3 import Solver, Bool, PbEq, Implies, And, Not, Or, sat, unsat
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    # Define dummy classes if Z3 is not available to avoid crashing on class definition
    class Solver: pass
    def Bool(s): return None
    def PbEq(s, i): return None
    def Implies(a,b): return None
    def And(s): return None
    def Not(s): return None
    def Or(s): return None
    sat = "sat"
    unsat = "unsat"

def format_duration(seconds):
    """Formats a duration in seconds into a human-readable string."""
    if seconds >= 60:
        minutes = int(seconds // 60); remaining_seconds = seconds % 60
        if remaining_seconds < 0.01: return f"{minutes} min"
        return f"{minutes} min {remaining_seconds:.2f} s"
    if seconds >= 1: return f"{seconds:.3f} s"
    if seconds >= 0.001: return f"{seconds * 1000:.2f} ms"
    return f"{seconds * 1_000_000:.2f} µs"

def validate_solver_solution_with_hash(solution_grid, puzzle_data):
    """Checks if a solver-found solution matches the website's hash."""
    expected_hash = puzzle_data.get('solution_hash')
    if not expected_hash: return
    yn_string = "".join(['y' if cell == 1 else 'n' for row in solution_grid for cell in row])
    string_to_hash = puzzle_data['task'] + yn_string
    calculated_hash = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()
    print("--- Hash Validation ---")
    if calculated_hash == expected_hash: print("\033[92m✅ Found solution MATCHES the website's expected solution.\033[0m")
    else: print("\033[91m❌ Found solution DOES NOT MATCH the website's expected solution.\033[0m")

class Z3StarBattleSolver:
    """A class to solve Star Battle puzzles using the Z3 SMT solver."""
    def __init__(self, region_grid, stars_per_region):
        self.region_grid = region_grid
        self.dim = len(region_grid)
        self.stars_per_region = stars_per_region

    def solve(self):
        """
        Sets up and runs the Z3 solver to find up to two solutions.
        """
        if not Z3_AVAILABLE: return [], {}
        
        s = Solver()
        grid_vars = [[Bool(f"cell_{r}_{c}") for c in range(self.dim)] for r in range(self.dim)]
        
        # Rule: N stars per row and N stars per column
        for i in range(self.dim):
            s.add(PbEq([(var, 1) for var in grid_vars[i]], self.stars_per_region))
            s.add(PbEq([(grid_vars[r][i], 1) for r in range(self.dim)], self.stars_per_region))
            
        # Rule: N stars per region
        regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim): regions[self.region_grid[r][c]].append(grid_vars[r][c])
        for region_vars in regions.values():
            s.add(PbEq([(var, 1) for var in region_vars], self.stars_per_region))
            
        # Rule: Stars cannot be adjacent
        for r in range(self.dim):
            for c in range(self.dim):
                # *** BUG FIX: Changed 'dim' to 'self.dim' ***
                neighbors = [Not(grid_vars[nr][nc]) for dr in [-1, 0, 1] for dc in [-1, 0, 1] if not (dr == 0 and dc == 0) and 0 <= (nr := r + dr) < self.dim and 0 <= (nc := c + dc) < self.dim]
                s.add(Implies(grid_vars[r][c], And(neighbors)))
        
        solutions = []
        if s.check() == sat:
            model = s.model()
            solution_board = [[(1 if model.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
            solutions.append(solution_board)
            
            # Block the first solution to check for a second one
            blocking_clause = Or([grid_vars[r][c] if solution_board[r][c] == 0 else Not(grid_vars[r][c]) for r in range(self.dim) for c in range(self.dim)])
            s.add(blocking_clause)
            if s.check() == sat:
                model = s.model()
                solution_board_2 = [[(1 if model.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
                solutions.append(solution_board_2)
                
        return solutions, {}


