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
    
    # Data-driven layout for the control panel
    panel_layout = [
        {'type': 'button', 'id': 'new', 'text': 'New Puzzle', 'ideal_height': 45},
        {'type': 'button', 'id': 'save', 'text': 'Save Puzzle', 'ideal_height': 45},
        {'type': 'button_group', 'ideal_height': 45, 'items': [
            {'id': 'import', 'text': 'Import', 'width_ratio': 0.5},
            {'id': 'export', 'text': 'Export', 'width_ratio': 0.5}
        ]},
        {'type': 'button_group', 'ideal_height': 45, 'items': [
            {'id': 'clear', 'text': 'Clear', 'width_ratio': 0.5},
            {'id': 'toggle', 'text': 'Xs', 'width_ratio': 0.5}
        ]},
        {'type': 'button_group', 'ideal_height': 45, 'items': [
            {'id': 'back', 'text': 'Undo', 'width_ratio': 0.5},
            {'id': 'forward', 'text': 'Redo', 'width_ratio': 0.5}
        ]},
        {'type': 'button', 'id': 'toggle_mode', 'text': 'Draw Mode', 'ideal_height': 45},
        {'type': 'button_group', 'ideal_height': 45, 'items': [
            {'id': 'color_r', 'text': '', 'width_ratio': 0.25},
            {'id': 'color_b', 'text': '', 'width_ratio': 0.25},
            {'id': 'color_y', 'text': '', 'width_ratio': 0.25},
            {'id': 'color_g', 'text': '', 'width_ratio': 0.25}
        ]},
        {'type': 'title', 'id': 'size_title', 'text': 'Board Size', 'ideal_height': 25},
        {'type': 'size_grid', 'id': 'size_selector', 'ideal_height': 160},
        {'type': 'button', 'id': 'find', 'text': 'Find Solution', 'ideal_height': 45, 'fixed_bottom': True},
        {'type': 'button', 'id': 'check', 'text': 'Check Solution', 'ideal_height': 45, 'fixed_bottom': True}
    ]

    # --- INITIAL GAME STATE SETUP ---
    initial_puzzle_data = pz.get_puzzle_from_website(5) # Default to size_id 5
    if initial_puzzle_data:
        # The website puzzle data doesn't contain the star count, so we add it from our constants
        initial_puzzle_data['stars'] = const.PUZZLE_DEFINITIONS[5]['stars']
    else:
        print("Failed to load initial puzzle. Exiting."); sys.exit(1)
        
    game_state = GameState(initial_puzzle_data, fonts)
    ui_elements = ui.build_panel_from_layout(panel_layout, fonts)
    game_state.set_ui_elements(ui_elements)

    # Map action IDs to their handler functions for clean dispatching
    action_map = {
        'new': actions.handle_new_puzzle,
        'save': actions.handle_save,
        'import': actions.handle_import,
        'export': actions.handle_export,
        'clear': actions.handle_clear,
        'toggle': actions.handle_toggle_mark_type,
        'back': actions.handle_undo,
        'forward': actions.handle_redo,
        'toggle_mode': actions.handle_toggle_mode,
        'check': actions.handle_check_solution,
        'find': actions.handle_find_solution,
    }

    # --- MAIN GAME LOOP ---
    running = True
    while running:
        # --- EVENT HANDLING ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            # Check for button clicks first
            action = None
            for name, elem in game_state.ui_elements.items():
                if isinstance(elem, Button) and elem.handle_event(event):
                    action = name
                    break
            
            # Dispatch to mapped action handler if a button was clicked
            if action in action_map:
                action_map[action](game_state)
                continue

            # Handle non-mapped UI element interactions that require a MOUSEBUTTONDOWN event
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                # Size selector grid
                size_buttons = game_state.ui_elements.get('size_selector', {})
                if size_buttons:
                    for size_id, b_data in size_buttons.items():
                        if b_data['rect'].collidepoint(pos):
                            actions.handle_select_size(game_state, size_id)
                            break # Found the clicked size, no need to check others
                
                # Color selector swatches (check if an action ID for a color button was found)
                color_map = {'color_r': 0, 'color_b': 1, 'color_y': 2, 'color_g': 3}
                if action in color_map:
                    actions.handle_select_color(game_state, color_map[action])

            # Handle direct grid and drawing input (now safely filtered)
            handle_mouse_input(event, game_state)

        if not running: break

        # --- DRAWING ---
        ui.draw_game(game_state)
        clock.tick(60)

    pygame.quit()
    sys.exit()

