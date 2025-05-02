# app.py
# Main application file for the ShowGo Slideshow Kiosk

import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

# --- Configuration ---
# Define base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define paths for uploads and configuration relative to the base directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, 'thumbnails')
CONFIG_FOLDER = os.path.join(BASE_DIR, 'config')
CONFIG_FILE = os.path.join(CONFIG_FOLDER, 'config.json')

# Ensure necessary directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = THUMBNAIL_FOLDER
# Add a secret key for session management (needed for flash messages later)
# In a real app, use a more secure, randomly generated key, possibly from environment variables
app.secret_key = 'dev-secret-key'

# --- Routes ---

@app.route('/')
def slideshow_viewer():
    """
    Route for the main slideshow display page.
    For now, it just renders a placeholder template.
    """
    # Later, we'll load config, get images, fetch widget data, etc.
    print("Accessing slideshow viewer route") # Debug print
    # We need to create this template file next
    # return render_template('slideshow.html')
    return "<h1>Slideshow Viewer Page (Placeholder)</h1>" # Simple placeholder for now

@app.route('/config')
def config_page():
    """
    Route for the configuration interface.
    For now, it just renders a placeholder template.
    Needs password protection later.
    """
    # Later, we'll add authentication and load existing config/images
    print("Accessing config page route") # Debug print
    # We need to create this template file next
    # return render_template('config.html')
    return "<h1>Configuration Page (Placeholder)</h1>" # Simple placeholder for now

# --- Running the App ---
if __name__ == '__main__':
    # Runs the Flask development server
    # Debug=True enables auto-reloading and detailed error pages
    # Host='0.0.0.0' makes it accessible on your network (use with caution)
    # Use port 5000 by default, can be changed with port=xxxx
    print(f"Base directory: {BASE_DIR}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Config folder: {CONFIG_FOLDER}")
    app.run(debug=True, host='0.0.0.0')
