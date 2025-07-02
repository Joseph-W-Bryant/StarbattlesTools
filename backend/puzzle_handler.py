# puzzle_handler.py
import requests
import re
import math
import hashlib
from collections import deque

# Use absolute imports from the 'backend' package
from backend.history_manager import HistoryManager
from backend.constants import (
    WEBSITE_SIZE_IDS, PUZZLE_DEFINITIONS, STATE_EMPTY, STATE_STAR, STATE_SECONDARY_MARK,
    SBN_B64_ALPHABET, SBN_CHAR_TO_INT, SBN_INT_TO_CHAR, SBN_CODE_TO_DIM_MAP,
    DIM_TO_SBN_CODE_MAP, UNIFIED_COLORS_BG, BASE64_DISPLAY_ALPHABET
)

# --- (The rest of the file remains the same until display_terminal_grid) ---

def _parse_as_webtask(main_part):
    try:
        best_split_index = -1
        for i in range(len(main_part), 0, -1):
            potential_task = main_part[:i]
            if not potential_task or not potential_task[-1].isdigit(): continue
            if not re.fullmatch(r'[\d,]+', potential_task): continue
            try:
                numbers = [int(n) for n in potential_task.split(',')]
                if len(numbers) > 0 and math.isqrt(len(numbers))**2 == len(numbers):
                    best_split_index = i
                    break
            except (ValueError, TypeError): continue
        if best_split_index != -1:
            task_part, ann_part = main_part[:best_split_index], main_part[best_split_index:]
            puzzle_data = decode_web_task_string(task_part)
            if puzzle_data: return puzzle_data, ann_part
        return None, None
    except Exception as e:
        print(f"Error during webtask parsing: {e}")
        return None, None

def universal_import(input_string):
    print("\nAttempting to import puzzle string...")
    parts = input_string.strip().split('~')
    main_part, history_part = parts[0], parts[1] if len(parts) > 1 else ""
    puzzle_data, raw_annotation_data = None, ""
    if len(main_part) >= 4 and main_part[0:2] in SBN_CODE_TO_DIM_MAP:
        try:
            puzzle_data = decode_sbn(main_part)
            if not puzzle_data: raise ValueError("SBN decoding failed.")
            print("Successfully decoded as SBN format.")
            _, dim = parse_and_validate_grid(puzzle_data['task'])
            if dim and main_part[3] == 'e':
                border_chars_needed = math.ceil((2 * dim * (dim - 1)) / 6)
                base_sbn_len = 4 + border_chars_needed
                raw_annotation_data = main_part[base_sbn_len:]
        except Exception as e:
            print(f"SBN parsing failed: {e}")
            return None
    else:
        print("Input not SBN, trying Web Task format...")
        result = _parse_as_webtask(main_part)
        if result and result[0]:
            puzzle_data, raw_annotation_data = result
            print("Successfully decoded as Web Task format.")
    if puzzle_data:
        _, dim = parse_and_validate_grid(puzzle_data['task'])
        if dim:
            puzzle_data['player_grid'] = decode_player_annotations(raw_annotation_data, dim)
            if history_part:
                mgr = HistoryManager.deserialize([[]] * dim, history_part)
                puzzle_data['history'] = {"changes": mgr.changes, "pointer": mgr.pointer}
        print("Puzzle import successful.")
        return puzzle_data
    print("Error: Could not recognize puzzle format.")
    return None

def get_puzzle_from_website(size_selection):
    url = "https://www.puzzle-star-battle.com/"
    if WEBSITE_SIZE_IDS[size_selection] != 0: url += f"?size={WEBSITE_SIZE_IDS[size_selection]}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"\nFetching puzzle from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        task_match = re.search(r"var task = '([^']+)';", response.text)
        hash_match = re.search(r"hashedSolution: '([^']+)'", response.text)
        if task_match:
            print("Successfully extracted puzzle data.")
            return {'task': task_match.group(1), 'solution_hash': hash_match.group(1) if hash_match else None}
        print("Error: Puzzle data not found in response.")
        return None
    except requests.RequestException as e:
        print(f"Error fetching puzzle: {e}")
        return None

