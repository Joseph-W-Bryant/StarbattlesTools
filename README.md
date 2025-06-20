> **IMPORTANT NOTE:** The most up-to-date, runnable version of this program is located inside the `SeperatedMain` folder. Any Python files in the main root directory are for testing and development purposes and should not be run directly.

# Star Battle Playground

A feature-rich desktop application for playing, solving, and managing Star Battle puzzles. This tool is designed for both casual players and puzzle enthusiasts, offering a robust set of features including a powerful import/export system, a Z3-powered solver, and full session management.

## About the Game

Star Battle (also known as "Two Not Touch") is a logic puzzle where the objective is to place a set number of stars in each row, column, and outlined region of a grid. The key rule is that stars cannot be placed in adjacent cells, not even diagonally.

## Features

* **Dynamic Puzzle Loading:** Instantly fetch new puzzles of varying size and difficulty directly from `puzzle-star-battle.com`.
* **Full Undo/Redo:** Complete session history tracking allows you to undo and redo every move.
* **Advanced Solver:** Utilizes the Z3 SMT solver to:
    * **Check Solution:** Instantly verify if your solution is correct.
    * **Find Solution:** Automatically find a valid solution for the current puzzle.
* **Robust Import/Export:**
    * A universal import function that correctly parses both **SBN** and **Web Task** formats.
    * Handles complex strings containing the base puzzle, player annotations, and full history data.
    * Export your current session to a portable string.
* **Save & Load Progress:**
    * Save your current puzzle, including annotations and history, to a local `saved_puzzles.txt` file with an optional comment.
    * Import any saved puzzle to continue exactly where you left off.
* **Draw Mode:** Toggle between the standard marking mode and a freeform drawing mode with multiple colors and an eraser to make notes directly on the grid.
* **Intuitive UI:** A clean interface with a dedicated control panel for all major actions.

## Installation

This application is built with Python and requires a few external libraries.

**1. Prerequisites:**
* Python 3.7 or newer.

**2. Install Libraries:**
The recommended way to install the libraries is using `pip`, Python's package installer. Open your terminal or command prompt and run the following commands:

```bash
pip install pygame
pip install requests
pip install z3-solver
```

> **Note for Linux Users:**
> Some Linux distributions manage Python packages through their native package manager (like `apt`, `dnf`, or `pacman`). If you prefer this method, or if `pip` gives an "externally-managed environment" error, you should use your system's package manager instead. The package names are often prefixed with `python-` or `python3-`.
>
> For example, on **Debian or Ubuntu-based systems**, the command would be:
> ```bash
> sudo apt update
> sudo apt install python3-pygame python3-requests python3-z3
> ```

## How to Run

1.  Clone or download this repository to your local machine.
2.  Navigate to the `SeperatedMain` folder in your terminal.
3.  Run the application with the following command:

```bash
python3 main.py
```

## How to Use the Application

### Basic Gameplay
* **Place a Star:** **Right-click** on an empty cell. Right-click again to remove it.
* **Place a Secondary Mark (Dot/X):**
    * **Left-click** on a cell to cycle through the states: Empty -> Mark -> Star -> Empty.
    * **Left-click and drag** across multiple cells to quickly place secondary marks.
* **Toggle Mark Type:** Use the "Xs" / "Dots" button on the control panel to switch the appearance of the secondary mark.

### Control Panel
* **New Puzzle:** Fetches a new puzzle from the web based on the selected size. If no size is selected (e.g., after an import), it defaults to a 10x10 medium puzzle.
* **Save Puzzle:** Prompts you in the terminal to add a comment, then saves your complete session (puzzle, annotations, and history) to `saved_puzzles.txt`.
* **Import:** Prompts you in the terminal to paste a puzzle string (either SBN or Web Task format).
* **Export:** Prints the SBN and Web Task strings for your current session to the terminal.
* **Clear:** In Mark Mode, this clears all your stars and marks. In Draw Mode, it erases all drawings.
* **Undo / Redo:** Step backward or forward through your move history.
* **Draw Mode / Mark Mode:** Toggles between placing puzzle marks and freeform drawing on the grid.
* **Color Swatches:** When in Draw Mode, select your drawing color. Right-click while drawing to erase.
* **Board Size Grid:** Select a puzzle size and difficulty. This will immediately fetch a new puzzle.
* **Find Solution:** Uses the Z3 solver to find and display a valid solution in the terminal.
* **Check Solution:** Uses the Z3 solver to verify if your current placement of stars is a correct solution. The result ("Correct!" or "Incorrect!") is displayed on the panel.

### File Structure

The project is organized into several modules to separate concerns:
* `main.py`: The main entry point of the application. Contains the game loop and event handling logic.
* `game_state.py`: A centralized class that holds and manages all dynamic state for the application.
* `action_handlers.py`: Contains the functions that execute when UI buttons are pressed (e.g., `handle_new_puzzle`).
* `puzzle_handler.py`: Manages all data-heavy logic, including the `universal_import` function and all encoding/decoding for the SBN and Web Task formats.
* `ui_manager.py`: Responsible for all drawing and rendering logic, including building the control panel and drawing the grid.
* `ui_elements.py`: Defines UI components, such as the `Button` class.
* `z3_solver.py`: Contains the `Z3StarBattleSolver` class and all logic related to interacting with the Z3 library.
* `history_manager.py`: A self-contained class for managing the undo/redo change list.
* `constants.py`: Stores all static values like colors, dimensions, and UI constants.

