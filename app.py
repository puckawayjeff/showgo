# app.py
# Main application file for the ShowGo Slideshow Kiosk

import os
import json
import random
import requests
import feedparser
import traceback
from datetime import datetime

# Make sure jsonify is imported
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
try:
    from PIL import Image, UnidentifiedImageError
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: Pillow library not found. Thumbnail generation will be skipped.")
    class UnidentifiedImageError(Exception): pass
    class Image: pass

from werkzeug.exceptions import RequestEntityTooLarge

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, 'thumbnails')
CONFIG_FOLDER = os.path.join(BASE_DIR, 'config')
CONFIG_FILE = os.path.join(CONFIG_FOLDER, 'config.json')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
THUMBNAIL_SIZE = (150, 150)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)
os.makedirs(os.path.join(STATIC_FOLDER, 'images'), exist_ok=True)

# --- Default Configuration ---
DEFAULT_CONFIG = {
    "slideshow": {
        "duration_seconds": 10,
        "transition_effect": "fade",
        "image_order": "sequential",
        "image_scaling": "cover"
    },
    "watermark": {
        "enabled": False,
        "text": "© Your Company",
        "position": "bottom-right"
    },
    "widgets": {
        "time": {"enabled": True},
        "weather": {"enabled": True, "location": "Oshkosh, WI", "api_key": ""},
        "rss": {"enabled": False, "feed_url": "https://feeds.bbci.co.uk/news/rss.xml?edition=us"}
    },
    "auth": {
         "username": "admin",
         "password_hash": generate_password_hash("showgo"),
         "password_changed": False
    },
    "burn_in_prevention": {
        "enabled": False,
        "elements": ["watermark"],
        "interval_seconds": 15,
        "strength_pixels": 3
    }
}

# --- Helper Functions ---
# (Keep allowed_file and generate_thumbnail functions the same)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_thumbnail(source_path, dest_path, size):
    if not PIL_AVAILABLE: return False, None
    try:
        if not os.path.isfile(source_path): return False, None
        with Image.open(source_path) as img:
            if img.format == 'GIF' and getattr(img, 'is_animated', False):
                 img.seek(0); img = img.convert('RGB')
            img.thumbnail(size)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            thumb_format = 'PNG'
            base, _ = os.path.splitext(dest_path)
            dest_path_with_ext = f"{base}.{thumb_format.lower()}"
            img.save(dest_path_with_ext, thumb_format)
            return True, dest_path_with_ext
    except UnidentifiedImageError: print(f"ERROR: Cannot identify image file {source_path}"); return False, None
    except FileNotFoundError: print(f"ERROR: File not found during Image.open: {source_path}"); return False, None
    except Exception as e: print(f"ERROR: Generic exception generating thumbnail for {os.path.basename(source_path)}: {e}"); traceback.print_exc(); return False, None

