# main.py
# Description: The main entry point for the Star Battle application.
# This file initializes the game and runs the main loop.

import os
import warnings
import pygame
import sys
import time
import copy

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import constants as const
import puzzle_handler as pz
import ui_manager as ui
from z3_solver import (
    Z3StarBattleSolver, validate_solver_solution_with_hash, format_duration, 
    Z3_AVAILABLE
)
from history_manager import HistoryManager
from ui_elements import Button

def main():
    """The main function to initialize and run the game application."""
    pygame.init()
    screen = pygame.display.set_mode((const.WINDOW_WIDTH, const.WINDOW_HEIGHT))
    pygame.display.set_caption("Star Battle Playground")
    clock = pygame.time.Clock()
    
    fonts = {
        'default': pygame.font.Font(None, 32),
        'small': pygame.font.Font(None, 24),
        'tiny': pygame.font.Font(None, 18)
    }
    
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
        {'type': 'title', 'id': 'size_title', 'text': 'Board Size', 'ideal_height': 25},
        {'type': 'size_grid', 'id': 'size_selector', 'ideal_height': 160},
        {'type': 'button', 'id': 'find', 'text': 'Find Solution', 'ideal_height': 45, 'fixed_bottom': True},
        {'type': 'button', 'id': 'check', 'text': 'Check Solution', 'ideal_height': 45, 'fixed_bottom': True}
    ]

    # --- INITIAL GAME STATE ---
    current_size_selection = 5
    puzzle_data = pz.get_puzzle_from_website(current_size_selection)
    if puzzle_data:
        puzzle_data['stars'] = const.PUZZLE_DEFINITIONS[current_size_selection]['stars']
    
    (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = pz.reset_game_state(puzzle_data)
    if not region_grid:
        print("Failed to load initial puzzle. Exiting."); sys.exit(1)
    
    history_manager = HistoryManager(player_grid)
    
    ui_elements = ui.build_panel_from_layout(panel_layout, fonts)
    
    mark_is_x, solution_status = True, None
    is_left_down, is_dragging, click_cell = False, False, None
    feedback_overlay_alpha, feedback_overlay_color = 0, const.COLOR_CORRECT
    FADE_SPEED = 4

    # --- MAIN GAME LOOP ---
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            def reset_feedback():
                nonlocal solution_status, feedback_overlay_alpha
                solution_status, feedback_overlay_alpha = None, 0

            action = None
            for name, elem in ui_elements.items():
                if isinstance(elem, Button):
                    result = elem.handle_event(event)
                    if result:
                        action = result
                        break 
            
            if not action and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                size_buttons = ui_elements.get('size_selector', {})
                for size_id, b_data in size_buttons.items():
                    if b_data['rect'].collidepoint(event.pos):
                        action = 'select_size'
                        current_size_selection = size_id
                        break
            
            if action:
                if action == 'back':
                    if history_manager.can_undo():
                        player_grid = history_manager.undo()
                        reset_feedback()
                elif action == 'forward':
                    if history_manager.can_redo():
                        player_grid = history_manager.redo()
                        reset_feedback()
                elif action == 'select_size' or action == 'new':
                    new_puzzle_data = pz.get_puzzle_from_website(current_size_selection)
                    if new_puzzle_data:
                        new_puzzle_data['stars'] = const.PUZZLE_DEFINITIONS[current_size_selection]['stars']
                        puzzle_data = new_puzzle_data
                        (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = pz.reset_game_state(puzzle_data)
                        history_manager.reset(player_grid)
                        reset_feedback()
                elif action == 'save':
                    comment = ui.get_comment_from_console()
                    pz.save_puzzle_entry(puzzle_data, player_grid, history_manager, comment)
                    screen = pygame.display.set_mode((const.WINDOW_WIDTH, const.WINDOW_HEIGHT))
                elif action == 'import':
                    input_string = ui.get_input_from_console()
                    screen = pygame.display.set_mode((const.WINDOW_WIDTH, const.WINDOW_HEIGHT))
                    if input_string:
                        new_puzzle_data, restored_manager = pz.universal_import(input_string)
                        if new_puzzle_data:
                            puzzle_data = new_puzzle_data
                            (region_grid, _, player_grid, current_grid_dim, cell_size, stars_per_region) = pz.reset_game_state(puzzle_data)
                            history_manager = restored_manager or HistoryManager(player_grid)
                            current_size_selection = -1
                            reset_feedback()
                    else: print("\nImport cancelled.")
                elif action == 'export':
                    if region_grid:
                        sbn_export = pz.encode_to_sbn(region_grid, stars_per_region, player_grid)
                        
                        raw_annotation_data = pz.encode_player_annotations(player_grid)
                        web_task_export = f"{puzzle_data.get('task', '')}{raw_annotation_data}"
                        
                        history_str = history_manager.serialize()
                        if history_str:
                            sbn_export += f"~{history_str}"
                            web_task_export += f"~{history_str}"

                        print("\n" + "="*50 + "\nEXPORTED PUZZLE STRINGS\n" + f"  -> SBN:      {sbn_export}\n" + f"  -> Web Task: {web_task_export}\n" + "="*50)
                elif action == 'clear':
                    initial_grid = [[const.STATE_EMPTY] * current_grid_dim for _ in range(current_grid_dim)]
                    history_manager.reset(initial_grid)
                    player_grid = history_manager.get_current_grid()
                    reset_feedback()
                elif action == 'toggle':
                    mark_is_x = not mark_is_x
                elif action == 'check':
                    is_correct = False
                    if not Z3_AVAILABLE:
                        solution_status = "Z3 Solver not available"
                    else:
                        print("Checking solution by solving with Z3...")
                        solver = Z3StarBattleSolver(region_grid, stars_per_region)
                        start_time = time.monotonic()
                        solutions, _ = solver.solve()
                        duration = time.monotonic() - start_time
                        print(f"Z3 solve time: {format_duration(duration)}")
                        player_solution_grid = [[1 if cell == const.STATE_STAR else 0 for cell in row] for row in player_grid]
                        if not solutions:
                            solution_status = "Incorrect! (No solution exists)"
                        elif player_solution_grid in solutions:
                            is_correct = True
                            solution_status = "Correct!" + (" (Multiple solutions exist)" if len(solutions) > 1 else "")
                        else:
                            solution_status = "Incorrect!"
                        if is_correct and puzzle_data.get('solution_hash'):
                            print("--- Performing secondary hash validation ---")
                            pz.check_solution(player_grid, puzzle_data)
                    feedback_overlay_color = const.COLOR_CORRECT if is_correct else const.COLOR_INCORRECT
                    feedback_overlay_alpha = 128
                elif action == 'find':
                    print("\n" + "="*40 + "\n--- Finding solution with Z3 Solver... ---")
                    solver = Z3StarBattleSolver(region_grid, stars_per_region)
                    start_time = time.monotonic()
                    solutions, _ = solver.solve()
                    duration = time.monotonic() - start_time
                    if not solutions: print("RESULT: No solution found.")
                    else:
                        print(f"RESULT: Found {len(solutions)} solution(s).")
                        validate_solver_solution_with_hash(solutions[0], puzzle_data)
                        pz.display_terminal_grid(region_grid, "Solution 1", solutions[0])
                    print(f"Solve time: {format_duration(duration)}\n" + "="*40 + "\n")
            
            # --- MOUSE INPUT HANDLING ---
            current_player_grid = history_manager.get_current_grid()
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                if pos[0] < const.GRID_AREA_WIDTH and not action:
                    col, row = int(pos[0] // cell_size), int(pos[1] // cell_size)
                    if 0 <= row < current_grid_dim and 0 <= col < current_grid_dim:
                        from_state = current_player_grid[row][col]
                        if event.button == 1: # Left Click
                            is_left_down, is_dragging, click_cell = True, False, (row, col)
                        elif event.button == 3: # Right Click
                            to_state = const.STATE_EMPTY if from_state == const.STATE_STAR else const.STATE_STAR
                            if from_state != to_state:
                                history_manager.add_change((row, col, from_state, to_state))
                                player_grid = history_manager.get_current_grid()
                                reset_feedback()
            
            elif event.type == pygame.MOUSEMOTION and is_left_down:
                is_dragging = True
                pos = event.pos
                if pos[0] < const.GRID_AREA_WIDTH:
                    col, row = int(pos[0] // cell_size), int(pos[1] // cell_size)
                    if 0 <= row < current_grid_dim and 0 <= col < current_grid_dim:
                        from_state = current_player_grid[row][col]
                        to_state = const.STATE_SECONDARY_MARK
                        if from_state != to_state:
                            history_manager.add_change((row, col, from_state, to_state))
                            player_grid = history_manager.get_current_grid()
                            reset_feedback()
            
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not is_dragging and click_cell:
                    row, col = click_cell
                    from_state = current_player_grid[row][col]
                    
                    # Cycle: Empty -> Secondary Mark (X) -> Star -> Empty
                    click_cycle_map = {
                        const.STATE_EMPTY: const.STATE_SECONDARY_MARK,
                        const.STATE_SECONDARY_MARK: const.STATE_STAR,
                        const.STATE_STAR: const.STATE_EMPTY,
                    }
                    to_state = click_cycle_map.get(from_state, const.STATE_EMPTY)

                    history_manager.add_change((row, col, from_state, to_state))
                    player_grid = history_manager.get_current_grid()
                    reset_feedback()
                is_left_down, is_dragging, click_cell = False, False, None
        
        # --- DRAWING ---
        screen.fill(const.COLOR_PANEL)
        if region_grid:
            ui.draw_background_colors(screen, region_grid, cell_size)
            ui.draw_player_marks(screen, player_grid, mark_is_x, cell_size)
            ui.draw_grid_lines(screen, region_grid, cell_size)
            ui.draw_feedback_overlay(screen, feedback_overlay_color, feedback_overlay_alpha)
        
        if feedback_overlay_alpha > 0:
            feedback_overlay_alpha = max(0, feedback_overlay_alpha - FADE_SPEED)
            
        ui.draw_control_panel(screen, fonts, ui_elements, current_size_selection, mark_is_x, solution_status, Z3_AVAILABLE, history_manager)
        pygame.display.set_caption(f"Star Battle ({stars_per_region} Stars)")
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    if not Z3_AVAILABLE:
        print("Warning: 'z3-solver' library not found. The 'Find Solution' and 'Check Solution' buttons will be disabled.")
    main()

