
# --- File: backend/z3_solver.py ---
import hashlib
import time
from collections import defaultdict
try:
    from z3 import Solver, Bool, PbEq, Implies, And, Not, Or, sat
    Z3_AVAILABLE = True
except ImportError:
    print("Warning: 'z3-solver' library not found.")
    Z3_AVAILABLE = False
    class Solver: pass
    def Bool(s): return None
    def PbEq(s, i): return None
    def Implies(a,b): return None
    def And(s): return None
    def Not(s): return None
    def Or(s): return None
    sat = "sat"
def format_duration(seconds):
    if seconds >= 60: return f"{int(seconds//60)} min {seconds%60:.2f} s"
    if seconds >= 1: return f"{seconds:.3f} s"
    return f"{seconds*1000:.2f} ms"
def validate_solver_solution_with_hash(solution_grid, puzzle_data):
    expected_hash = puzzle_data.get('solution_hash')
    if not expected_hash: return
    yn_string = "".join(['y' if cell else 'n' for row in solution_grid for cell in row])
    string_to_hash = puzzle_data['task'] + yn_string
    calculated_hash = hashlib.md5(string_to_hash.encode()).hexdigest()
    print("--- Hash Validation ---")
    print(f"\033[92m✅ MATCHES\033[0m" if calculated_hash == expected_hash else "\033[91m❌ DOES NOT MATCH\033[0m")
class Z3StarBattleSolver:
    def __init__(self, region_grid, stars_per_region):
        self.region_grid, self.dim, self.stars_per_region = region_grid, len(region_grid), stars_per_region

    def solve(self):
        if not Z3_AVAILABLE: return [], {}
        s = Solver()
        grid_vars = [[Bool(f"c_{r}_{c}") for c in range(self.dim)] for r in range(self.dim)]
        # Rule: N stars per row and column
        for i in range(self.dim):
            s.add(PbEq([(grid_vars[i][c], 1) for c in range(self.dim)], self.stars_per_region))
            s.add(PbEq([(grid_vars[r][i], 1) for r in range(self.dim)], self.stars_per_region))
        # Rule: N stars per region
        regions = defaultdict(list)
        for r in range(self.dim):
            for c in range(self.dim): regions[self.region_grid[r][c]].append(grid_vars[r][c])
        for r_vars in regions.values():
            s.add(PbEq([(var, 1) for var in r_vars], self.stars_per_region))
        # Rule: Stars cannot be adjacent
        for r in range(self.dim):
            for c in range(self.dim):
                neighbors = []
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0: continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.dim and 0 <= nc < self.dim:
                            neighbors.append(Not(grid_vars[nr][nc]))
                if neighbors:
                    s.add(Implies(grid_vars[r][c], And(neighbors)))

        solutions, start_time = [], time.monotonic()
        if s.check() == sat:
            model = s.model()
            solution = [[(1 if model.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)]
            solutions.append(solution)
            # Block this solution and check for another
            s.add(Or([Not(v) if solution[r][c] else v for r, row in enumerate(grid_vars) for c, v in enumerate(row)]))
            if s.check() == sat:
                model2 = s.model()
                solutions.append([[(1 if model2.evaluate(grid_vars[r][c]) else 0) for c in range(self.dim)] for r in range(self.dim)])
        print(f"Z3 solve time: {format_duration(time.monotonic() - start_time)}")
        return solutions, {}


