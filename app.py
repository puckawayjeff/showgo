# app.py
# Main application file for the ShowGo Slideshow Kiosk

import os
import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_httpauth import HTTPBasicAuth # Import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash # For more secure password handling (optional but recommended)

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

# --- Default Configuration ---
# !! IMPORTANT: Storing plain text passwords in config is NOT secure for production.
#    Consider environment variables or a more robust user management system.
#    For slightly better security here, we *could* store a hash instead of plain text,
#    but the fundamental issue of storing credentials in a potentially accessible file remains.
DEFAULT_CONFIG = {
    "slideshow": {
        "duration_seconds": 10,
        "transition_effect": "fade",
        "image_order": "sequential"
    },
    "watermark": {
        "enabled": False,
        "text": "© Your Company",
        "position": "bottom-right",
        "move": True
    },
    "widgets": {
        "time": {"enabled": True},
        "weather": {"enabled": True, "location": "Oshkosh, WI", "api_key": ""},
        "rss": {"enabled": False, "feed_url": ""}
    },
    "auth": {
         "username": "admin",
         # Store a hash of the default password 'password'
         # If you change the default password, generate a new hash using:
         # from werkzeug.security import generate_password_hash
         # print(generate_password_hash('your_new_password'))
         "password_hash": generate_password_hash("password")
         # "password": "password" # Original plain text - less secure
    }
}

# --- Configuration Loading/Saving Functions ---

def load_config():
    """Loads configuration from config.json, falling back to defaults."""
    needs_resave = False # Flag to indicate if migration happened
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded_settings = json.load(f)
                # Merge with defaults carefully to ensure all keys/subkeys exist
                config = DEFAULT_CONFIG.copy()
                for key, default_value in DEFAULT_CONFIG.items():
                    if key in loaded_settings:
                        if isinstance(default_value, dict):
                            # Merge dictionaries deeply (1 level for simplicity here)
                            config[key] = default_value.copy()
                            config[key].update(loaded_settings[key])
                            # Deeper merge for widgets
                            if key == "widgets":
                                for widget_key, widget_default in default_value.items():
                                     if widget_key in loaded_settings[key] and isinstance(widget_default, dict):
                                         config[key][widget_key] = widget_default.copy()
                                         config[key][widget_key].update(loaded_settings[key][widget_key])
                        else:
                            config[key] = loaded_settings[key]
                    else:
                         # Key from default not found in loaded, keep default
                         config[key] = default_value

                # Ensure auth structure exists if loading older config
                if 'auth' not in config:
                    config['auth'] = DEFAULT_CONFIG['auth'].copy()
                    needs_resave = True # Need to save the added auth section

                # If loading an old config with plain password, hash it (migration step)
                if 'password' in config['auth'] and 'password_hash' not in config['auth']:
                     print("Hashing plain text password found in config...")
                     config['auth']['password_hash'] = generate_password_hash(config['auth']['password'])
                     del config['auth']['password'] # Remove plain text version
                     needs_resave = True # Config changed, needs saving

                # Also remove plain password if hash already exists (cleanup)
                elif 'password' in config['auth'] and 'password_hash' in config['auth']:
                    print("Removing redundant plain text password from config...")
                    del config['auth']['password']
                    needs_resave = True # Config changed, needs saving

                if needs_resave:
                    save_config(config) # Save updated config immediately after loading/migration

                print("Configuration loaded from file.")
                return config
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {CONFIG_FILE}. Using default configuration.")
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading config file: {e}. Using default configuration.")
            return DEFAULT_CONFIG.copy()
    else:
        print("Config file not found. Saving default configuration.")
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

def save_config(config_data):
    """Saves the configuration dictionary to config.json."""
    # --- CLEANUP: Ensure plain password is removed if hash exists ---
    if 'auth' in config_data and 'password_hash' in config_data['auth'] and 'password' in config_data['auth']:
        print("Removing plain text password before saving.")
        del config_data['auth']['password']
    # --- END CLEANUP ---

    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = THUMBNAIL_FOLDER
app.config['SHOWGO_CONFIG'] = load_config()
app.secret_key = 'dev-secret-key' # Change in production!

# --- Authentication Setup ---
# Explicitly set a realm name
auth = HTTPBasicAuth(realm="ShowGo Configuration Access")

@auth.verify_password
def verify_password(username, password):
    """Checks username/password against the loaded configuration."""
    # --- DEBUG PRINT ---
    # print(f"--- verify_password called with username: {username} ---") # Keep commented unless debugging
    # --- END DEBUG PRINT ---

    config_auth = app.config['SHOWGO_CONFIG'].get('auth', {})
    stored_username = config_auth.get('username')
    stored_password_hash = config_auth.get('password_hash')

    if username == stored_username and stored_password_hash:
        # Use check_password_hash to compare provided password with stored hash
        result = check_password_hash(stored_password_hash, password)
        # print(f"--- Password check result: {result} ---") # Keep commented unless debugging
        return result

    # print(f"--- Password check failed (username mismatch or no hash) ---") # Keep commented unless debugging
    return False

# --- Routes ---

@app.route('/')
def slideshow_viewer():
    """
    Route for the main slideshow display page. (No auth required)
    """
    current_config = app.config['SHOWGO_CONFIG']
    # print("Accessing slideshow viewer route") # Keep commented unless debugging
    # return render_template('slideshow.html', config=current_config)
    return f"<h1>Slideshow Viewer</h1><pre>{json.dumps(current_config, indent=2)}</pre>"

@app.route('/config')
@auth.login_required # Apply the authentication decorator
def config_page():
    """
    Route for the configuration interface. Requires authentication.
    """
    current_config = app.config['SHOWGO_CONFIG']
    # print(f"Accessing config page route (User: {auth.current_user()})") # Keep commented unless debugging
    # return render_template('config.html', config=current_config)
    return f"<h1>Configuration Page (Authenticated as: {auth.current_user()})</h1><pre>{json.dumps(current_config, indent=2)}</pre>"

# --- Running the App ---
if __name__ == '__main__':
    print(f"Base directory: {BASE_DIR}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Config folder: {CONFIG_FOLDER}")
    app.run(debug=True, host='0.0.0.0')