# --- Configuration Loading/Saving Functions ---
# (Keep load_config and save_config functions the same as v14)
def load_config():
    """Loads configuration from config.json, falling back to defaults."""
    needs_resave = False
    config_to_use = DEFAULT_CONFIG.copy() # Start with current defaults

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded_settings = json.load(f)

            # --- Migration from old watermark 'move' setting ---
            if 'watermark' in loaded_settings and isinstance(loaded_settings['watermark'], dict) \
               and 'move' in loaded_settings['watermark']:
                print("Migrating old watermark 'move' setting...")
                if loaded_settings['watermark']['move']:
                    if 'burn_in_prevention' not in loaded_settings: loaded_settings['burn_in_prevention'] = {}
                    loaded_settings['burn_in_prevention']['enabled'] = True
                    current_elements = loaded_settings['burn_in_prevention'].get('elements', [])
                    if 'watermark' not in current_elements: current_elements.append('watermark')
                    loaded_settings['burn_in_prevention']['elements'] = current_elements
                del loaded_settings['watermark']['move']
                needs_resave = True
            # ---------------------------------------------------

            # Merge loaded settings onto defaults (handles missing keys in loaded file)
            for key, default_value in DEFAULT_CONFIG.items():
                if key in loaded_settings:
                    if isinstance(default_value, dict):
                        if key not in config_to_use: config_to_use[key] = default_value.copy()
                        if isinstance(loaded_settings.get(key), dict):
                             config_to_use[key].update(loaded_settings[key])
                    else:
                        config_to_use[key] = loaded_settings[key]

            # --- Specific checks/migrations after merge ---
            if 'auth' not in config_to_use or not isinstance(config_to_use.get('auth'), dict):
                config_to_use['auth'] = DEFAULT_CONFIG['auth'].copy()
                needs_resave = True
            elif 'password_changed' not in config_to_use['auth']:
                config_to_use['auth']['password_changed'] = config_to_use['auth'].get('password_hash') != DEFAULT_CONFIG['auth']['password_hash']
                print(f"Added missing 'password_changed' flag, set to: {config_to_use['auth']['password_changed']}")
                needs_resave = True
            if 'burn_in_prevention' not in config_to_use:
                config_to_use['burn_in_prevention'] = DEFAULT_CONFIG['burn_in_prevention'].copy()
            if 'slideshow' not in config_to_use:
                 config_to_use['slideshow'] = DEFAULT_CONFIG['slideshow'].copy()
                 needs_resave = True
            elif 'image_scaling' not in config_to_use.get('slideshow', {}):
                 config_to_use.setdefault('slideshow', {})['image_scaling'] = DEFAULT_CONFIG['slideshow']['image_scaling']
                 print("Added missing 'image_scaling' setting to slideshow config.")
                 needs_resave = True
            if 'password' in config_to_use.get('auth', {}):
                 if 'password_hash' not in config_to_use['auth']:
                     config_to_use['auth']['password_hash'] = generate_password_hash(config_to_use['auth']['password'])
                 del config_to_use['auth']['password']
                 needs_resave = True

            if needs_resave: save_config(config_to_use)
            return config_to_use

        except json.JSONDecodeError: print(f"Error decoding JSON from {CONFIG_FILE}. Using default."); return DEFAULT_CONFIG.copy()
        except Exception as e: print(f"Error loading config file: {e}. Using default."); traceback.print_exc(); return DEFAULT_CONFIG.copy()
    else:
        print("Config file not found. Saving default configuration.")
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

def save_config(config_data):
    """Saves the configuration dictionary to config.json."""
    if 'auth' in config_data and 'password_hash' in config_data['auth'] and 'password' in config_data['auth']:
        del config_data['auth']['password']
    if 'watermark' in config_data and 'move' in config_data['watermark']:
         del config_data['watermark']['move']
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e: print(f"Error saving configuration: {e}"); return False

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = THUMBNAIL_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024
app.config['SHOWGO_CONFIG'] = load_config()
app.secret_key = 'dev-secret-key'

# --- Authentication Setup ---
auth = HTTPBasicAuth(realm="ShowGo Configuration Access")

@auth.verify_password
def verify_password(username, password):
    config_auth = app.config['SHOWGO_CONFIG'].get('auth', {})
    stored_username = config_auth.get('username')
    stored_password_hash = config_auth.get('password_hash')
    if username == stored_username and stored_password_hash:
        return check_password_hash(stored_password_hash, password)
    return False

# --- Routes ---
@app.route('/')
def slideshow_viewer():
    """
    Route for the main slideshow display page. Fetches data and renders template.
    """
    current_config = app.config['SHOWGO_CONFIG']
    image_files = []; weather_data = None; rss_data = None
    config_timestamp = 0 # Default timestamp

    # --- Get Config Timestamp ---
    try:
        if os.path.exists(CONFIG_FILE):
            config_timestamp = os.path.getmtime(CONFIG_FILE)
    except Exception as e:
        print(f"Error getting config timestamp: {e}")

    # --- Get Image List ---
    try:
        if os.path.isdir(app.config['UPLOAD_FOLDER']):
            image_files = [ f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f)) and allowed_file(f) ]
            if current_config.get('slideshow', {}).get('image_order') == 'random': random.shuffle(image_files)
            else: image_files.sort()
        else: print(f"Upload directory not found: {app.config['UPLOAD_FOLDER']}")
    except Exception as e: print(f"Error listing upload directory for slideshow: {e}")

    # --- Fetch Weather Data ---
    weather_config = current_config.get('widgets', {}).get('weather', {})
    if weather_config.get('enabled') and weather_config.get('api_key') and weather_config.get('location'):
        try:
            api_key = weather_config['api_key']; location = weather_config['location']
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=imperial"
            response = requests.get(weather_url, timeout=10); response.raise_for_status()
            weather_data = response.json()
        except requests.exceptions.RequestException as e: print(f"Error fetching weather data: {e}")
        except Exception as e: print(f"Unexpected error processing weather data: {e}"); traceback.print_exc()

    # --- Fetch RSS Data ---
    rss_config = current_config.get('widgets', {}).get('rss', {})
    if rss_config.get('enabled') and rss_config.get('feed_url'):
        try:
            feed_url = rss_config['feed_url']; headers = {'User-Agent': 'ShowGo/1.0'}
            rss_data_raw = feedparser.parse(feed_url, agent=headers['User-Agent'])
            if rss_data_raw.bozo and isinstance(rss_data_raw.bozo_exception, Exception): print(f"Error parsing RSS feed (bozo): {rss_data_raw.bozo_exception}"); rss_data = None
            elif rss_data_raw.entries: rss_data = [{'title': entry.get('title', 'No Title'), 'link': entry.get('link', '#')} for entry in rss_data_raw.entries[:5]]
            else: print(f"RSS feed parsed but no entries found: {feed_url}"); rss_data = []
        except Exception as e: print(f"Error fetching or parsing RSS feed: {e}"); traceback.print_exc()

    # Pass all data, including the initial timestamp, to the template
    return render_template('slideshow.html',
                           config=current_config,
                           images=image_files,
                           weather=weather_data,
                           rss_headlines=rss_data,
                           initial_config_timestamp=config_timestamp) # Pass timestamp


