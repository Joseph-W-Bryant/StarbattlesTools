# puzzle_handler.py
# Description: Manages puzzle data, including web fetching, SBN/task conversion, and saving with a unified history format.

import requests
import re
import math
import hashlib
from collections import deque
from datetime import datetime
from history_manager import HistoryManager

from constants import (
    WEBSITE_SIZE_IDS, PUZZLE_DEFINITIONS, STATE_EMPTY, STATE_STAR, STATE_SECONDARY_MARK,
    SBN_B64_ALPHABET, SBN_CHAR_TO_INT, SBN_INT_TO_CHAR, SBN_CODE_TO_DIM_MAP,
    DIM_TO_SBN_CODE_MAP, UNIFIED_COLORS_BG, BASE64_DISPLAY_ALPHABET, GRID_AREA_WIDTH
)

def encode_player_annotations(player_grid):
    """Encodes a player's grid state into a compact raw annotation string."""
    if not player_grid: return ""
    dim = len(player_grid)
    game_to_sbn_state = {STATE_EMPTY: 0, STATE_SECONDARY_MARK: 1, STATE_STAR: 2}
    flat_states = [game_to_sbn_state.get(player_grid[r][c], 0) for r in range(dim) for c in range(dim)]
    
    if not any(flat_states): return ""

    sbn_states = []
    # Special handling for 10x10 and 11x11 grids
    if dim in [10, 11] and flat_states:
        sbn_states.append(str(flat_states[0]))
        flat_states = flat_states[1:]
        
    for i in range(0, len(flat_states), 3):
        chunk = flat_states[i:i+3]
        while len(chunk) < 3: chunk.append(0)
        s1, s2, s3 = chunk
        value = s1 * 16 + s2 * 4 + s3
        sbn_states.append(SBN_INT_TO_CHAR[value])
        
    return "".join(sbn_states)

def decode_player_annotations(annotation_data_str, dim):
    """Decodes a raw annotation string into a 2D player grid."""
    if not annotation_data_str:
        return None
    try:
        player_grid = [[STATE_EMPTY] * dim for _ in range(dim)]
        flat_indices = [(r, c) for r in range(dim) for c in range(dim)]
        sbn_to_game_state = {0: STATE_EMPTY, 1: STATE_SECONDARY_MARK, 2: STATE_STAR}
        
        char_cursor, cell_cursor = 0, 0
        
        if dim in [10, 11] and annotation_data_str:
            value = int(annotation_data_str[0])
            player_grid[0][0] = sbn_to_game_state.get(value, STATE_EMPTY)
            char_cursor, cell_cursor = 1, 1
            
        while cell_cursor < dim * dim and char_cursor < len(annotation_data_str):
            char = annotation_data_str[char_cursor]
            value = SBN_CHAR_TO_INT.get(char, 0)
            states = [(value // 16), (value % 16) // 4, value % 4]
            for i in range(3):
                if cell_cursor + i < dim * dim:
                    r, c = flat_indices[cell_cursor + i]
                    player_grid[r][c] = sbn_to_game_state.get(states[i], STATE_EMPTY)
            cell_cursor += 3
            char_cursor += 1
            
        return player_grid
    except (KeyError, IndexError, ValueError):
        return None

def save_puzzle_entry(puzzle_data, player_grid, history_manager, comment):
    """Formats and appends a puzzle entry with annotations and history."""
    try:
        region_grid, dim = parse_and_validate_grid(puzzle_data['task'])
        if not region_grid:
            raise ValueError("Invalid puzzle data for saving.")

        stars = puzzle_data.get('stars', 1)
        
        sbn_export = encode_to_sbn(region_grid, stars, player_grid)
        
        raw_annotation_data = encode_player_annotations(player_grid)
        web_task_export = f"{puzzle_data.get('task', '')}{raw_annotation_data}"

        history_str = history_manager.serialize()
        if history_str:
            sbn_export += f"~{history_str}"
            web_task_export += f"~{history_str}"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"#-{'-'*75}\n"
            f"# Puzzle saved on: {timestamp}\n"
            f"# Comment: {comment}\n"
            f"#-{'-'*75}\n"
            f"SBN Format:      {sbn_export}\n"
            f"Web Task Format: {web_task_export}\n"
            f"\n\n"
        )
        with open("saved_puzzles.txt", "a") as f:
            f.write(entry)
        print(f"\n✅ Puzzle successfully saved to 'saved_puzzles.txt' with comment: '{comment}'")
    except Exception as e:
        print(f"\n❌ Error saving puzzle: {e}")

def universal_import(input_string):
    """
    Intelligently decodes a puzzle string with optional annotations and history.
    """
    print("\nAttempting to import puzzle string...")
    parts = input_string.strip().split('~')
    main_part = parts[0]
    history_part = parts[1] if len(parts) > 1 else ""
    
    puzzle_data = None
    raw_annotation_data = ""
    
    # --- Try SBN format first ---
    if re.match(r'^[0-9A-Z]{3}', main_part):
        try:
            temp_puzzle_data = decode_sbn(main_part)
            if temp_puzzle_data:
                puzzle_data = temp_puzzle_data
                print("Successfully decoded as SBN format.")
                dim, _ = parse_and_validate_grid(puzzle_data['task'])
                flag = main_part[3]
                if flag == 'e':
                    border_bits_needed = 2 * len(dim) * (len(dim) - 1)
                    border_chars_needed = math.ceil(border_bits_needed / 6)
                    base_sbn_len = 4 + border_chars_needed
                    raw_annotation_data = main_part[base_sbn_len:]
        except Exception:
            puzzle_data = None
            
    # --- If not SBN, try Web Task format by finding the perfect square boundary ---
    if not puzzle_data:
        print("Could not parse as SBN, attempting Web Task format...")
        best_split_index = -1
        for i in range(len(main_part), 0, -1):
            potential_task = main_part[:i]
            if not potential_task or not potential_task[-1].isdigit():
                continue
            if not re.fullmatch(r'[\d,]+', potential_task):
                continue
            numbers = potential_task.split(',')
            if any(not n for n in numbers): continue
            num_count = len(numbers)
            if num_count > 0:
                sqrt_val = math.isqrt(num_count)
                if sqrt_val * sqrt_val == num_count:
                    best_split_index = i
                    break
        
        if best_split_index != -1:
            task_part = main_part[:best_split_index]
            ann_part = main_part[best_split_index:]
            puzzle_data = decode_web_task_string(task_part)
            if puzzle_data:
                print("Successfully decoded as Web Task format.")
                raw_annotation_data = ann_part

    # --- Final processing if any format was successful ---
    if puzzle_data:
        _, dim = parse_and_validate_grid(puzzle_data['task'])
        player_grid = decode_player_annotations(raw_annotation_data, dim)
        puzzle_data['player_grid'] = player_grid or [[STATE_EMPTY] * dim for _ in range(dim)]
        
        initial_grid_for_history = [[STATE_EMPTY] * dim for _ in range(dim)]
        restored_manager = HistoryManager.deserialize(initial_grid_for_history, history_part)
        
        if restored_manager and restored_manager.pointer > 0:
            puzzle_data['player_grid'] = restored_manager.get_current_grid()

        print("Puzzle import successful.")
        return puzzle_data, restored_manager

    print("Error: Could not recognize the puzzle format.")
    return None, None

def get_puzzle_from_website(size_selection):
    url = "https://www.puzzle-star-battle.com/"; website_size_id = WEBSITE_SIZE_IDS[size_selection]
    if website_size_id != 0: url += f"?size={website_size_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    print(f"\nFetching puzzle data from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10); response.raise_for_status()
        task_match = re.search(r"var task = '([^']+)';", response.text)
        hash_match = re.search(r"hashedSolution: '([^']+)'", response.text)
        if task_match and hash_match:
            print("Successfully extracted puzzle data.")
            return {'task': task_match.group(1), 'solution_hash': hash_match.group(1)}
        print("Error: Could not find required puzzle data."); return None
    except requests.RequestException as e:
        print(f"Error: Could not fetch puzzle data. {e}"); return None

