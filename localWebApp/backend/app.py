
# --- File: backend/app.py ---
from flask import Flask, jsonify, request
from flask_cors import CORS

# Use absolute imports from the 'backend' package.
from backend import puzzle_handler as pz
from backend.z3_solver import Z3StarBattleSolver, Z3_AVAILABLE, validate_solver_solution_with_hash
from backend import constants as const

app = Flask(__name__)
CORS(app)

@app.route('/api/new_puzzle', methods=['GET'])
def get_new_puzzle():
    try:
        size_id = int(request.args.get('size_id', 5))
        if not 0 <= size_id < len(const.PUZZLE_DEFINITIONS):
            return jsonify({'error': 'Invalid size_id'}), 400
        
        # MODIFIED: Call the new function to get a puzzle from local files
        puzzle_data = pz.get_puzzle_from_local_file(size_id)
        
        if puzzle_data:
            region_grid, _ = pz.get_grid_from_puzzle_task(puzzle_data)
            if region_grid:
                return jsonify({
                    'regionGrid': region_grid,
                    'starsPerRegion': puzzle_data['stars'],
                    'sourcePuzzleData': puzzle_data
                })
        return jsonify({'error': 'Failed to fetch puzzle from local files'}), 500
    except Exception as e:
        print(f"Error in /api/new_puzzle: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/api/solve', methods=['POST'])
def find_solution():
    if not Z3_AVAILABLE:
        return jsonify({'error': 'Z3 Solver not available on the server'}), 503
    try:
        data = request.json
        region_grid, stars_per_region, source_puzzle_data = data.get('regionGrid'), data.get('starsPerRegion'), data.get('sourcePuzzleData')
        if not all([region_grid, stars_per_region]):
             return jsonify({'error': 'Missing regionGrid or starsPerRegion in request'}), 400
        solver = Z3StarBattleSolver(region_grid, stars_per_region)
        solutions, _ = solver.solve()
        if solutions:
            if source_puzzle_data:
                 validate_solver_solution_with_hash(solutions[0], source_puzzle_data)
            return jsonify({'solution': solutions[0]})
        return jsonify({'solution': None})
    except Exception as e:
        print(f"Error in /api/solve: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/api/check', methods=['POST'])
def check_solution():
    if not Z3_AVAILABLE:
        return jsonify({'error': 'Z3 Solver not available on the server'}), 503
    try:
        data = request.json
        region_grid = data.get('regionGrid')
        player_grid = data.get('playerGrid')
        stars_per_region = data.get('starsPerRegion')
        source_puzzle_data = data.get('sourcePuzzleData') # Now receiving this from frontend

        if not all([region_grid, player_grid, stars_per_region is not None]):
             return jsonify({'error': 'Missing data in request'}), 400

        solver = Z3StarBattleSolver(region_grid, stars_per_region)
        solutions, _ = solver.solve()
        
        is_correct = False
        if solutions:
            player_solution = [[1 if cell == const.STATE_STAR else 0 for cell in row] for row in player_grid]
            if player_solution in solutions:
                is_correct = True

        # Perform secondary hash validation if the solution is correct and hash is available
        hash_validated = False
        if is_correct and source_puzzle_data and source_puzzle_data.get('solution_hash'):
            print("--- Performing secondary hash validation ---")
            # We need a function to do this check, let's assume it's in pz
            hash_validated = pz.check_solution_hash(player_grid, source_puzzle_data)
            print(f"Hash validation result: {hash_validated}")

        return jsonify({'isCorrect': is_correct, 'hashValidated': hash_validated})
    except Exception as e:
        print(f"Error in /api/check: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/api/export', methods=['POST'])
def export_puzzle():
    try:
        data = request.json
        region_grid, player_grid, stars_per_region, history = data.get('regionGrid'), data.get('playerGrid'), data.get('starsPerRegion'), data.get('history')
        if not all([region_grid, player_grid, stars_per_region is not None]):
            return jsonify({'error': 'Missing data in request'}), 400
        sbn_string = pz.encode_to_sbn(region_grid, stars_per_region, player_grid)
        if history and history.get('changes'):
            h_changes, h_pointer = history['changes'], history.get('pointer', 0)
            # Correctly access dictionary values by key
            change_strings = [
                f"{pz.SBN_INT_TO_CHAR[change['r']]}"
                f"{pz.SBN_INT_TO_CHAR[change['c']]}"
                f"{pz.SBN_INT_TO_CHAR[change['from']]}"
                f"{pz.SBN_INT_TO_CHAR[change['to']]}"
                for change in h_changes
            ]
            pointer_char = pz.SBN_INT_TO_CHAR.get(h_pointer, '0')
            history_str = f"h:{''.join(change_strings)}:{pointer_char}"
            sbn_string += f"~{history_str}"
        return jsonify({'exportString': sbn_string})
    except Exception as e:
        print(f"Error in /api/export: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/api/import', methods=['POST'])
def import_puzzle():
    try:
        data = request.json
        import_string = data.get('importString')
        if not import_string:
            return jsonify({'error': 'No import string provided'}), 400
        puzzle_data = pz.universal_import(import_string)
        if not puzzle_data:
            return jsonify({'error': 'Could not recognize puzzle format'}), 400
        region_grid, _ = pz.parse_and_validate_grid(puzzle_data['task'])
        return jsonify({
            'regionGrid': region_grid,
            'playerGrid': puzzle_data.get('player_grid'),
            'starsPerRegion': puzzle_data.get('stars'),
            'history': puzzle_data.get('history')
        })
    except Exception as e:
        print(f"Error in /api/import: {e}")
        return jsonify({'error': 'An internal error occurred'}), 500
