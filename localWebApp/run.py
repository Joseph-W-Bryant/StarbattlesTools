# run.py
# This script launches the Flask application.
# Because the project is installed in editable mode via pyproject.toml,
# Python now knows where to find the 'backend' package without any path manipulation.

from backend.app import app

if __name__ == '__main__':
    # Run the Flask app.
    # The 'debug=True' flag enables auto-reloading when backend files are changed.
    app.run(host='0.0.0.0', port=5001, debug=True)