def decode_sbn(sbn_string):
    """Decodes an SBN string into a puzzle_data dictionary."""
    try:
        size_code = sbn_string[0:2]; dim = SBN_CODE_TO_DIM_MAP.get(size_code)
        if not dim: return None
        stars = int(sbn_string[2])
        border_bits_needed = 2 * dim * (dim - 1)
        border_chars_needed = math.ceil(border_bits_needed / 6)
        region_data_str = sbn_string[4 : 4 + border_chars_needed]
        full_bitfield = "".join(bin(SBN_CHAR_TO_INT[char])[2:].zfill(6) for char in region_data_str)
        padding_bits = len(full_bitfield) - border_bits_needed
        border_data = full_bitfield[padding_bits:]
        num_single_direction_borders = dim * (dim - 1)
        vertical_bits = border_data[0 : num_single_direction_borders]
        horizontal_bits = border_data[num_single_direction_borders : border_bits_needed]
        region_grid = reconstruct_grid_from_borders(dim, vertical_bits, horizontal_bits)
        task_string = ",".join(str(cell) for row in region_grid for cell in row)
        return {'task': task_string, 'solution_hash': None, 'stars': stars}
    except (KeyError, IndexError, ValueError):
        return None

def decode_web_task_string(task_string):
    """Decodes a Web Task string into a puzzle_data dictionary."""
    try:
        region_grid, dim = parse_and_validate_grid(task_string)
        if not region_grid: return None
        stars = 1
        for pdef in PUZZLE_DEFINITIONS:
            if pdef['dim'] == dim: stars = pdef['stars']; break
        return {'task': task_string, 'solution_hash': None, 'stars': stars}
    except Exception:
        return None

