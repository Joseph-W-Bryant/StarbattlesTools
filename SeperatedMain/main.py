# main.py
# Description: The main entry point for the Star Battle application.
# This file initializes the game and runs the main loop.

import os
import warnings
import pygame
import sys

# Suppress Pygame welcome message and warnings
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import constants as const
import puzzle_handler as pz
import ui_manager as ui
import action_handlers as actions
from game_state import GameState
from ui_elements import Button
from z3_solver import Z3_AVAILABLE

def main():
    """The main function to initialize and run the game application."""
    pygame.init()
    pygame.display.set_caption("Star Battle Playground")
    clock = pygame.time.Clock()
    
    fonts = {
        'default': pygame.font.Font(None, 32),
        'small': pygame.font.Font(None, 24),
        'tiny': pygame.font.Font(None, 18)
    }
    
    # --- Data-driven layout for BOTH control panels ---
    left_panel_layout = [
        {'type': 'button', 'id': 'toggle_mode', 'text': 'Draw Mode', 'ideal_height': 45},
        {'type': 'button', 'id': 'border_mode', 'text': 'Add Border', 'ideal_height': 45},
        {'type': 'button_group', 'items': [
            {'id': 'color_r', 'text': '', 'width_ratio': 0.25},
            {'id': 'color_b', 'text': '', 'width_ratio': 0.25},
            {'id': 'color_y', 'text': '', 'width_ratio': 0.25},
            {'id': 'color_g', 'text': '', 'width_ratio': 0.25}
        ], 'ideal_height': 45},
        {'type': 'button_group', 'items': [
            {'id': 'back', 'text': 'Undo', 'width_ratio': 0.5},
            {'id': 'forward', 'text': 'Redo', 'width_ratio': 0.5}
        ], 'ideal_height': 45},
        {'type': 'button_group', 'items': [
            {'id': 'clear', 'text': 'Clear', 'width_ratio': 0.5},
            {'id': 'toggle', 'text': 'Xs', 'width_ratio': 0.5}
        ], 'ideal_height': 45},
    ]

    right_panel_layout = [
        {'type': 'button', 'id': 'new', 'text': 'New Puzzle', 'ideal_height': 45},
        {'type': 'button', 'id': 'save', 'text': 'Save Puzzle', 'ideal_height': 45},
        {'type': 'button_group', 'items': [
            {'id': 'import', 'text': 'Import', 'width_ratio': 0.5},
            {'id': 'export', 'text': 'Export', 'width_ratio': 0.5}
        ], 'ideal_height': 45},
        {'type': 'title', 'id': 'size_title', 'text': 'Board Size', 'ideal_height': 25},
        {'type': 'size_grid', 'id': 'size_selector', 'ideal_height': 160},
        {'type': 'button', 'id': 'find', 'text': 'Find Solution', 'ideal_height': 45, 'fixed_bottom': True},
        {'type': 'button', 'id': 'check', 'text': 'Check Solution', 'ideal_height': 45, 'fixed_bottom': True}
    ]

    # Combine layouts for the builder
    panel_layouts = [
        {'side': 'left', 'layout': left_panel_layout},
        {'side': 'right', 'layout': right_panel_layout}
    ]

    # --- INITIAL GAME STATE SETUP ---
    initial_puzzle_data = pz.get_puzzle_from_website(5) # Default to size_id 5
    if initial_puzzle_data:
        initial_puzzle_data['stars'] = const.PUZZLE_DEFINITIONS[5]['stars']
    else:
        print("Failed to load initial puzzle. Exiting."); sys.exit(1)
        
    game_state = GameState(initial_puzzle_data, fonts)
    ui_elements = ui.build_panels(panel_layouts, fonts)
    game_state.set_ui_elements(ui_elements)

    # Map action IDs to their handler functions for clean dispatching
    action_map = {
        'new': actions.handle_new_puzzle, 'save': actions.handle_save,
        'import': actions.handle_import, 'export': actions.handle_export,
        'clear': actions.handle_clear, 'toggle': actions.handle_toggle_mark_type,
        'back': actions.handle_undo, 'forward': actions.handle_redo,
        'toggle_mode': actions.handle_toggle_mode, 'border_mode': actions.handle_toggle_border_mode,
        'check': actions.handle_check_solution, 'find': actions.handle_find_solution,
    }

    # --- MAIN GAME LOOP ---
    running = True
    while running:
        # --- EVENT HANDLING ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            action = None
            for name, elem in game_state.ui_elements.items():
                if isinstance(elem, Button) and elem.handle_event(event):
                    action = name
                    break
            
            if action in action_map:
                action_map[action](game_state)
                continue

            # Special handling for button-like elements not in the action_map
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if 'size_selector' in game_state.ui_elements:
                    size_buttons = game_state.ui_elements['size_selector'].get('buttons', {})
                    for size_id, b_data in size_buttons.items():
                        if b_data['rect'].collidepoint(pos):
                            actions.handle_select_size(game_state, size_id)
                            break # Found a click, no need to check others
                
                color_map = {'color_r': 0, 'color_b': 1, 'color_y': 2, 'color_g': 3}
                if action in color_map:
                    actions.handle_select_color(game_state, color_map[action])

            handle_mouse_input(event, game_state)

        if not running: break

        # --- DRAWING ---
        ui.draw_game(game_state)
        clock.tick(60)

    pygame.quit()
    sys.exit()