@app.route('/uploads/<path:filename>')
def serve_uploaded_image(filename):
    # (Keep serve_uploaded_image route the same)
    requested_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    safe_path = os.path.abspath(requested_path)
    if not safe_path.startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])): return "Forbidden", 403
    if not os.path.isfile(safe_path): return "Not Found", 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- NEW API Route for Checking Config ---
@app.route('/api/config/check')
def check_config():
    """Returns the last modification timestamp of the config file."""
    try:
        if os.path.exists(CONFIG_FILE):
            timestamp = os.path.getmtime(CONFIG_FILE)
            return jsonify({'timestamp': timestamp})
        else:
            # Config file missing, return 0 or error? Return 0 for simplicity.
            return jsonify({'timestamp': 0})
    except Exception as e:
        print(f"Error checking config timestamp: {e}")
        # Return an error status or a default timestamp
        return jsonify({'error': 'Could not check config status', 'timestamp': 0}), 500

# --- Config page route ---
@app.route('/config')
@auth.login_required
def config_page():
    # (Keep config_page logic the same)
    current_config = app.config['SHOWGO_CONFIG']
    auth_config = current_config.get('auth', {})
    if not auth_config.get('password_changed', False):
        flash("Please change the default password.", "warning")
        return render_template('config.html', config=current_config, images=[], force_password_change=True)
    image_files = []
    try:
        if os.path.isdir(app.config['UPLOAD_FOLDER']):
            image_files = sorted([ f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f)) and allowed_file(f) ])
        else: print(f"Upload directory not found: {app.config['UPLOAD_FOLDER']}")
    except Exception as e: print(f"Error listing upload directory: {e}"); flash("Error retrieving image list.", "error")
    return render_template('config.html', config=current_config, images=image_files, force_password_change=False)

# --- Upload, Thumbnail, Delete, Save Settings routes ---
# (Keep upload_image, serve_thumbnail, delete_images, save_settings routes the same)
@app.route('/config/upload', methods=['POST'])
@auth.login_required
def upload_image():
    if not PIL_AVAILABLE: flash("Image processing library (Pillow) not installed. Cannot generate thumbnails.", "error")
    if 'image_files' not in request.files: flash('No file part in the request.', 'error'); return redirect(url_for('config_page'))
    files = request.files.getlist('image_files'); uploaded_count = 0; error_count = 0; thumb_error_count = 0
    if not files or files[0].filename == '': flash('No selected file.', 'error'); return redirect(url_for('config_page'))
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename); save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            base, ext = os.path.splitext(filename); counter = 1
            while os.path.exists(save_path): filename = f"{base}_{counter}{ext}"; save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename); counter += 1
            try:
                file.save(save_path); uploaded_count += 1
                if PIL_AVAILABLE:
                    thumb_filename = filename; thumb_dest_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumb_filename)
                    success, actual_thumb_path = generate_thumbnail(save_path, thumb_dest_path, THUMBNAIL_SIZE)
                    if not success: thumb_error_count += 1
            except RequestEntityTooLarge as e: print(f"Upload failed for {filename}: {e}"); flash('Upload failed: Total size of files exceeds the server limit.', 'error'); return redirect(url_for('config_page'))
            except Exception as e: print(f"Error saving file {filename}: {e}"); flash(f'Error saving file {filename}.', 'error'); error_count += 1
        elif file and file.filename != '': flash(f'File type not allowed for {secure_filename(file.filename)}.', 'error'); error_count += 1
    if uploaded_count > 0:
        success_msg = f'Successfully uploaded {uploaded_count} image(s).'
        if thumb_error_count > 0: success_msg += f' Failed to generate thumbnails for {thumb_error_count} image(s).'; flash(success_msg, 'warning')
        else: flash(success_msg, 'success')
    if error_count > 0: flash(f'Failed to upload {error_count} file(s) or invalid type.', 'error')
    return redirect(url_for('config_page'))

