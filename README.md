> **IMPORTANT NOTE:** The most up-to-date, runnable version of this program is located inside the `SeperatedMain` folder. Any Python files in the main root directory are for testing and development purposes and should not be run directly.

# Star Battle Playground

A feature-rich desktop application for playing, solving, and managing Star Battle puzzles. This tool is designed for both casual players and puzzle enthusiasts, offering a robust set of features including a powerful import/export system, a Z3-powered solver, and full session management.

## About the Game

Star Battle (also known as "Two Not Touch") is a logic puzzle where the objective is to place a set number of stars in each row, column, and outlined region of a grid. The key rule is that stars cannot be placed in adjacent cells, not even diagonally.

## Features

* **Dynamic Puzzle Loading:** Instantly fetch new puzzles of varying size and difficulty directly from `puzzle-star-battle.com`.
* **Full Undo/Redo:** Complete session history tracking for marks allows you to undo and redo every placement.
* **Advanced Solver:** Utilizes the Z3 SMT solver to check your solution or find one automatically.
* **Robust Import/Export:** A universal import function that correctly parses both **SBN** and **Web Task** formats. Export your current session to a portable string.
* **Save & Load Progress:** Save your current puzzle, including annotations and history, to a local `saved_puzzles.txt` file.
* **Annotation Tools:**
    * **Draw Mode:** Make freeform notes directly on the grid with multiple colors.
    * **Border Mode:** Draw custom, thick borders around any group of cells to highlight regions of interest.
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

## Controls

The application has three main interaction modes, which you can switch between using the buttons on the control panel.

### Mark Mode (Default)

This is the standard mode for solving the puzzle.

* **Place/Remove a Star:** **Right-click** on a cell to place a star. Right-click the star again to remove it.
* **Cycle Marks:** **Left-click** on a cell to cycle through the states: Empty -> X -> Star -> Empty.
* **Quickly Place X's:** **Left-click and drag** across multiple cells to quickly fill them with X marks.

### Add Border Mode

This mode allows you to draw custom, thick yellow borders to highlight regions.

* **Draw a Border:** **Left-click and drag** over a group of cells. The border will form around the outside of the shape you draw.
* **Erase a Border:** **Right-click and drag** over any part of a custom border to erase the entire shape.

### Draw Mode

This mode allows you to make freeform annotations on top of the grid.

* **Draw:** **Left-click and drag** to draw on the grid using the selected color.
* **Erase:** **Right-click and drag** to erase your drawings with a large circular eraser.

### Control Panel Buttons

* **New Puzzle:** Fetches a new puzzle from the web based on the selected size.
* **Save Puzzle:** Prompts you in the terminal to add a comment, then saves your complete session to `saved_puzzles.txt`.
* **Import/Export:** Import a puzzle from a string or export your current session to the terminal.
* **Clear:** Clears player marks (Mark Mode), custom borders (Border Mode), or drawings (Draw Mode).
* **Toggle (Xs/Dots):** Switches the appearance of the secondary mark.
* **Undo / Redo:** Steps forward or backward through your history of placed marks. (Does not affect drawings or custom borders).
* **Draw Mode/Add Border/Mark Mode:** Switches between the main interaction modes.
* **Color Swatches:** In Draw Mode, select your drawing color.
* **Board Size Grid:** Select a puzzle size and difficulty to fetch a new puzzle.
* **Find/Check Solution:** Uses the Z3 solver to find a solution or check your current work.

