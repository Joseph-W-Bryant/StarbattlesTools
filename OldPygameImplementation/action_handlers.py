# action_handlers.py
# Description: Contains all functions that handle UI events and actions.

import pygame
import time
import constants as const
import puzzle_handler as pz
import ui_manager as ui
from z3_solver import Z3StarBattleSolver, validate_solver_solution_with_hash, format_duration, Z3_AVAILABLE
from history_manager import HistoryManager

# --- Button Action Handlers ---

def handle_new_puzzle(game_state):
    """
    Loads a new puzzle from the website based on the current size selection.
    If no size is selected (e.g., after an import), it defaults to 10x10 medium.
    """
    size_to_fetch = game_state.current_size_selection
    if size_to_fetch == -1:
        print("No size selected, defaulting to 10x10 Medium (ID: 5).")
        size_to_fetch = 5

    print(f"\nRequesting new puzzle for size ID: {size_to_fetch}")
    new_puzzle_data = pz.get_puzzle_from_website(size_to_fetch)

    if new_puzzle_data:
        new_puzzle_data['stars'] = const.PUZZLE_DEFINITIONS[size_to_fetch]['stars']
        game_state.reset_puzzle_state(new_puzzle_data)
        game_state.current_size_selection = size_to_fetch

def handle_save(game_state):
    """Saves the current puzzle state, including history, to a file."""
    comment = ui.get_comment_from_console()
    pz.save_puzzle_entry(game_state.puzzle_data, game_state.player_grid, game_state.history, comment)
    game_state.screen = pygame.display.set_mode((const.WINDOW_WIDTH, const.WINDOW_HEIGHT))

def handle_import(game_state):
    """Imports a puzzle from a user-provided string."""
    input_string = ui.get_input_from_console()
    game_state.screen = pygame.display.set_mode((const.WINDOW_WIDTH, const.WINDOW_HEIGHT))
    if input_string:
        new_puzzle_data = pz.universal_import(input_string)
        if new_puzzle_data:
            game_state.reset_puzzle_state(new_puzzle_data)
            game_state.current_size_selection = -1
    else:
        print("\nImport cancelled.")

def handle_export(game_state):
    """Prints export strings for the current puzzle state to the console."""
    if game_state.region_grid:
        sbn_export = pz.encode_to_sbn(game_state.region_grid, game_state.stars_per_region, game_state.player_grid)
        raw_annotation_data = pz.encode_player_annotations(game_state.player_grid)
        web_task_export = f"{game_state.puzzle_data.get('task', '')}{raw_annotation_data}"
        
        history_str = game_state.history.serialize()
        if history_str:
            sbn_export += f"~{history_str}"
            web_task_export += f"~{history_str}"
            
        print("\n" + "="*50 + "\nEXPORTED PUZZLE STRINGS\n" + 
              f"  -> SBN:      {sbn_export}\n" + 
              f"  -> Web Task: {web_task_export}\n" + "="*50)

def handle_clear(game_state):
    """Clears either drawings, borders, or player marks depending on the current mode."""
    if game_state.is_draw_mode:
        game_state.draw_surface.fill((0, 0, 0, 0))
    elif game_state.is_border_mode:
        game_state.custom_borders = []
    else:
        initial_grid = [[const.STATE_EMPTY] * game_state.grid_dim for _ in range(game_state.grid_dim)]
        game_state.history.reset(initial_grid)
        game_state.update_player_grid_from_history()

def handle_toggle_mark_type(game_state):
    """Toggles the secondary mark between an 'X' and a dot."""
    game_state.mark_is_x = not game_state.mark_is_x

def handle_toggle_mode(game_state):
    """Toggles between marking mode and drawing mode."""
    game_state.is_draw_mode = not game_state.is_draw_mode
    if game_state.is_draw_mode:
        game_state.is_border_mode = False

def handle_toggle_border_mode(game_state):
    """Toggles between marking mode and border drawing mode."""
    game_state.is_border_mode = not game_state.is_border_mode
    if game_state.is_border_mode:
        game_state.is_draw_mode = False

def handle_undo(game_state):
    """Undoes the last action."""
    if game_state.history.can_undo():
        game_state.history.undo()
        game_state.update_player_grid_from_history()

def handle_redo(game_state):
    """Redoes the last undone action."""
    if game_state.history.can_redo():
        game_state.history.redo()
        game_state.update_player_grid_from_history()

def handle_check_solution(game_state):
    """Uses the Z3 solver to check if the user's solution is correct."""
    if not Z3_AVAILABLE:
        game_state.solution_status = "Z3 Solver not available"
        return
        
    print("\n" + "="*40 + f"\n--- Running Z3 Solver for: Check Solution ---")
    solver = Z3StarBattleSolver(game_state.region_grid, game_state.stars_per_region)
    start_time = time.monotonic()
    solutions, _ = solver.solve()
    duration = time.monotonic() - start_time
    print(f"Z3 solve time: {format_duration(duration)}")

    player_solution_grid = [[1 if cell == const.STATE_STAR else 0 for cell in row] for row in game_state.player_grid]
    
    is_correct = False
    if not solutions:
        game_state.solution_status = "Incorrect! (No solution exists)"
    elif player_solution_grid in solutions:
        is_correct = True
        game_state.solution_status = "Correct!" + (" (Multiple solutions exist)" if len(solutions) > 1 else "")
    else:
        game_state.solution_status = "Incorrect!"
    
    if is_correct and game_state.puzzle_data.get('solution_hash'):
        print("--- Performing secondary hash validation ---")
        pz.check_solution(game_state.player_grid, game_state.puzzle_data)

    game_state.feedback_overlay_color = const.COLOR_CORRECT if is_correct else const.COLOR_INCORRECT
    game_state.feedback_overlay_alpha = 128

def handle_find_solution(game_state):
    """Uses the Z3 solver to find a valid solution."""
    if not Z3_AVAILABLE:
        game_state.solution_status = "Z3 Solver not available"
        return

    print("\n" + "="*40 + f"\n--- Running Z3 Solver for: Find Solution ---")
    solver = Z3StarBattleSolver(game_state.region_grid, game_state.stars_per_region)
    start_time = time.monotonic()
    solutions, _ = solver.solve()
    duration = time.monotonic() - start_time
    print(f"Z3 solve time: {format_duration(duration)}")

    if not solutions:
        print("RESULT: No solution found.")
    else:
        print(f"RESULT: Found {len(solutions)} solution(s).")
        if game_state.puzzle_data.get('solution_hash'):
            validate_solver_solution_with_hash(solutions[0], game_state.puzzle_data)
        pz.display_terminal_grid(game_state.region_grid, "Solution 1", solutions[0])
    print("="*40 + "\n")

# --- Other UI Handlers ---

def handle_select_size(game_state, size_id):
    """Handles the user clicking on a new puzzle size button."""
    game_state.current_size_selection = size_id
    handle_new_puzzle(game_state)

def handle_select_color(game_state, color_index):
    """Sets the current drawing color."""
    game_state.current_color_index = color_index

