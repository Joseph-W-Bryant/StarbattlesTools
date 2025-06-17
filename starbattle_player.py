# --- Silence Pygame messages and warnings ---
import os
import warnings

# Hide the "Hello from the pygame community" message.
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

# Filter out the specific warnings.
# Using a wildcard '*' at the end makes the filter more robust to slight changes.
warnings.filterwarnings("ignore", category=RuntimeWarning, message="Your system is avx2 capable but pygame was not built with support for it.*")
warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources is deprecated as an API.*")
# --- End of silencing code ---


import pygame
import requests
import re
import sys

# --- Configuration ---
GRID_DIMENSION = 10 
STARS_PER_REGION = 2 

# --- UI Constants ---
CELL_SIZE = 60
WINDOW_SIZE = GRID_DIMENSION * CELL_SIZE
GUTTER = 5
BORDER_NORMAL = 1
BORDER_THICK = 4

# --- Colors ---
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRID_LINES = (200, 200, 200)
COLOR_STAR = (255, 200, 0)
COLOR_DOT = (150, 150, 150)

# --- Game State Constants ---
STATE_EMPTY = 0
STATE_STAR = 1
STATE_DOT = 2

def get_puzzle_from_website(grid_dimension):
    """
    Fetches the puzzle data string ('task') from the puzzle-star-battle website.
    """
    if grid_dimension == 10:
        website_url_size = 5
    else:
        print(f"Warning: The URL parameter for a {grid_dimension}x{grid_dimension} grid is unknown. Assuming it's {grid_dimension}.")
        website_url_size = grid_dimension
        
    url = f"https://www.puzzle-star-battle.com/?size={website_url_size}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"Fetching puzzle data from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: Could not fetch puzzle data from the website. {e}")
        return None

    match = re.search(r"var task = '([^']+)';", response.text)
    
    if match:
        print("Successfully extracted puzzle data.")
        return match.group(1)
    else:
        print("Error: Could not find the puzzle data ('task' variable) in the page source.")
        return None

def parse_task_to_grid(task_string, dimension):
    """
    Converts the 1D comma-separated string of region numbers into a 2D grid.
    """
    if not task_string:
        return None
        
    try:
        numbers = [int(n) for n in task_string.split(',')]
        if len(numbers) != dimension * dimension:
            print(f"Error: Data length ({len(numbers)}) doesn't match grid size ({dimension}x{dimension}).")
            return None
            
        grid = []
        for i in range(dimension):
            row = numbers[i * dimension : (i + 1) * dimension]
            grid.append(row)
        return grid
    except (ValueError, TypeError):
        print("Error: Could not parse the task string into numbers.")
        return None

def draw_board(screen, region_grid, player_grid):
    """
    Master drawing function that renders the entire game board.
    """
    screen.fill(COLOR_WHITE)
    draw_player_marks(screen, player_grid)
    draw_grid_lines(screen, region_grid)

def draw_grid_lines(screen, region_grid):
    """
    Draws all grid lines, making region borders thicker.
    """
    dim = len(region_grid)
    for i in range(dim + 1):
        pygame.draw.line(screen, COLOR_GRID_LINES, (i * CELL_SIZE, 0), (i * CELL_SIZE, WINDOW_SIZE), BORDER_NORMAL)
        pygame.draw.line(screen, COLOR_GRID_LINES, (0, i * CELL_SIZE), (WINDOW_SIZE, i * CELL_SIZE), BORDER_NORMAL)

    for r in range(dim):
        for c in range(dim):
            if c < dim - 1 and region_grid[r][c] != region_grid[r][c+1]:
                start_pos = ((c + 1) * CELL_SIZE, r * CELL_SIZE)
                end_pos = ((c + 1) * CELL_SIZE, (r + 1) * CELL_SIZE)
                pygame.draw.line(screen, COLOR_BLACK, start_pos, end_pos, BORDER_THICK)

            if r < dim - 1 and region_grid[r][c] != region_grid[r+1][c]:
                start_pos = (c * CELL_SIZE, (r + 1) * CELL_SIZE)
                end_pos = ((c + 1) * CELL_SIZE, (r + 1) * CELL_SIZE)
                pygame.draw.line(screen, COLOR_BLACK, start_pos, end_pos, BORDER_THICK)

def draw_player_marks(screen, player_grid):
    """
    Draws the stars and dots placed by the player.
    """
    dim = len(player_grid)
    for r in range(dim):
        for c in range(dim):
            cell_state = player_grid[r][c]
            center_x = c * CELL_SIZE + CELL_SIZE // 2
            center_y = r * CELL_SIZE + CELL_SIZE // 2
            
            if cell_state == STATE_STAR:
                radius = CELL_SIZE // 2 - GUTTER * 2
                pygame.draw.circle(screen, COLOR_STAR, (center_x, center_y), radius)
            elif cell_state == STATE_DOT:
                radius = CELL_SIZE // 6
                pygame.draw.circle(screen, COLOR_DOT, (center_x, center_y), radius)

def main():
    """
    The main game loop.
    """
    task_string = get_puzzle_from_website(GRID_DIMENSION)
    
    region_grid = parse_task_to_grid(task_string, GRID_DIMENSION)
    if not region_grid:
        print("Failed to set up the board. Exiting.")
        sys.exit(1)

    player_grid = [[STATE_EMPTY for _ in range(GRID_DIMENSION)] for _ in range(GRID_DIMENSION)]

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption(f"Star Battle Player ({STARS_PER_REGION} Stars)")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                grid_col = mouse_x // CELL_SIZE
                grid_row = mouse_y // CELL_SIZE

                if 0 <= grid_row < GRID_DIMENSION and 0 <= grid_col < GRID_DIMENSION:
                    current_state = player_grid[grid_row][grid_col]
                    
                    if event.button == 1: # Left Click
                        if current_state == STATE_STAR:
                            player_grid[grid_row][grid_col] = STATE_EMPTY
                        else:
                            player_grid[grid_row][grid_col] = STATE_STAR
                    
                    elif event.button == 3: # Right Click
                        if current_state == STATE_DOT:
                            player_grid[grid_row][grid_col] = STATE_EMPTY
                        else:
                            player_grid[grid_row][grid_col] = STATE_DOT

        draw_board(screen, region_grid, player_grid)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
