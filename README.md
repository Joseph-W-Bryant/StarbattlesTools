# Star Battle Web App

This is a web-based version of the Star Battle puzzle game with a Python/Flask backend and a plain HTML/CSS/JS frontend. This project was refactored from an original Pygame application.

## How to Run Locally

This setup uses a standard Python packaging approach that guarantees the backend will run correctly.

### 1. Backend Server Setup

First, ensure you have Python 3 installed.

**Navigate to the project's ROOT directory (`StarbattlesTools/`).**

Create and activate a virtual environment (highly recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

**Install the project in "editable" mode:**
This command reads the `pyproject.toml` file, installs all dependencies from it, and links your source code to your Python environment. This permanently solves all import errors.
```bash
pip install -e .
```
*(The `.` refers to the current directory)*

### 2. Run the Backend Server

Now, run the server using the simple launcher script:
```bash
python run.py
```
The backend will now be running at `http://127.0.0.1:5001`. Keep this terminal window open.

### 3. Frontend Application

1.  Open the root project folder (`StarbattlesTools`) in VS Code.
2.  Install the **Live Server** extension from the Extensions marketplace.
3.  Navigate to `frontend/index.html`.
4.  Right-click the file and select "Open with Live Server".
5.  Your default web browser will open the application.

