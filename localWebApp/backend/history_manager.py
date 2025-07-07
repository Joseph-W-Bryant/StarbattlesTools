# --- File: backend/history_manager.py ---
import copy
from backend.constants import SBN_CHAR_TO_INT, SBN_INT_TO_CHAR

class HistoryManager:
    def __init__(self, initial_state):
        self.initial_state = copy.deepcopy(initial_state)
        self.changes = []
        self.pointer = 0
    def add_change(self, change):
        if self.pointer < len(self.changes):
            self.changes = self.changes[:self.pointer]
        self.changes.append(change)
        self.pointer += 1
    def get_current_grid(self):
        grid = copy.deepcopy(self.initial_state)
        for i in range(self.pointer):
            # This needs to access object properties if the format is a list of dicts
            change = self.changes[i]
            r, c, _, to_state = change['r'], change['c'], change['from'], change['to']
            grid[r][c] = to_state
        return grid
    def undo(self):
        if self.can_undo(): self.pointer -= 1
    def redo(self):
        if self.can_redo(): self.pointer += 1
    def can_undo(self): return self.pointer > 0
    def can_redo(self): return self.pointer < len(self.changes)
    def reset(self, initial_state):
        self.initial_state, self.changes, self.pointer = copy.deepcopy(initial_state), [], 0

    def serialize(self):
        if not self.changes: return ""
        # Correctly serialize from a list of dictionaries
        changes = [
            f"{SBN_INT_TO_CHAR.get(c['r'], '0')}{SBN_INT_TO_CHAR.get(c['c'], '0')}"
            f"{SBN_INT_TO_CHAR.get(c['from'], '0')}{SBN_INT_TO_CHAR.get(c['to'], '0')}"
            for c in self.changes
        ]
        pointer = SBN_INT_TO_CHAR.get(self.pointer, '0')
        return f"h:{''.join(changes)}:{pointer}"
        
    @classmethod
    def deserialize(cls, initial_state, history_string):
        manager = cls(initial_state)
        try:
            # Check if history_string is valid and has the correct format
            if not history_string or not history_string.startswith('h:'):
                return manager
                
            _, change_data, pointer_data = history_string.split(':')
            if change_data:
                for i in range(0, len(change_data), 4):
                    s = change_data[i:i+4]
                    if len(s) == 4:
                        # FIXED: Create a dictionary instead of a tuple to match the frontend
                        change = {
                            'r': SBN_CHAR_TO_INT.get(s[0]),
                            'c': SBN_CHAR_TO_INT.get(s[1]),
                            'from': SBN_CHAR_TO_INT.get(s[2]),
                            'to': SBN_CHAR_TO_INT.get(s[3]),
                        }
                        manager.changes.append(change)

            manager.pointer = SBN_CHAR_TO_INT.get(pointer_data, 0)
        except (KeyError, IndexError, ValueError) as e:
            print(f"Error deserializing history: {e}")
            return cls(initial_state) # Return a fresh manager on error
        return manager