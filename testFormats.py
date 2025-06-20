# pygame_format_demonstrator.py
#
# Description:
# A Pygame application to visually demonstrate and compare different encoding
# formats for Star Battle puzzles, including a refined, standards-compliant
# version of the "Structured Block" format (Idea 2).
#
# How to Use:
# - Run the script. A Pygame window will appear.
# - Left-click a cell to cycle: Empty -> X -> Star -> Empty.
# - Right-click a cell to place/remove a Star directly.
# - Use the buttons on the right panel to get a new puzzle,
#   clear your marks, or export the current state.
# - The exported formats will be printed to the console.

import pygame
import requests
import re
import math
from collections import defaultdict, deque
import zlib
import base64
import sys

# --- UI & Game Constants ---
GRID_AREA_WIDTH = 600
GRID_AREA_HEIGHT = 600
PANEL_WIDTH = 250
WINDOW_WIDTH = GRID_AREA_WIDTH + PANEL_WIDTH
WINDOW_HEIGHT = GRID_AREA_HEIGHT
GUTTER = 5
BORDER_NORMAL = 1
BORDER_THICK = 4

DEFAULT_PUZZLE_IDX = 3 # 8x8 medium from the website list

# --- Colors ---
COLOR_BLACK = (0, 0, 0)
COLOR_GRID_LINES = (200, 200, 200)
COLOR_STAR = (255, 200, 0)
COLOR_X = (40, 40, 40)
COLOR_PANEL = (50, 50, 60)
COLOR_BUTTON = (80, 80, 90)
COLOR_BUTTON_HOVER = (110, 110, 120)
COLOR_BUTTON_TEXT = (220, 220, 220)
PYGAME_UNIFIED_COLORS = [
    (255,204,204), (204,255,204), (255,255,204), (204,229,255),
    (255,204,255), (204,255,255), (255,229,204), (229,204,255)
]

# --- State Constants ---
STATE_EMPTY = 0
STATE_STAR = 1
STATE_X = 2
ANNOT_CHAR_MAP = {STATE_EMPTY: '.', STATE_STAR: 's', STATE_X: 'x'}

# --- Utility & Drawing Functions ---
def get_puzzle_from_website(size_selection):
    """Fetches puzzle data from puzzle-star-battle.com."""
    url = f"https://www.puzzle-star-battle.com/?size={size_selection}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"Fetching puzzle data from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        task_match = re.search(r"var task = '([^']+)';", response.text)
        if task_match:
            print("Successfully extracted puzzle data.\n")
            return task_match.group(1)
        return None
    except requests.RequestException as e:
        print(f"Error fetching puzzle data: {e}")
        return None

def parse_grid_from_task(task_string, dim):
    """Parses a comma-separated task string into a 2D list."""
    try:
        numbers = [int(n) for n in task_string.split(',')]
        grid = [numbers[i*dim:(i+1)*dim] for i in range(dim)]
        return grid
    except (ValueError, TypeError):
        return None

