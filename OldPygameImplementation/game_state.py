# game_state.py
# Description: A centralized class to manage the entire state of the application.

import pygame
import constants as const
import puzzle_handler as pz
from history_manager import HistoryManager

class GameState:
    """
    Manages the complete, centralized state of the Star Battle application,
    acting as a single source of truth for all dynamic data.
    """
    def __init__(self, puzzle_data, fonts):
        """Initializes the game state with the first puzzle."""
        self.fonts = fonts
        self.ui_elements = {}
        self.current_size_selection = 5
        self.screen = pygame.display.set_mode((const.WINDOW_WIDTH, const.WINDOW_HEIGHT))
        
        # Core puzzle components
        self.puzzle_data = {}
        self.region_grid = None
        self.player_grid = None
        self.grid_dim = 0
        self.cell_size = 0
        self.stars_per_region = 0
        self.history = HistoryManager([[]]) # Dummy init

        # Drawing Mode
        self.is_draw_mode = False
        self.draw_surface = pygame.Surface((const.GRID_AREA_WIDTH, const.GRID_AREA_HEIGHT), pygame.SRCALPHA)
        self.current_color_index = 0
        self.brush_size = 3
        self.last_pos = None # Will store coordinates relative to the grid surface

        # Border Mode (Free-form)
        self.is_border_mode = False
        # List of tuples: ({(r,c), ...}, (R,G,B))
        self.custom_borders = [] 
        self.current_border_path = set()

        # General State
        self.mark_is_x = True
        self.solution_status = None
        self.feedback_overlay_alpha = 0
        self.feedback_overlay_color = const.COLOR_CORRECT
        
        self.is_left_down = False
        self.is_right_down = False
        
        self.is_dragging = False
        self.click_cell = None
        
        self.reset_puzzle_state(puzzle_data)


    def set_ui_elements(self, ui_elements):
        """Stores the constructed UI elements."""
        self.ui_elements = ui_elements

    def reset_puzzle_state(self, puzzle_data):
        """
        Resets the game state with new puzzle data, correctly handling imported
        history and annotations.
        """
        if not puzzle_data or 'task' not in puzzle_data:
            print("Error: Invalid puzzle data provided for reset.")
            return

        self.puzzle_data = puzzle_data
        (self.region_grid, _, self.player_grid, self.grid_dim, 
         self.cell_size, self.stars_per_region) = pz.reset_game_state(puzzle_data)

        if not self.region_grid:
            print("Failed to load puzzle from data. State not reset.")
            return
            
        restored_manager = puzzle_data.get('history_manager')

        if restored_manager:
            self.history = restored_manager
            self.player_grid = self.history.get_current_grid()
        else:
            self.history = HistoryManager(self.player_grid)

        # Clear all temporary user visuals and modes
        self.draw_surface.fill((0, 0, 0, 0))
        self.custom_borders = []
        self.current_border_path = set()
        self.is_draw_mode = False
        self.is_border_mode = False
        self.reset_feedback()
        print(f"Game state reset for a {self.grid_dim}x{self.grid_dim} puzzle.")

    def update_player_grid_from_history(self):
        """Safely updates the player grid from the history manager."""
        self.player_grid = self.history.get_current_grid()
        self.reset_feedback()

    def add_player_grid_change(self, r, c, from_state, to_state):
        """Adds a change to the history and updates the grid."""
        if from_state != to_state:
            self.history.add_change((r, c, from_state, to_state))
            self.update_player_grid_from_history()

    def reset_feedback(self):
        """Resets the solution feedback overlay."""
        self.solution_status = None
        self.feedback_overlay_alpha = 0