def encode_player_annotations(player_grid):
    if not player_grid: return ""
    dim, game_to_sbn = len(player_grid), {STATE_EMPTY: 0, STATE_SECONDARY_MARK: 1, STATE_STAR: 2}
    flat = [game_to_sbn.get(player_grid[r][c], 0) for r in range(dim) for c in range(dim)]
    if not any(flat): return ""
    sbn_states = [str(flat.pop(0))] if dim in [10, 11] and flat else []
    for i in range(0, len(flat), 3):
        chunk = flat[i:i+3]; chunk.extend([0] * (3 - len(chunk)))
        value = chunk[0] * 16 + chunk[1] * 4 + chunk[2]
        sbn_states.append(SBN_INT_TO_CHAR[value])
    return "".join(sbn_states)

def decode_player_annotations(annotation_data_str, dim):
    grid = [[STATE_EMPTY] * dim for _ in range(dim)]
    if not annotation_data_str: return grid
    try:
        flat_indices, sbn_to_game = [(r, c) for r in range(dim) for c in range(dim)], {0: STATE_EMPTY, 1: STATE_SECONDARY_MARK, 2: STATE_STAR}
        char_cursor, cell_cursor = 0, 0
        if dim in [10, 11] and annotation_data_str and annotation_data_str[0].isdigit():
            grid[0][0] = sbn_to_game.get(int(annotation_data_str[0]), STATE_EMPTY)
            char_cursor, cell_cursor = 1, 1
        while cell_cursor < dim**2 and char_cursor < len(annotation_data_str):
            value = SBN_CHAR_TO_INT.get(annotation_data_str[char_cursor], 0)
            states = [(value // 16), (value % 16) // 4, value % 4]
            for i in range(3):
                if cell_cursor + i < dim**2:
                    r, c = flat_indices[cell_cursor + i]
                    grid[r][c] = sbn_to_game.get(states[i], STATE_EMPTY)
            cell_cursor, char_cursor = cell_cursor + 3, char_cursor + 1
        return grid
    except (KeyError, IndexError, ValueError): return [[STATE_EMPTY] * dim for _ in range(dim)]

def encode_to_sbn(region_grid, stars, player_grid=None):
    dim, sbn_code = len(region_grid), DIM_TO_SBN_CODE_MAP.get(len(region_grid))
    if not sbn_code: return None
    v_bits = ['1' if c<dim-1 and r_g[c]!=r_g[c+1] else '0' for r_g in region_grid for c in range(dim-1)]
    h_bits = ['1' if r<dim-1 and region_grid[r][c]!=region_grid[r+1][c] else '0' for r in range(dim-1) for c in range(dim)]
    bitfield = "".join(v_bits) + "".join(h_bits)
    padded = ('0' * ((6 - len(bitfield) % 6) % 6)) + bitfield
    region_data = "".join([SBN_INT_TO_CHAR[int(padded[i:i+6], 2)] for i in range(0, len(padded), 6)])
    ann_data = encode_player_annotations(player_grid) if player_grid else ""
    return f"{sbn_code}{stars}{'e' if ann_data else 'W'}{region_data}{ann_data}"

def decode_sbn(sbn_string):
    try:
        dim = SBN_CODE_TO_DIM_MAP.get(sbn_string[0:2])
        stars, border_bits_needed = int(sbn_string[2]), 2 * dim * (dim - 1)
        border_chars = math.ceil(border_bits_needed / 6)
        region_data = sbn_string[4:4+border_chars].ljust(border_chars, SBN_B64_ALPHABET[0])
        full_bitfield = "".join(bin(SBN_CHAR_TO_INT.get(c,0))[2:].zfill(6) for c in region_data)[-border_bits_needed:]
        v_bits, h_bits = full_bitfield[:dim*(dim-1)], full_bitfield[dim*(dim-1):]
        region_grid = reconstruct_grid_from_borders(dim, v_bits, h_bits)
        task_str = ",".join(str(cell) for row in region_grid for cell in row)
        return {'task': task_str, 'solution_hash': None, 'stars': stars}
    except (KeyError, IndexError, ValueError) as e: raise e

def decode_web_task_string(task_string):
    try:
        region_grid, dim = parse_and_validate_grid(task_string)
        if not region_grid: return None
        stars = next((p['stars'] for p in PUZZLE_DEFINITIONS if p['dim'] == dim), 1)
        return {'task': task_string, 'solution_hash': None, 'stars': stars}
    except Exception: return None

def reconstruct_grid_from_borders(dim, v_bits, h_bits):
    grid, region_id = [[0]*dim for _ in range(dim)], 1
    for r_start in range(dim):
        for c_start in range(dim):
            if grid[r_start][c_start] == 0:
                q = deque([(r_start, c_start)])
                grid[r_start][c_start] = region_id
                while q:
                    r, c = q.popleft()
                    if c < dim-1 and grid[r][c+1]==0 and v_bits[r*(dim-1)+c]=='0': grid[r][c+1]=region_id; q.append((r,c+1))
                    if c > 0 and grid[r][c-1]==0 and v_bits[r*(dim-1)+c-1]=='0': grid[r][c-1]=region_id; q.append((r,c-1))
                    if r < dim-1 and grid[r+1][c]==0 and h_bits[c*(dim-1)+r]=='0': grid[r+1][c]=region_id; q.append((r+1,c))
                    if r > 0 and grid[r-1][c]==0 and h_bits[c*(dim-1)+r-1]=='0': grid[r-1][c]=region_id; q.append((r-1,c))
                region_id += 1
    return grid

def parse_and_validate_grid(task_string):
    if not task_string: return None, None
    try:
        nums = [int(n) for n in task_string.split(',')]
        if not nums: return None, None
        dim = math.isqrt(len(nums))
        if dim**2 != len(nums): return None, None
        return [nums[i*dim:(i+1)*dim] for i in range(dim)], dim
    except (ValueError, TypeError): return None, None

# --- THIS FUNCTION IS FIXED ---
def display_terminal_grid(grid, title, content_grid=None):
    """Prints a simple version of the grid to the terminal for server-side debugging."""
    if not grid: return
    dim = len(grid)
    print(f"\n--- {title} ---")
    for r in range(dim):
        row_str = []
        for c in range(dim):
            # The symbol is either a star (if content is provided) or the region number
            symbol = '★' if content_grid and content_grid[r][c] == 1 else str(grid[r][c])
            # We just append the symbol, no more complex color codes
            row_str.append(f"{symbol:^3}") # Pad to 3 spaces for alignment
        print(" ".join(row_str))
    print("-----------------\n")

def get_grid_from_puzzle_task(puzzle_data):
    if not puzzle_data or 'task' not in puzzle_data: return None, None
    region_grid, dimension = parse_and_validate_grid(puzzle_data['task'])
    if region_grid:
        # This call is now safe
        display_terminal_grid(region_grid, "Terminal Symbol Display (Server)")
        return region_grid, dimension
    return None, None

def check_solution_hash(player_grid, puzzle_data):
    """Validates a player's solution against the website's MD5 hash."""
    if not puzzle_data or 'solution_hash' not in puzzle_data or not puzzle_data['solution_hash']:
        return False
        
    # Convert player grid (with states 0, 1, 2) to the 'y'/'n' string format
    yn_string = "".join(['y' if cell == STATE_STAR else 'n' for row in player_grid for cell in row])
    string_to_hash = puzzle_data['task'] + yn_string
    calculated_hash = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()
    
    is_correct = calculated_hash == puzzle_data['solution_hash']
    
    print(f"Calculated Hash: {calculated_hash}")
    print(f"Expected Hash:   {puzzle_data['solution_hash']}")
    if is_correct:
        print("\033[92m--> Hash matches!\033[0m")
    else:
        print("\033[91m--> Hash does NOT match.\033[0m")
        
    return is_correct

