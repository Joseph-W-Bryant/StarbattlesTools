# history_manager.py
# Description: A class to manage a differential state history for undo/redo functionality.

import copy
from constants import SBN_CHAR_TO_INT, SBN_INT_TO_CHAR

class HistoryManager:
    """
    Manages a history of grid changes. It is self-contained and rebuilds the
    grid state on demand to ensure correctness.
    """
    def __init__(self, initial_state):
        self.initial_state = copy.deepcopy(initial_state)
        self.changes = []  # List of tuples: (row, col, from_state, to_state)
        self.pointer = 0

    def add_change(self, change):
        if self.pointer < len(self.changes):
            self.changes = self.changes[:self.pointer]
        self.changes.append(change)
        self.pointer += 1

    def get_current_grid(self):
        """Builds and returns the grid state at the current pointer."""
        grid = copy.deepcopy(self.initial_state)
        for i in range(self.pointer):
            r, c, _, to_state = self.changes[i]
            grid[r][c] = to_state
        return grid

    def undo(self):
        if self.can_undo():
            self.pointer -= 1
        return self.get_current_grid()

    def redo(self):
        if self.can_redo():
            self.pointer += 1
        return self.get_current_grid()

    def can_undo(self):
        return self.pointer > 0

    def can_redo(self):
        return self.pointer < len(self.changes)

    def reset(self, initial_state):
        self.initial_state = copy.deepcopy(initial_state)
        self.changes = []
        self.pointer = 0

    def serialize(self):
        if not self.changes: return ""
        change_strings = [f"{SBN_INT_TO_CHAR[r]}{SBN_INT_TO_CHAR[c]}{SBN_INT_TO_CHAR[f]}{SBN_INT_TO_CHAR[t]}" for r, c, f, t in self.changes]
        pointer_char = SBN_INT_TO_CHAR.get(self.pointer, '0')
        return f"h:{''.join(change_strings)}:{pointer_char}"

    @classmethod
    def deserialize(cls, initial_state, history_string):
        """Creates a HistoryManager from a serialized string."""
        manager = cls(initial_state)
        try:
            parts = history_string.split(':')
            if len(parts) != 3 or parts[0] != 'h':
                return manager
            change_data, pointer_data = parts[1], parts[2]
            if change_data:
                for i in range(0, len(change_data), 4):
                    s = change_data[i:i+4]
                    if len(s) == 4:
                        r, c, from_s, to_s = (SBN_CHAR_TO_INT[s[0]], SBN_CHAR_TO_INT[s[1]], 
                                              SBN_CHAR_TO_INT[s[2]], SBN_CHAR_TO_INT[s[3]])
                        manager.changes.append((r, c, from_s, to_s))
            manager.pointer = SBN_CHAR_TO_INT.get(pointer_data, 0)
        except (KeyError, IndexError, ValueError):
            return cls(initial_state)
        return manager