@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    requested_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)
    safe_path = os.path.abspath(requested_path)
    if not safe_path.startswith(os.path.abspath(app.config['THUMBNAIL_FOLDER'])): return "Forbidden", 403
    if not os.path.isfile(safe_path):
         placeholder = os.path.join(STATIC_FOLDER, 'images', 'placeholder_thumb.png')
         if os.path.isfile(placeholder): return send_from_directory(os.path.join(STATIC_FOLDER, 'images'), 'placeholder_thumb.png')
         else: return "Not Found", 404
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename)

@app.route('/config/delete', methods=['POST'])
@auth.login_required
def delete_images():
    images_to_delete = request.form.getlist('selected_images')
    if not images_to_delete: flash("No images selected for deletion.", "warning"); return redirect(url_for('config_page'))
    deleted_count = 0; error_count = 0
    for filename in images_to_delete:
        safe_filename = secure_filename(filename)
        if safe_filename != filename: print(f"Warning: Filename '{filename}' sanitized to '{safe_filename}' during deletion check. Skipping."); error_count += 1; continue
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        thumb_base, _ = os.path.splitext(safe_filename); thumb_filename_png = f"{thumb_base}.png"
        thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumb_filename_png)
        original_deleted = False
        try:
            if os.path.isfile(original_path): os.remove(original_path); original_deleted = True
            else: print(f"Original file not found for deletion: {original_path}")
            if os.path.isfile(thumbnail_path): os.remove(thumbnail_path)
            else: print(f"Thumbnail file not found for deletion: {thumbnail_path}")
            if original_deleted: deleted_count += 1
        except OSError as e: print(f"Error deleting file {safe_filename}: {e}"); error_count += 1
    if deleted_count > 0: flash(f"Successfully deleted {deleted_count} image(s).", "success")
    if error_count > 0: flash(f"Error occurred while deleting {error_count} file(s). Check logs.", "error")
    return redirect(url_for('config_page'))

@app.route('/config/save', methods=['POST'])
@auth.login_required
def save_settings():
    try:
        current_config = app.config['SHOWGO_CONFIG']
        auth_config = current_config.get('auth', {})
        if not auth_config.get('password_changed', False):
             flash("Cannot save settings until default password is changed.", "error")
             return redirect(url_for('config_page'))
        if 'slideshow' not in current_config: current_config['slideshow'] = DEFAULT_CONFIG['slideshow'].copy()
        current_config['slideshow']['duration_seconds'] = int(request.form.get('duration_seconds', 10))
        current_config['slideshow']['transition_effect'] = request.form.get('transition_effect', 'fade')
        current_config['slideshow']['image_order'] = request.form.get('image_order', 'sequential')
        current_config['slideshow']['image_scaling'] = request.form.get('image_scaling', 'cover')
        if 'watermark' not in current_config: current_config['watermark'] = DEFAULT_CONFIG['watermark'].copy()
        current_config['watermark']['enabled'] = 'watermark_enabled' in request.form
        current_config['watermark']['text'] = request.form.get('watermark_text', '')
        current_config['watermark']['position'] = request.form.get('watermark_position', 'bottom-right')
        if 'widgets' not in current_config: current_config['widgets'] = DEFAULT_CONFIG['widgets'].copy()
        if 'time' not in current_config['widgets']: current_config['widgets']['time'] = DEFAULT_CONFIG['widgets']['time'].copy()
        current_config['widgets']['time']['enabled'] = 'time_widget_enabled' in request.form
        if 'weather' not in current_config['widgets']: current_config['widgets']['weather'] = DEFAULT_CONFIG['widgets']['weather'].copy()
        current_config['widgets']['weather']['enabled'] = 'weather_widget_enabled' in request.form
        current_config['widgets']['weather']['location'] = request.form.get('weather_location', '')
        current_config['widgets']['weather']['api_key'] = request.form.get('weather_api_key', '')
        if 'rss' not in current_config['widgets']: current_config['widgets']['rss'] = DEFAULT_CONFIG['widgets']['rss'].copy()
        current_config['widgets']['rss']['enabled'] = 'rss_widget_enabled' in request.form
        current_config['widgets']['rss']['feed_url'] = request.form.get('rss_feed_url', '')
        if 'burn_in_prevention' not in current_config: current_config['burn_in_prevention'] = DEFAULT_CONFIG['burn_in_prevention'].copy()
        current_config['burn_in_prevention']['enabled'] = 'burn_in_prevention_enabled' in request.form
        current_config['burn_in_prevention']['elements'] = request.form.getlist('burn_in_elements')
        current_config['burn_in_prevention']['interval_seconds'] = int(request.form.get('burn_in_interval_seconds', 15))
        current_config['burn_in_prevention']['strength_pixels'] = int(request.form.get('burn_in_strength_pixels', 3))
        if save_config(current_config):
            app.config['SHOWGO_CONFIG'] = current_config
            flash("Configuration saved successfully!", "success")
        else: flash("Error saving configuration.", "error")
    except ValueError: flash("Invalid input value provided (e.g., duration, interval, strength must be numbers).", "error")
    except Exception as e: print(f"Error processing save settings request: {e}"); traceback.print_exc(); flash("An unexpected error occurred while saving settings.", "error")
    return redirect(url_for('config_page'))