def calculate_star_points(center_x, center_y, outer_radius, inner_radius):
    points = []
    for i in range(10):
        angle = math.pi / 5 * i - math.pi / 2
        radius = outer_radius if i % 2 == 0 else inner_radius
        points.append((center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
    return points

def draw_background(screen, region_grid, cell_size):
    dim = len(region_grid)
    for r in range(dim):
        for c in range(dim):
            rect = pygame.Rect(c * cell_size, r * cell_size, cell_size, cell_size)
            region_num = region_grid[r][c]
            pygame.draw.rect(screen, PYGAME_UNIFIED_COLORS[(region_num - 1) % len(PYGAME_UNIFIED_COLORS)], rect)

def draw_grid_lines(screen, region_grid, cell_size):
    dim = len(region_grid)
    for i in range(dim + 1):
        pygame.draw.line(screen, COLOR_GRID_LINES, (i * cell_size, 0), (i * cell_size, GRID_AREA_HEIGHT), BORDER_NORMAL)
        pygame.draw.line(screen, COLOR_GRID_LINES, (0, i * cell_size), (GRID_AREA_WIDTH, i * cell_size), BORDER_NORMAL)
    for r in range(dim):
        for c in range(dim):
            if c < dim - 1 and region_grid[r][c] != region_grid[r][c+1]:
                pygame.draw.line(screen, COLOR_BLACK, ((c + 1) * cell_size, r * cell_size), ((c + 1) * cell_size, (r + 1) * cell_size), BORDER_THICK)
            if r < dim - 1 and region_grid[r][c] != region_grid[r+1][c]:
                pygame.draw.line(screen, COLOR_BLACK, (c * cell_size, (r + 1) * cell_size), ((c + 1) * cell_size, (r + 1) * cell_size), BORDER_THICK)
    pygame.draw.rect(screen, COLOR_BLACK, (0, 0, GRID_AREA_WIDTH, GRID_AREA_HEIGHT), BORDER_THICK)

def draw_player_marks(screen, player_grid, cell_size):
    dim = len(player_grid)
    for r in range(dim):
        for c in range(dim):
            center_x, center_y = c * cell_size + cell_size / 2, r * cell_size + cell_size / 2
            if player_grid[r][c] == STATE_STAR:
                outer_rad, inner_rad = cell_size / 2.5, cell_size / 5
                pygame.draw.polygon(screen, COLOR_STAR, calculate_star_points(center_x, center_y, outer_rad, inner_rad))
            elif player_grid[r][c] == STATE_X:
                margin = GUTTER * 2.5
                line_width = max(1, int(cell_size / 15))
                pygame.draw.line(screen, COLOR_X, (c * cell_size + margin, r * cell_size + margin), ((c + 1) * cell_size - margin, (r + 1) * cell_size - margin), line_width)
                pygame.draw.line(screen, COLOR_X, ((c + 1) * cell_size - margin, r * cell_size + margin), (c * cell_size + margin, (r + 1) * cell_size - margin), line_width)

def draw_control_panel(screen, font, buttons):
    pygame.draw.rect(screen, COLOR_PANEL, (GRID_AREA_WIDTH, 0, PANEL_WIDTH, WINDOW_HEIGHT))
    mouse_pos = pygame.mouse.get_pos()
    for name, b in buttons.items():
        color = COLOR_BUTTON_HOVER if b['rect'].collidepoint(mouse_pos) else COLOR_BUTTON
        pygame.draw.rect(screen, color, b['rect'], border_radius=8)
        text_surf = font.render(b['text'], True, COLOR_BUTTON_TEXT)
        screen.blit(text_surf, text_surf.get_rect(center=b['rect'].center))

# --- Bitstream to Bytes Conversion ---
def bitstream_to_bytes(bit_str):
    """Converts a string of '0's and '1's to bytes, with trailing padding."""
    padding = (8 - len(bit_str) % 8) % 8
    padded_str = bit_str + '0' * padding
    return bytes(int(padded_str[i:i+8], 2) for i in range(0, len(padded_str), 8))

def bytes_to_bitstream(byte_data):
    """Converts bytes back into a bitstream string."""
    return "".join(f"{byte:08b}" for byte in byte_data)

# --- IDEA 2 (REFINED): Encoder and Decoder ---

def encode_idea2_refined(dim, stars, region_grid, player_grid):
    """Encodes the puzzle using standard Base64 and trailing padding."""
    header = f"SB2:{dim}x{stars}"

    # Region Data Encoding
    h_borders = ['1' if region_grid[r][c] != region_grid[r+1][c] else '0' for r in range(dim - 1) for c in range(dim)]
    v_borders = ['1' if region_grid[r][c] != region_grid[r][c+1] else '0' for r in range(dim) for c in range(dim - 1)]
    region_bitstream = "".join(h_borders) + "".join(v_borders)
    region_bytes = bitstream_to_bytes(region_bitstream)
    region_b64 = base64.b64encode(region_bytes).decode('utf-8')

    # Annotation Data Encoding (2 bits per cell: 00=empty, 01=star, 10=X)
    annot_map = {STATE_EMPTY: "00", STATE_STAR: "01", STATE_X: "10"}
    annot_bitstream = "".join([annot_map.get(player_grid[r][c], "00") for r in range(dim) for c in range(dim)])
    
    annot_b64 = ""
    if any(s != STATE_EMPTY for row in player_grid for s in row):
        annot_bytes = bitstream_to_bytes(annot_bitstream)
        annot_b64 = base64.b64encode(annot_bytes).decode('utf-8')

    return f"{header}:R{region_b64}:A{annot_b64}"

def reconstruct_grid_from_bitstream(dim, h_bits, v_bits):
    """Reconstructs the region grid from horizontal and vertical border bitstreams."""
    region_grid = [[0] * dim for _ in range(dim)]
    region_id = 1
    for r_start in range(dim):
        for c_start in range(dim):
            if region_grid[r_start][c_start] == 0:
                q = deque([(r_start, c_start)])
                region_grid[r_start][c_start] = region_id
                while q:
                    r,c = q.popleft()
                    # Up
                    if r > 0 and h_bits[(r-1)*dim + c] == '0' and region_grid[r-1][c] == 0:
                        region_grid[r-1][c] = region_id; q.append((r-1,c))
                    # Down
                    if r < dim-1 and h_bits[r*dim+c] == '0' and region_grid[r+1][c] == 0:
                        region_grid[r+1][c] = region_id; q.append((r+1,c))
                    # Left
                    if c > 0 and v_bits[r*(dim-1)+(c-1)] == '0' and region_grid[r][c-1] == 0:
                        region_grid[r][c-1] = region_id; q.append((r,c-1))
                    # Right
                    if c < dim-1 and v_bits[r*(dim-1)+c] == '0' and region_grid[r][c+1] == 0:
                        region_grid[r][c+1] = region_id; q.append((r,c+1))
                region_id += 1
    return region_grid

def decode_idea2_refined(data_string):
    """Decodes the refined format back into puzzle data."""
    try:
        parts = data_string.split(':')
        if len(parts) != 4 or parts[0] != "SB2": return None
        
        meta, region_data, annot_data = parts[1], parts[2][1:], parts[3][1:]
        dim, stars = map(int, meta.split('x'))

        # Decode Region Data
        region_bytes = base64.b64decode(region_data)
        full_bitstream = bytes_to_bitstream(region_bytes)
        
        num_h_bits = (dim - 1) * dim
        num_v_bits = dim * (dim - 1)
        h_bits = full_bitstream[:num_h_bits]
        v_bits = full_bitstream[num_h_bits : num_h_bits + num_v_bits]
        region_grid = reconstruct_grid_from_bitstream(dim, h_bits, v_bits)

        # Decode Annotation Data
        player_grid = [[STATE_EMPTY] * dim for _ in range(dim)]
        if annot_data:
            annot_bytes = base64.b64decode(annot_data)
            annot_bitstream = bytes_to_bitstream(annot_bytes)
            state_map = {"00": STATE_EMPTY, "01": STATE_STAR, "10": STATE_X}
            for i in range(dim * dim):
                r, c = divmod(i, dim)
                bits = annot_bitstream[i*2 : i*2 + 2]
                player_grid[r][c] = state_map.get(bits, STATE_EMPTY)

        return region_grid, player_grid, stars
    except Exception as e:
        print(f"Failed to decode Idea 2 Refined: {e}")
        return None, None, None

# --- Other Format Encoders (for comparison) ---

# FORMAT 1
def run_length_encode(data):
    if not data: return ""
    encoded_pairs = []
    count = 1
    current_item = data[0]
    for i in range(1, len(data)):
        if data[i] == current_item:
            count += 1
        else:
            encoded_pairs.append(f"{current_item}*{count}")
            current_item, count = data[i], 1
    encoded_pairs.append(f"{current_item}*{count}")
    return ",".join(encoded_pairs)

def encode_idea1(dim, stars, region_grid, player_grid):
    flat_regions = [item for row in region_grid for item in row]
    flat_player = [ANNOT_CHAR_MAP[item] for row in player_grid for item in row]
    regions_rle, annot_rle = run_length_encode(flat_regions), run_length_encode(flat_player)
    return f"dim={dim}&stars={stars}&regions={regions_rle}&annot={annot_rle}"

# FORMAT 3
def to_alg_notation(r, c): return f"{chr(ord('A')+c)}{r+1}"
def encode_idea3(dim, stars, region_grid, player_grid):
    header = f"{dim}x{stars}"
    region_coords = defaultdict(list)
    for r in range(dim):
        for c in range(dim):
            region_coords[region_grid[r][c]].append(to_alg_notation(r,c))
    region_strings = [f"{rid}:{','.join(coords)}" for rid, coords in sorted(region_coords.items())]
    star_coords = [to_alg_notation(r,c) for r in range(dim) for c in range(dim) if player_grid[r][c] == STATE_STAR]
    x_coords = [to_alg_notation(r,c) for r in range(dim) for c in range(dim) if player_grid[r][c] == STATE_X]
    full_string = header + ";" + ";".join(region_strings)
    if star_coords: full_string += f";s:{','.join(star_coords)}"
    if x_coords: full_string += f";x:{','.join(x_coords)}"
    return full_string

# FORMAT 4
def encode_idea4(dim, stars, region_grid, player_grid):
    verbose_string = encode_idea1(dim, stars, region_grid, player_grid)
    compressed_binary = zlib.compress(verbose_string.encode('utf-8'))
    return base64.b64encode(compressed_binary).decode('utf-8')

# --- Main Program ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Pygame Format Demonstrator")
    font = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()

    dim, stars = 8, 1 # Default values for 8x8 puzzle
    task_string = get_puzzle_from_website(DEFAULT_PUZZLE_IDX)
    if not task_string:
        print("Could not start. Exiting.")
        return
    region_grid = parse_grid_from_task(task_string, dim)
    player_grid = [[STATE_EMPTY for _ in range(dim)] for _ in range(dim)]
    cell_size = GRID_AREA_WIDTH / dim

    buttons = {}
    b_width, b_height, b_margin = 220, 45, 15
    button_defs = [('export', 'Export All Formats'), ('new', 'New Puzzle'), ('clear', 'Clear Board')]
    current_y = b_margin
    for name, text in button_defs:
        rect = pygame.Rect(GRID_AREA_WIDTH + (PANEL_WIDTH - b_width) // 2, current_y, b_width, b_height)
        buttons[name] = {'rect': rect, 'text': text}
        current_y += b_height + b_margin

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                clicked_button = False
                for name, b_data in buttons.items():
                    if b_data['rect'].collidepoint(pos):
                        clicked_button = True
                        if name == 'export':
                            print("\n" + "="*50)
                            print("--- EXPORTING IN ALL FORMATS ---")
                            print("\n[Idea 1: Verbose Key Format]")
                            print(encode_idea1(dim, stars, region_grid, player_grid))
                            print("\n[Idea 2: Refined Structured Block Format]")
                            refined_str = encode_idea2_refined(dim, stars, region_grid, player_grid)
                            print(refined_str)
                            # Also test the decoder for this format
                            print("---> Decoding the above string to test integrity...")
                            r_grid, p_grid, s = decode_idea2_refined(refined_str)
                            if r_grid and p_grid:
                                print("---> Decode Successful!")
                            else:
                                print("---> DECODE FAILED!")

                            print("\n[Idea 3: Coordinate List Format]")
                            print(encode_idea3(dim, stars, region_grid, player_grid))
                            print("\n[Idea 4: Compressed Human-Readable Format]")
                            print(encode_idea4(dim, stars, region_grid, player_grid))
                            print("="*50 + "\n")
                        elif name == 'new':
                            task_string = get_puzzle_from_website(DEFAULT_PUZZLE_IDX)
                            if task_string:
                                region_grid = parse_grid_from_task(task_string, dim)
                                player_grid = [[STATE_EMPTY for _ in range(dim)] for _ in range(dim)]
                        elif name == 'clear':
                            player_grid = [[STATE_EMPTY for _ in range(dim)] for _ in range(dim)]
                        break
                if not clicked_button and pos[0] < GRID_AREA_WIDTH:
                    c, r = int(pos[0] // cell_size), int(pos[1] // cell_size)
                    if 0 <= r < dim and 0 <= c < dim:
                        if event.button == 1:
                            player_grid[r][c] = (player_grid[r][c] + 1) % 3
                        elif event.button == 3:
                            player_grid[r][c] = STATE_EMPTY if player_grid[r][c] == STATE_STAR else STATE_STAR

        screen.fill(COLOR_PANEL)
        if region_grid:
            draw_background(screen, region_grid, cell_size)
            draw_grid_lines(screen, region_grid, cell_size)
            draw_player_marks(screen, player_grid, cell_size)
        draw_control_panel(screen, font, buttons)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

