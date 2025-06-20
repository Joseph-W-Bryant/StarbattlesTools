# history_manager.py
# Description: A class to manage the state history for undo/redo functionality.

import copy

class HistoryManager:
    """
    Manages a history of grid states to allow for undo and redo operations.
    """
    def __init__(self, initial_state):
        """
        Initializes the history with the starting state of the grid.
        
        Args:
            initial_state: The initial 2D list representing the player grid.
        """
        # We use deepcopy to ensure states are independent
        self.history = [copy.deepcopy(initial_state)]
        self.pointer = 0

    def add_state(self, state):
        """
        Adds a new state to the history. This clears any future 'redo' states.
        
        Args:
            state: The new 2D list grid state to add.
        """
        # If the pointer is not at the end of history, trim the future states
        if self.pointer < len(self.history) - 1:
            self.history = self.history[:self.pointer + 1]
            
        # Add the new state
        self.history.append(copy.deepcopy(state))
        self.pointer += 1

    def undo(self):
        """
        Moves the pointer back one step and returns the previous state.
        
        Returns:
            The previous grid state, or the current state if no undo is possible.
        """
        if self.can_undo():
            self.pointer -= 1
        return copy.deepcopy(self.history[self.pointer])

    def redo(self):
        """
        Moves the pointer forward one step and returns the next state.
        
        Returns:
            The next grid state, or the current state if no redo is possible.
        """
        if self.can_redo():
            self.pointer += 1
        return copy.deepcopy(self.history[self.pointer])

    def can_undo(self):
        """Checks if an undo operation is possible."""
        return self.pointer > 0

    def can_redo(self):
        """Checks if a redo operation is possible."""
        return self.pointer < len(self.history) - 1

    def reset(self, initial_state):
        """Resets the history to a new initial state."""
        self.history = [copy.deepcopy(initial_state)]
        self.pointer = 0