def encode_to_sbn(region_grid, stars, player_grid=None):
    """Encodes a region grid into an SBN string, including annotations."""
    dim = len(region_grid)
    sbn_code = DIM_TO_SBN_CODE_MAP.get(dim)
    if not sbn_code: return None

    vertical_bits = ['1' if c < dim - 1 and region_grid[r][c] != region_grid[r][c+1] else '0' for r in range(dim) for c in range(dim - 1)]
    horizontal_bits = ['1' if r < dim - 1 and region_grid[r][c] != region_grid[r+1][c] else '0' for c in range(dim) for r in range(dim - 1)]
    clean_bitfield = "".join(vertical_bits) + "".join(horizontal_bits)
    
    padding_bits = (math.ceil(len(clean_bitfield) / 6) * 6) - len(clean_bitfield)
    padded_bitfield = ('0' * padding_bits) + clean_bitfield
    
    region_data_chars = [SBN_INT_TO_CHAR[int(padded_bitfield[i:i+6], 2)] for i in range(0, len(padded_bitfield), 6)]
    region_data = "".join(region_data_chars)

    raw_annotation_data = encode_player_annotations(player_grid) if player_grid else ""
    flag = 'e' if raw_annotation_data else 'W'
    
    return f"{sbn_code}{stars}{flag}{region_data}{raw_annotation_data}"

def reconstruct_grid_from_borders(dim, vertical_bits, horizontal_bits):
    region_grid = [[0] * dim for _ in range(dim)]; region_id = 1
    for r_start in range(dim):
        for c_start in range(dim):
            if region_grid[r_start][c_start] == 0:
                q = deque([(r_start, c_start)]); region_grid[r_start][c_start] = region_id
                while q:
                    r, c = q.popleft()
                    if c < dim - 1 and region_grid[r][c+1] == 0 and vertical_bits[r*(dim-1) + c] == '0': region_grid[r][c+1] = region_id; q.append((r, c+1))
                    if c > 0 and region_grid[r][c-1] == 0 and vertical_bits[r*(dim-1) + (c-1)] == '0': region_grid[r][c-1] = region_id; q.append((r, c-1))
                    if r < dim - 1 and region_grid[r+1][c] == 0 and horizontal_bits[c*(dim-1) + r] == '0': region_grid[r+1][c] = region_id; q.append((r+1, c))
                    if r > 0 and region_grid[r-1][c] == 0 and horizontal_bits[c*(dim-1) + (r-1)] == '0': region_grid[r-1][c] = region_id; q.append((r-1, c))
                region_id += 1
    return region_grid

def parse_and_validate_grid(task_string):
    """Parses a task string and returns the grid and its dimension if it's a valid square grid."""
    if not task_string: return None, None
    try:
        numbers = [int(n) for n in task_string.split(',')]; total_cells = len(numbers)
        if total_cells == 0: return None, None
        dimension = math.isqrt(total_cells)
        if dimension * dimension != total_cells: return None, None
        grid = [numbers[i*dimension:(i+1)*dimension] for i in range(dimension)]
        return grid, dimension
    except (ValueError, TypeError): return None, None

def display_terminal_grid(grid, title, content_grid=None):
    if not grid: return
    RESET = "\033[0m"; print(f"\n--- {title} ---")
    dim = len(grid)
    for r in range(dim):
        colored_chars = []
        for c in range(dim):
            region_num = grid[r][c]; color_ansi = UNIFIED_COLORS_BG[(region_num - 1) % len(UNIFIED_COLORS_BG)][2]
            if content_grid: symbol = '★' if content_grid[r][c] == 1 else '·'
            else: symbol = BASE64_DISPLAY_ALPHABET[(region_num - 1) % len(BASE64_DISPLAY_ALPHABET)]
            colored_chars.append(f"{color_ansi} {symbol} {RESET}")
        print("".join(colored_chars))
    print("-----------------\n")

def reset_game_state(puzzle_data):
    if not puzzle_data or 'task' not in puzzle_data: return (None,) * 6
    region_grid, dimension = parse_and_validate_grid(puzzle_data['task'])
    if region_grid:
        display_terminal_grid(region_grid, "Terminal Symbol Display")
        stars = puzzle_data.get('stars', 1)
        player_grid = puzzle_data.get('player_grid') or [[STATE_EMPTY] * dimension for _ in range(dimension)]
        cell_size = GRID_AREA_WIDTH / dimension
        return region_grid, puzzle_data, player_grid, dimension, cell_size, stars
    return (None,) * 6

def check_solution(player_grid, puzzle_data):
    if not puzzle_data or 'solution_hash' not in puzzle_data or not puzzle_data['solution_hash']: return False
    yn_string = "".join(['y' if cell == STATE_STAR else 'n' for row in player_grid for cell in row])
    string_to_hash = puzzle_data['task'] + yn_string
    calculated_hash = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()
    is_correct = calculated_hash == puzzle_data['solution_hash']
    print(f"Calculated Hash: {calculated_hash}\nExpected Hash:   {puzzle_data['solution_hash']}")
    if is_correct: print("\033[92m--> Hash matches!\033[0m")
    else: print("\033[91m--> Hash does NOT match.\033[0m")
    return is_correct

