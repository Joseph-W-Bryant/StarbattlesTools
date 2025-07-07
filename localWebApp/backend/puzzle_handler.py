# puzzle_handler.py
import re
import math
import hashlib
from collections import deque
import os
import random

# Use absolute imports from the 'backend' package
from backend.history_manager import HistoryManager
from backend.constants import (
    WEBSITE_SIZE_IDS, PUZZLE_DEFINITIONS, STATE_EMPTY, STATE_STAR, STATE_SECONDARY_MARK,
    SBN_B64_ALPHABET, SBN_CHAR_TO_INT, SBN_INT_TO_CHAR, SBN_CODE_TO_DIM_MAP,
    DIM_TO_SBN_CODE_MAP, UNIFIED_COLORS_BG, BASE64_DISPLAY_ALPHABET
)

def get_puzzle_from_local_file(size_id):
    """
    Fetches a random puzzle SBN string from a local text file based on size_id.
    """
    try:
        # --- MODIFIED LINE ---
        # The filename is now the size_id directly (e.g., '0.txt', '1.txt').
        file_path = os.path.join(os.path.dirname(__file__), 'puzzles', f'{size_id}.txt')

        print(f"\nFetching puzzle from local file: {file_path}...")

        if not os.path.exists(file_path):
            print(f"Error: Puzzle file not found at {file_path}")
            return None

        with open(file_path, 'r') as f:
            puzzles = [line.strip() for line in f if line.strip()]
        
        if not puzzles:
            print(f"Error: No puzzles found in {file_path}")
            return None
            
        random_sbn_string = random.choice(puzzles)
        print(f"Selected SBN: {random_sbn_string}")

        puzzle_data = decode_sbn(random_sbn_string)
        
        if puzzle_data:
            print("Successfully decoded SBN puzzle from local file.")
            return puzzle_data

        print("Error: Failed to decode the SBN string.")
        return None

    except Exception as e:
        print(f"Error fetching puzzle from local file: {e}")
        return None


# --- (Code from universal_import down to decode_player_annotations is unchanged) ---

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
    dim = len(region_grid)
    sbn_code = DIM_TO_SBN_CODE_MAP.get(dim)
    if not sbn_code: return None

    # Vertical borders are stored row-by-row, which is correct.
    vertical_bits = ['1' if c < dim - 1 and region_grid[r][c] != region_grid[r][c+1] else '0' for r in range(dim) for c in range(dim - 1)]
    
    # **FIXED**: Horizontal borders must be stored column-by-column to match the decoder.
    # The original loop order `for r... for c...` was incorrect. It has been changed to `for c... for r...`.
    horizontal_bits = ['1' if r < dim - 1 and region_grid[r][c] != region_grid[r+1][c] else '0' for c in range(dim) for r in range(dim - 1)]
    
    clean_bitfield = "".join(vertical_bits) + "".join(horizontal_bits)
    
    padding_needed = (6 - len(clean_bitfield) % 6) % 6
    padded_bitfield = ('0' * padding_needed) + clean_bitfield
    
    region_data_chars = [SBN_INT_TO_CHAR[int(padded_bitfield[i:i+6], 2)] for i in range(0, len(padded_bitfield), 6)]
    region_data = "".join(region_data_chars)

    raw_annotation_data = encode_player_annotations(player_grid) if player_grid else ""
    flag = 'e' if raw_annotation_data else 'W'
    
    return f"{sbn_code}{stars}{flag}{region_data}{raw_annotation_data}"

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
                    # Reads vertical borders in row-major order
                    if c < dim-1 and grid[r][c+1]==0 and v_bits[r*(dim-1)+c]=='0': grid[r][c+1]=region_id; q.append((r,c+1))
                    if c > 0 and grid[r][c-1]==0 and v_bits[r*(dim-1)+c-1]=='0': grid[r][c-1]=region_id; q.append((r,c-1))
                    # Reads horizontal borders in column-major order
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

def display_terminal_grid(grid, title, content_grid=None):
    """Prints a simple version of the grid to the terminal for server-side debugging."""
    if not grid: return
    dim = len(grid)
    print(f"\n--- {title} ---")
    for r in range(dim):
        row_str = []
        for c in range(dim):
            # Using modulo to keep alignment for double-digit region numbers
            symbol = '★' if content_grid and content_grid[r][c] == 1 else str(grid[r][c] % 10)
            row_str.append(f"{symbol:^3}") 
        print(" ".join(row_str))
    print("-----------------\n")

def get_grid_from_puzzle_task(puzzle_data):
    if not puzzle_data or 'task' not in puzzle_data: return None, None
    region_grid, dimension = parse_and_validate_grid(puzzle_data['task'])
    if region_grid:
        display_terminal_grid(region_grid, "Terminal Symbol Display (Server)")
        return region_grid, dimension
    return None, None

def check_solution_hash(player_grid, puzzle_data):
    """Validates a player's solution against the website's MD5 hash."""
    if not puzzle_data or 'solution_hash' not in puzzle_data or not puzzle_data['solution_hash']:
        return False
        
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
