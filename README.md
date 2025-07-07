# Star Battle Web App

This repository contains a web-based version of the Star Battle puzzle game. It features a robust Python/Flask backend for puzzle generation and solving, and a responsive HTML/CSS/JS frontend for gameplay.

This project has two primary ways to run it: a zero-setup live demo and a fully self-hosted local version.

---

## Option 1: Live Demo (No Setup Required)

This is the quickest way to try the application. The frontend is pre-configured to connect to a live backend server hosted on PythonAnywhere.

### How to Run:
1.  Navigate into the `LiveDemo/` folder.
2.  Open the `index.html` file directly in your web browser (e.g., Chrome, Firefox, Safari).

That's it! The application will load and be fully functional.

---

## Option 2: Local Web App (Self-Hosted)

This option allows you to run both the backend server and the frontend on your own machine. This is ideal for development, offline use, or if you wish to host the entire application yourself. The frontend in the `localWebApp` folder is already configured to connect to the local backend.

### 1. Backend Server Setup

First, ensure you have Python 3 installed.

**Navigate to the `localWebApp/` directory.** All subsequent commands should be run from here.

Create and activate a virtual environment (highly recommended):
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
py -m venv venv
venv\Scripts\activate
```

Install the project in "editable" mode. This command reads the `pyproject.toml` file, installs all dependencies, and correctly configures the Python path.
```bash
pip install -e .
```
*(The `.` refers to the current directory, `localWebApp/`)*

### 2. Run the Backend Server

With your virtual environment still active, run the server:
```bash
python run.py
```
The backend will now be running at `http://127.0.0.1:5001`. Keep this terminal window open.

### 3. Run the Frontend Application

With the backend server running, simply open the `localWebApp/index.html` file in your web browser. The application will connect to your local backend and be fully functional.

> **Note:** The frontend files in `LiveDemo/` and `localWebApp/` are identical except for the `API_BASE_URL` variable in `script.js`, which is pre-set in each version to point to the correct backend.

---

## Miscellaneous Tools

This repository also includes a `MiscTools/` folder. This directory contains a collection of various scripts and utilities that are not part of the core puzzle application but may be useful for advanced users or for performing other interesting tasks. Feel free to explore them if you're curious.