def handle_mouse_input(event, game_state):
    """Processes all direct mouse interactions with the grid."""
    if event.type not in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
        return

    pos = event.pos
    is_on_grid = const.GRID_START_X <= pos[0] < const.GRID_START_X + const.GRID_AREA_WIDTH
    if not is_on_grid:
        return

    grid_pos = (pos[0] - const.GRID_START_X, pos[1])
    col = int(grid_pos[0] // game_state.cell_size)
    row = int(grid_pos[1] // game_state.cell_size)

    if game_state.is_border_mode:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                game_state.is_left_down = True
                game_state.current_border_path = {(row, col)}
            elif event.button == 3:
                game_state.is_right_down = True
                game_state.custom_borders = [b for b in game_state.custom_borders if (row, col) not in b[0]]
        elif event.type == pygame.MOUSEMOTION:
            if game_state.is_left_down and 0 <= row < game_state.grid_dim and 0 <= col < game_state.grid_dim:
                game_state.current_border_path.add((row, col))
            elif game_state.is_right_down:
                game_state.custom_borders = [b for b in game_state.custom_borders if (row, col) not in b[0]]
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                game_state.is_left_down = False
                if game_state.current_border_path:
                    color = const.DRAWING_COLORS[game_state.current_color_index][:3]
                    game_state.custom_borders.append((game_state.current_border_path, color))
                game_state.current_border_path = set()
            elif event.button == 3:
                game_state.is_right_down = False
        return

    if game_state.is_draw_mode:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: game_state.is_left_down = True
            if event.button == 3: game_state.is_right_down = True
            game_state.last_pos = grid_pos
        elif event.type == pygame.MOUSEMOTION and (game_state.is_left_down or game_state.is_right_down):
            color = const.DRAWING_COLORS[game_state.current_color_index] if game_state.is_left_down else (0,0,0,0)
            brush = game_state.brush_size if game_state.is_left_down else game_state.brush_size * 6
            if game_state.last_pos:
                pygame.draw.line(game_state.draw_surface, color, game_state.last_pos, grid_pos, int(brush * 2 + 1))
            pygame.draw.circle(game_state.draw_surface, color, grid_pos, brush)
            game_state.last_pos = grid_pos
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: game_state.is_left_down = False
            if event.button == 3: game_state.is_right_down = False
            game_state.last_pos = None
        return

    if 0 <= row < game_state.grid_dim and 0 <= col < game_state.grid_dim:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                game_state.is_left_down, game_state.is_dragging, game_state.click_cell = True, False, (row, col)
            elif event.button == 3:
                fs, ts = game_state.player_grid[row][col], const.STATE_EMPTY if game_state.player_grid[row][col] == const.STATE_STAR else const.STATE_STAR
                game_state.add_player_grid_change(row, col, fs, ts)
        elif event.type == pygame.MOUSEMOTION and game_state.is_left_down:
            game_state.is_dragging = True
            if game_state.player_grid[row][col] != const.STATE_SECONDARY_MARK:
                game_state.add_player_grid_change(row, col, game_state.player_grid[row][col], const.STATE_SECONDARY_MARK)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if not game_state.is_dragging and game_state.click_cell:
                    r, c = game_state.click_cell
                    fs = game_state.player_grid[r][c]
                    cycle = {0: 2, 2: 1, 1: 0}
                    game_state.add_player_grid_change(r, c, fs, cycle.get(fs, const.STATE_EMPTY))
                game_state.is_left_down, game_state.is_dragging, game_state.click_cell = False, False, None
            elif event.button == 3:
                game_state.is_right_down = False

if __name__ == "__main__":
    if not Z3_AVAILABLE:
        print("Warning: 'z3-solver' library not found. Solver buttons will be disabled.")
    main()