# --- Password Change Routes ---
# (Keep change_password and update_password routes the same)
@app.route('/config/change-password', methods=['POST'])
@auth.login_required
def change_password():
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    if app.config['SHOWGO_CONFIG'].get('auth', {}).get('password_changed', False): flash("Password has already been changed.", "error"); return redirect(url_for('config_page'))
    if not new_password or not confirm_password: flash("New password fields are required.", "error"); return redirect(url_for('config_page'))
    if new_password != confirm_password: flash("New password and confirmation do not match.", "error"); return redirect(url_for('config_page'))
    if new_password == "showgo": flash("New password cannot be the default password.", "error"); return redirect(url_for('config_page'))
    try:
        current_config = app.config['SHOWGO_CONFIG']
        new_hash = generate_password_hash(new_password)
        current_config['auth']['password_hash'] = new_hash
        current_config['auth']['password_changed'] = True
        if save_config(current_config):
            app.config['SHOWGO_CONFIG'] = current_config
            flash("Password changed successfully! You can now configure ShowGo.", "success")
            return redirect(url_for('config_page'))
        else: flash("Error saving new password configuration.", "error"); return redirect(url_for('config_page'))
    except Exception as e: print(f"Error processing initial password change: {e}"); traceback.print_exc(); flash("An unexpected error occurred while changing the password.", "error"); return redirect(url_for('config_page'))

@app.route('/config/update-password', methods=['POST'])
@auth.login_required
def update_password():
    current_password = request.form.get('update_current_password')
    new_password = request.form.get('update_new_password')
    confirm_password = request.form.get('update_confirm_password')
    if not app.config['SHOWGO_CONFIG'].get('auth', {}).get('password_changed', False): flash("Cannot update password until default is changed.", "error"); return redirect(url_for('config_page'))
    if not current_password or not new_password or not confirm_password: flash("All fields are required to update password.", "error"); return redirect(url_for('config_page'))
    if new_password != confirm_password: flash("New password and confirmation do not match.", "error"); return redirect(url_for('config_page'))
    config_auth = app.config['SHOWGO_CONFIG'].get('auth', {}); stored_password_hash = config_auth.get('password_hash')
    if not stored_password_hash or not check_password_hash(stored_password_hash, current_password): flash("Incorrect current password.", "error"); return redirect(url_for('config_page'))
    if check_password_hash(stored_password_hash, new_password): flash("New password cannot be the same as the current password.", "error"); return redirect(url_for('config_page'))
    try:
        current_config = app.config['SHOWGO_CONFIG']
        new_hash = generate_password_hash(new_password)
        current_config['auth']['password_hash'] = new_hash
        if save_config(current_config):
            app.config['SHOWGO_CONFIG'] = current_config
            flash("Password updated successfully!", "success")
        else: flash("Error saving updated password configuration.", "error")
    except Exception as e: print(f"Error processing password update: {e}"); traceback.print_exc(); flash("An unexpected error occurred while updating the password.", "error")
    return redirect(url_for('config_page'))

# --- Running the App ---
if __name__ == '__main__':
    if not PIL_AVAILABLE: print("-------------------------------------------------------\nWARNING: Pillow library not installed. Thumbnails disabled.\n         pip install Pillow\n-------------------------------------------------------")
    print(f"Base directory: {BASE_DIR}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Thumbnail folder: {THUMBNAIL_FOLDER}")
    print(f"Config folder: {CONFIG_FOLDER}")
    app.run(debug=True, host='0.0.0.0')