def handle_mouse_input(event, game_state):
    """Processes all direct mouse interactions with the grid."""
    # --- ADDED GUARD ---
    # Only proceed for events that have a 'pos' attribute.
    if event.type not in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
        return

    pos = event.pos
    if pos[0] >= const.GRID_AREA_WIDTH:
        return # Mouse is over the control panel, ignore grid input

    # --- MOUSE BUTTON DOWN ---
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1: game_state.is_left_down = True
        if event.button == 3: game_state.is_right_down = True
        
        if game_state.is_draw_mode:
            game_state.last_pos = pos
        else: # Mark Mode
            col = int(pos[0] // game_state.cell_size)
            row = int(pos[1] // game_state.cell_size)
            if 0 <= row < game_state.grid_dim and 0 <= col < game_state.grid_dim:
                if event.button == 1: # Left click (for single click or drag start)
                    game_state.is_dragging = False
                    game_state.click_cell = (row, col)
                elif event.button == 3: # Right click (place star)
                    from_state = game_state.player_grid[row][col]
                    to_state = const.STATE_EMPTY if from_state == const.STATE_STAR else const.STATE_STAR
                    game_state.add_player_grid_change(row, col, from_state, to_state)

    # --- MOUSE MOTION ---
    elif event.type == pygame.MOUSEMOTION:
        if game_state.is_draw_mode and (game_state.is_left_down or game_state.is_right_down):
            color = const.DRAWING_COLORS[game_state.current_color_index] if game_state.is_left_down else (0,0,0,0) # Right click is eraser
            current_brush_size = game_state.brush_size if game_state.is_left_down else game_state.brush_size * 3
            if game_state.last_pos is not None:
                pygame.draw.line(game_state.draw_surface, color, game_state.last_pos, pos, current_brush_size * 2 + 1)
            pygame.draw.circle(game_state.draw_surface, color, pos, current_brush_size)
            game_state.last_pos = pos
        elif not game_state.is_draw_mode and game_state.is_left_down: # Dragging in Mark Mode
            game_state.is_dragging = True
            col = int(pos[0] // game_state.cell_size)
            row = int(pos[1] // game_state.cell_size)
            if 0 <= row < game_state.grid_dim and 0 <= col < game_state.grid_dim:
                from_state = game_state.player_grid[row][col]
                if from_state != const.STATE_SECONDARY_MARK:
                    game_state.add_player_grid_change(row, col, from_state, const.STATE_SECONDARY_MARK)

    # --- MOUSE BUTTON UP ---
    elif event.type == pygame.MOUSEBUTTONUP:
        if event.button == 1: game_state.is_left_down = False
        if event.button == 3: game_state.is_right_down = False
        
        if game_state.is_draw_mode:
            game_state.last_pos = None
        elif not game_state.is_dragging and game_state.click_cell and event.button == 1: # Single left click in Mark Mode
            row, col = game_state.click_cell
            from_state = game_state.player_grid[row][col]
            click_cycle_map = {
                const.STATE_EMPTY: const.STATE_SECONDARY_MARK,
                const.STATE_SECONDARY_MARK: const.STATE_STAR,
                const.STATE_STAR: const.STATE_EMPTY,
            }
            to_state = click_cycle_map.get(from_state, const.STATE_EMPTY)
            game_state.add_player_grid_change(row, col, from_state, to_state)
            
        game_state.click_cell = None
        game_state.is_dragging = False

if __name__ == "__main__":
    if not Z3_AVAILABLE:
        print("Warning: 'z3-solver' library not found. The 'Find Solution' and 'Check Solution' buttons will be disabled.")
    main()

