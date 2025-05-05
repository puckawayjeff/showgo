# app.py
# Main application file for the ShowGo Slideshow Kiosk

import os
import json
import random
import requests
import feedparser
import traceback
import uuid # Import UUID library
import shutil # Import for directory removal
from datetime import datetime, timezone
from dotenv import load_dotenv
from functools import wraps # For custom decorator

# Import specific exceptions if needed for more granular error handling later
from werkzeug.exceptions import NotFound, InternalServerError, RequestEntityTooLarge
# Import SQLAlchemy exceptions for specific error handling
from sqlalchemy.exc import ProgrammingError, OperationalError

# Added Response, make_response
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_from_directory, jsonify, Response, make_response)
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
try:
    from PIL import Image, UnidentifiedImageError
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: Pillow library not found. Thumbnail generation will be skipped.")
    # Define dummy classes if Pillow is not available
    class UnidentifiedImageError(Exception): pass
    class Image: pass


# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, 'thumbnails')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
THUMBNAIL_SIZE = (150, 150)
THUMBNAIL_FORMAT = 'PNG' # Store thumbnails as PNG
THUMBNAIL_EXT = f".{THUMBNAIL_FORMAT.lower()}" # Expected thumbnail extension

# Load environment variables from .env file
load_dotenv()

# --- Flask App Initialization ---
app = Flask(__name__)

# Configure database connection (using environment variables)
db_user = os.environ.get('MYSQL_USER')
db_password = os.environ.get('MYSQL_PASSWORD')
db_host = os.environ.get('MYSQL_HOST')
db_name = os.environ.get('MYSQL_DB')

if not all([db_user, db_password, db_host, db_name]):
    raise ValueError("Database connection parameters missing in environment variables (MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB)")

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Other App Config ---
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = THUMBNAIL_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set for Flask application")

# Ensure necessary directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
os.makedirs(os.path.join(STATIC_FOLDER, 'images'), exist_ok=True)


# --- Database Models (Expanded Definition) ---
class Setting(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Setting {self.key}>'

class ImageFile(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    uuid_filename = db.Column(db.String(36), unique=True, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    extension = db.Column(db.String(10), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def get_disk_filename(self):
        return f"{self.uuid_filename}.{self.extension}"

    def get_thumbnail_filename(self):
        return f"{self.uuid_filename}{THUMBNAIL_EXT}"

    def get_upload_path(self):
        return os.path.join(app.config['UPLOAD_FOLDER'], self.get_disk_filename())

    def get_thumbnail_path(self):
        return os.path.join(app.config['THUMBNAIL_FOLDER'], self.get_thumbnail_filename())

    def check_files_exist(self):
        return os.path.isfile(self.get_upload_path()) and os.path.isfile(self.get_thumbnail_path())

    def __repr__(self):
        return f'<ImageFile {self.id}: {self.display_name} ({self.get_disk_filename()})>'
# --- END Database Models ---


# --- Default Configuration ---
DEFAULT_SETTINGS_DB = {
    "slideshow_duration_seconds": 10,
    "slideshow_transition_effect": "kenburns",
    "slideshow_image_order": "random",
    "slideshow_image_scaling": "cover",
    "watermark_enabled": False,
    "watermark_text": "ShowGo Slideshow",
    "watermark_position": "top-right",
    "widgets_time_enabled": True,
    "widgets_weather_enabled": True,
    "widgets_weather_location": "Oshkosh",
    "widgets_rss_enabled": False,
    "widgets_rss_feed_url": "https://feeds.bbci.co.uk/news/rss.xml?edition=us",
    "auth_username": "admin",
    "auth_password_hash": generate_password_hash("showgo"),
    "auth_password_changed": False,
    "burn_in_prevention_enabled": False,
    "burn_in_prevention_elements": ["watermark"],
    "burn_in_prevention_interval_seconds": 15,
    "burn_in_prevention_strength_pixels": 3
}

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_thumbnail(source_path, dest_path, size):
    """Generates a thumbnail for an image using Pillow."""
    if not PIL_AVAILABLE:
        return False, None
    try:
        if not os.path.isfile(source_path):
            return False, None
        with Image.open(source_path) as img:
            if img.format == 'GIF' and getattr(img, 'is_animated', False):
                img.seek(0)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            img.thumbnail(size)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            img.save(dest_path, THUMBNAIL_FORMAT)
            return True, dest_path
    except UnidentifiedImageError:
        print(f"ERROR: Cannot identify image file {source_path}")
        return False, None
    except FileNotFoundError:
        print(f"ERROR: File not found during Image.open: {source_path}")
        return False, None
    except Exception as e:
        print(f"ERROR: Generic exception generating thumbnail for {os.path.basename(source_path)}: {e}")
        traceback.print_exc()
        return False, None

# --- Database Initialization/Self-Healing Function ---
def initialize_database():
    """Creates tables if they don't exist and ensures default settings are populated."""
    print("Attempting database initialization/check...")
    try:
        db.create_all()
        print("Tables checked/created.")

        settings_added = 0
        for key, default_value in DEFAULT_SETTINGS_DB.items():
            setting = db.session.get(Setting, key)
            if setting is None:
                print(f"Adding missing default setting: {key}")
                setting = Setting(key=key, value=default_value)
                db.session.add(setting)
                settings_added += 1

        if settings_added > 0:
            db.session.commit()
            print(f"Added {settings_added} default settings.")
            global _settings_cache
            _settings_cache = None # Invalidate cache after adding defaults
        else:
            print("All default settings present.")

        old_api_key_setting = db.session.get(Setting, 'widgets_weather_api_key')
        if old_api_key_setting:
            print("Removing obsolete 'widgets_weather_api_key' setting...")
            db.session.delete(old_api_key_setting)
            db.session.commit()
            print("Obsolete setting removed.")

        return True # Indicate success

    except OperationalError as op_err:
        print(f"FATAL: Database connection error during initialization: {op_err}")
        traceback.print_exc()
        db.session.rollback()
        return False # Indicate failure
    except Exception as e:
        print(f"ERROR during database initialization: {e}")
        traceback.print_exc()
        db.session.rollback()
        return False # Indicate failure

# --- Configuration Loading/Saving ---
_settings_cache = None
_cache_timestamp = None

def get_setting(key, default=None):
    """Gets a setting value from cache or database."""
    global _settings_cache
    if _settings_cache and key in _settings_cache:
        return _settings_cache[key]
    try:
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            return setting.value
    except ProgrammingError as e:
        if e.orig and getattr(e.orig, 'errno', None) == 1146:
            print(f"WARNING: Settings table missing when getting '{key}'. Attempting recovery.")
            if initialize_database():
                print(f"Recovery successful. Retrying get_setting for '{key}'.")
                try:
                    setting = Setting.query.filter_by(key=key).first()
                    if setting:
                        return setting.value
                except Exception as retry_e:
                    print(f"ERROR getting setting '{key}' after recovery attempt: {retry_e}")
            else:
                print(f"ERROR: Database recovery failed during get_setting for '{key}'.")
        else:
             print(f"Unhandled ProgrammingError getting setting '{key}': {e}")
             traceback.print_exc()
    except Exception as e:
        print(f"Error getting setting '{key}': {e}")
    return default if default is not None else DEFAULT_SETTINGS_DB.get(key)


def load_settings_from_db():
    """Loads all settings, attempting recovery if table is missing."""
    global _settings_cache
    settings_dict = {}
    try:
        settings = Setting.query.all()
        db_settings_dict = {setting.key: setting.value for setting in settings}
        settings_dict = DEFAULT_SETTINGS_DB.copy()
        settings_dict.update(db_settings_dict)
        _settings_cache = settings_dict
        print("Settings loaded from database and merged with defaults.")
    except ProgrammingError as e:
        if e.orig and getattr(e.orig, 'errno', None) == 1146:
            print("WARNING: Settings table missing. Attempting recovery.")
            if initialize_database():
                print("Recovery successful. Retrying settings load.")
                try:
                    settings = Setting.query.all()
                    db_settings_dict = {setting.key: setting.value for setting in settings}
                    settings_dict = DEFAULT_SETTINGS_DB.copy()
                    settings_dict.update(db_settings_dict)
                    _settings_cache = settings_dict
                    print("Settings loaded successfully after recovery.")
                except Exception as retry_e:
                    print(f"ERROR loading settings after recovery attempt: {retry_e}")
                    traceback.print_exc()
                    print("Falling back to default settings after failed recovery.")
                    settings_dict = DEFAULT_SETTINGS_DB.copy()
                    _settings_cache = settings_dict
            else:
                print("ERROR: Database recovery failed. Falling back to default settings.")
                settings_dict = DEFAULT_SETTINGS_DB.copy()
                _settings_cache = settings_dict
        else:
             print(f"Unhandled ProgrammingError loading settings: {e}")
             traceback.print_exc()
             print("Falling back to default settings due to unhandled DB error.")
             settings_dict = DEFAULT_SETTINGS_DB.copy()
             _settings_cache = settings_dict
    except Exception as e:
        print(f"Error loading settings from DB: {e}. Falling back to defaults.")
        traceback.print_exc()
        settings_dict = DEFAULT_SETTINGS_DB.copy()
        _settings_cache = settings_dict
    return settings_dict

def save_setting(key, value):
    """Saves a setting, attempting recovery if table is missing."""
    global _settings_cache
    try:
        setting = db.session.get(Setting, key)
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        if _settings_cache is not None:
            _settings_cache[key] = value
        return True
    except ProgrammingError as e:
         if e.orig and getattr(e.orig, 'errno', None) == 1146:
            print(f"WARNING: Settings table missing when saving '{key}'. Attempting recovery.")
            if initialize_database():
                 print(f"Recovery successful. Retrying save_setting for '{key}'.")
                 try:
                     setting = db.session.get(Setting, key)
                     if setting:
                         setting.value = value
                     else:
                         setting = Setting(key=key, value=value)
                         db.session.add(setting)
                     db.session.commit()
                     if _settings_cache is not None:
                         _settings_cache[key] = value
                     return True
                 except Exception as retry_e:
                     db.session.rollback()
                     print(f"ERROR saving setting '{key}' after recovery attempt: {retry_e}")
                     traceback.print_exc()
                     return False
            else:
                print(f"ERROR: Database recovery failed during save_setting for '{key}'.")
                db.session.rollback()
                return False
         else:
             db.session.rollback()
             print(f"Unhandled ProgrammingError saving setting '{key}': {e}")
             traceback.print_exc()
             return False
    except Exception as e:
        db.session.rollback()
        print(f"Error saving setting '{key}': {e}")
        traceback.print_exc()
        return False

def get_config_timestamp_from_db():
     """Gets the timestamp, attempting recovery if table missing."""
     # print("--- get_config_timestamp_from_db called ---")
     try:
          latest_setting = Setting.query.order_by(Setting.last_updated.desc()).first()
          if latest_setting:
               if isinstance(latest_setting.last_updated, datetime):
                    timestamp = latest_setting.last_updated.timestamp()
                    return timestamp
               else:
                    return 0.0
          else:
               return 0.0
     except ProgrammingError as e:
          if e.orig and getattr(e.orig, 'errno', None) == 1146:
            print("WARNING: Settings table missing for timestamp check. Attempting recovery.")
            if initialize_database():
                 print("Recovery successful. Retrying timestamp check.")
                 try:
                     latest_setting = Setting.query.order_by(Setting.last_updated.desc()).first()
                     if latest_setting and isinstance(latest_setting.last_updated, datetime):
                         return latest_setting.last_updated.timestamp()
                     else:
                         return 0.0
                 except Exception as retry_e:
                     print(f"ERROR getting timestamp after recovery: {retry_e}")
                     return None
            else:
                print("ERROR: Database recovery failed during timestamp check.")
                return None
          else:
              print(f"Unhandled ProgrammingError getting timestamp: {e}")
              traceback.print_exc()
              return None
     except Exception as e:
          print(f"ERROR in get_config_timestamp_from_db: {e}")
          traceback.print_exc()
          return None

# --- Filesystem Validation Helpers ---
def get_database_images():
    """Gets all ImageFile records, attempting recovery if table is missing."""
    try:
        all_images = ImageFile.query.all()
        db_uuids = {img.uuid_filename for img in all_images}
        return all_images, db_uuids
    except ProgrammingError as e:
         if e.orig and getattr(e.orig, 'errno', None) == 1146:
            print("WARNING: Images table missing. Attempting recovery.")
            if initialize_database():
                 print("Recovery successful. Retrying image query.")
                 try:
                     all_images = ImageFile.query.all()
                     db_uuids = {img.uuid_filename for img in all_images}
                     return all_images, db_uuids
                 except Exception as retry_e:
                     print(f"ERROR querying images after recovery: {retry_e}")
                     traceback.print_exc()
                     return [], set()
            else:
                print("ERROR: Database recovery failed during image query.")
                return [], set()
         else:
              print(f"Unhandled ProgrammingError querying images: {e}")
              traceback.print_exc()
              return [], set()
    except Exception as e:
        print(f"Error querying database images: {e}")
        traceback.print_exc()
        return [], set()

def find_missing_files(db_images):
    """Checks database images against the filesystem and returns those with missing files."""
    missing = []
    for img in db_images:
        original_exists = os.path.isfile(img.get_upload_path())
        thumbnail_exists = os.path.isfile(img.get_thumbnail_path())
        if not original_exists or not thumbnail_exists:
            img.missing_info = []
            if not original_exists:
                img.missing_info.append(f"Original ({img.get_disk_filename()})")
            if not thumbnail_exists:
                 img.missing_info.append(f"Thumbnail ({img.get_thumbnail_filename()})")
            missing.append(img)
    return missing

def find_unexpected_items(db_uuids):
    """
    Scans uploads and thumbnails folders for items not corresponding to DB entries.
    Returns lists of orphaned UUID files, other unexpected files, and unexpected directories.
    """
    orphaned_uuid_files = []
    unexpected_files = []
    unexpected_dirs = []
    upload_folder = app.config['UPLOAD_FOLDER']
    if os.path.isdir(upload_folder):
        try:
            for item_name in os.listdir(upload_folder):
                item_path = os.path.join(upload_folder, item_name)
                item_info = {'folder': 'uploads', 'name': item_name}
                if os.path.isdir(item_path):
                    unexpected_dirs.append(item_info)
                elif os.path.isfile(item_path):
                    uuid_part, _ = os.path.splitext(item_name)
                    is_uuid_format = len(uuid_part) == 32 and all(c in '0123456789abcdef' for c in uuid_part)
                    if is_uuid_format:
                        if uuid_part not in db_uuids:
                            orphaned_uuid_files.append(item_info)
                    else:
                        if item_name.lower() not in ['.ds_store', 'thumbs.db']:
                            unexpected_files.append(item_info)
        except OSError as e:
            print(f"Error reading directory {upload_folder}: {e}")
    else:
         print(f"Warning: Upload directory not found: {upload_folder}")

    thumbnail_folder = app.config['THUMBNAIL_FOLDER']
    if os.path.isdir(thumbnail_folder):
        try:
            for item_name in os.listdir(thumbnail_folder):
                item_path = os.path.join(thumbnail_folder, item_name)
                item_info = {'folder': 'thumbnails', 'name': item_name}
                if os.path.isdir(item_path):
                    if not any(d['name'] == item_name and d['folder'] == 'thumbnails' for d in unexpected_dirs):
                        unexpected_dirs.append(item_info)
                elif os.path.isfile(item_path):
                    uuid_part, ext = os.path.splitext(item_name)
                    is_uuid_format = len(uuid_part) == 32 and all(c in '0123456789abcdef' for c in uuid_part)
                    is_expected_ext = ext.lower() == THUMBNAIL_EXT
                    if is_uuid_format and is_expected_ext:
                        if uuid_part not in db_uuids:
                             if not any(f['name'] == item_name and f['folder'] == 'thumbnails' for f in orphaned_uuid_files):
                                 orphaned_uuid_files.append(item_info)
                    else:
                         if item_name.lower() not in ['.ds_store', 'thumbs.db']:
                              if not any(f['name'] == item_name and f['folder'] == 'thumbnails' for f in unexpected_files):
                                   unexpected_files.append(item_info)
        except OSError as e:
            print(f"Error reading directory {thumbnail_folder}: {e}")
    else:
        print(f"Warning: Thumbnail directory not found: {thumbnail_folder}")
    return orphaned_uuid_files, unexpected_files, unexpected_dirs

def cleanup_unexpected_items(items_to_delete):
    """Deletes files or directories based on a list of item dictionaries."""
    deleted_files = 0
    deleted_dirs = 0
    error_count = 0
    for item in items_to_delete:
        folder_key = 'UPLOAD_FOLDER' if item.get('folder') == 'uploads' else 'THUMBNAIL_FOLDER'
        base_path = app.config.get(folder_key)
        if not base_path:
            print(f"Error: Invalid folder type '{item.get('folder')}' for item '{item.get('name')}'")
            error_count += 1
            continue
        item_path = os.path.join(base_path, item.get('name', ''))
        item_path = os.path.abspath(item_path)
        if not item_path.startswith(os.path.abspath(base_path)):
             print(f"Error: Attempted deletion outside designated folder: {item_path}")
             error_count += 1
             continue
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
                print(f"Deleted unexpected file: {item['folder']}/{item['name']}")
                deleted_files += 1
            elif os.path.isdir(item_path):
                print(f"Deleting unexpected directory: {item['folder']}/{item['name']}")
                shutil.rmtree(item_path)
                print(f"Deleted unexpected directory: {item['folder']}/{item['name']}")
                deleted_dirs += 1
            else:
                print(f"Warning: Unexpected item not found for deletion (already removed?): {item['folder']}/{item['name']}")
        except OSError as e:
            print(f"Error deleting unexpected item {item['folder']}/{item['name']}: {e}")
            error_count += 1
        except Exception as e:
            print(f"Unexpected error deleting item {item['folder']}/{item['name']}: {e}")
            traceback.print_exc()
            error_count += 1
    return deleted_files, deleted_dirs, error_count

def remove_missing_db_entries(missing_image_ids):
    """Deletes ImageFile records from the database based on a list of IDs."""
    deleted_count = 0
    error_count = 0
    if not missing_image_ids:
        return 0, 0

    for image_id_str in missing_image_ids:
        try:
            image_id = int(image_id_str)
            image_record = db.session.get(ImageFile, image_id)
            if image_record:
                print(f"Removing DB record for missing image ID {image_id} ('{image_record.display_name}')")
                db.session.delete(image_record)
                deleted_count += 1
            else:
                print(f"DB record for missing image ID {image_id} not found (already deleted?).")
        except ValueError:
            print(f"Invalid image ID received for deletion: {image_id_str}")
            error_count += 1
        except Exception as e:
            print(f"Error deleting DB record for missing image ID {image_id_str}: {e}")
            traceback.print_exc()
            error_count += 1
            db.session.rollback()

    if error_count == 0:
        try:
            db.session.commit()
        except Exception as e:
            print(f"Error committing deletions of missing DB entries: {e}")
            traceback.print_exc()
            flash("Database error occurred while committing deletions.", "error")
            db.session.rollback()
            return 0, deleted_count + error_count
    elif deleted_count > 0:
        try:
            db.session.commit()
            print(f"Committed deletion of {deleted_count} missing DB entries despite {error_count} errors.")
        except Exception as e:
             print(f"Error committing partial deletions of missing DB entries: {e}")
             traceback.print_exc()
             flash("Database error occurred while committing partial deletions.", "error")
             db.session.rollback()
             return 0, deleted_count + error_count

    return deleted_count, error_count
# --- END Validation Helpers ---


# --- Load initial settings into app context ---
# Wrap the initial load in a try-except to catch startup DB errors
try:
    with app.app_context():
        initialize_database()
        app.config['SHOWGO_CONFIG_DB'] = load_settings_from_db()
except OperationalError as op_err:
    print(f"FATAL: Database connection failed on startup: {op_err}")
    print("!!! WARNING: Running with default settings only due to DB connection failure !!!")
    app.config['SHOWGO_CONFIG_DB'] = DEFAULT_SETTINGS_DB.copy()
except Exception as startup_err:
     print(f"FATAL: Unexpected error during startup database initialization: {startup_err}")
     print("!!! WARNING: Running with default settings only due to unexpected startup error !!!")
     app.config['SHOWGO_CONFIG_DB'] = DEFAULT_SETTINGS_DB.copy()


# --- Authentication Setup ---
auth = HTTPBasicAuth(realm="ShowGo Configuration Access")
@auth.verify_password
def verify_password(username, password):
    """Verify user credentials against stored settings."""
    with app.app_context():
        stored_username = get_setting('auth_username', 'admin')
        stored_password_hash = get_setting('auth_password_hash')

    if username == stored_username and stored_password_hash:
        try:
            is_valid = check_password_hash(stored_password_hash, password)
            return is_valid
        except Exception as e:
            print(f"ERROR: Exception during check_password_hash: {e}")
            traceback.print_exc()
            return False
    else:
        return False

# --- Decorator to check for initial password change ---
def check_password_changed(f):
    """Decorator to ensure the default password has been changed."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        with app.app_context():
            password_changed = get_setting('auth_password_changed', False)
        if not password_changed:
            flash("Please change the default password before accessing configuration.", "warning")
            return redirect(url_for('config_set_initial_password'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def slideshow_viewer():
    """ Route for the main slideshow display page. """
    with app.app_context():
        current_config_dict = _settings_cache if _settings_cache is not None else load_settings_from_db()
        if current_config_dict is None:
             print("CRITICAL ERROR: Could not load settings for slideshow viewer.")
             raise InternalServerError("Failed to load application configuration.")

        config_timestamp = get_config_timestamp_from_db()
        current_config = {
            "slideshow": { "duration_seconds": current_config_dict.get("slideshow_duration_seconds", 10), "transition_effect": current_config_dict.get("slideshow_transition_effect", "fade"), "image_order": current_config_dict.get("slideshow_image_order", "sequential"), "image_scaling": current_config_dict.get("slideshow_image_scaling", "cover") },
            "watermark": { "enabled": current_config_dict.get("watermark_enabled", False), "text": current_config_dict.get("watermark_text", ""), "position": current_config_dict.get("watermark_position", "bottom-right") },
            "widgets": { "time": {"enabled": current_config_dict.get("widgets_time_enabled", True)}, "weather": { "enabled": current_config_dict.get("widgets_weather_enabled", True), "location": current_config_dict.get("widgets_weather_location", "") }, "rss": { "enabled": current_config_dict.get("widgets_rss_enabled", False), "feed_url": current_config_dict.get("widgets_rss_feed_url", "") } },
            "burn_in_prevention": { "enabled": current_config_dict.get("burn_in_prevention_enabled", False), "elements": current_config_dict.get("burn_in_prevention_elements", ["watermark"]), "interval_seconds": current_config_dict.get("burn_in_prevention_interval_seconds", 15), "strength_pixels": current_config_dict.get("burn_in_prevention_strength_pixels", 3) },
        }
        all_db_images, _ = get_database_images()
        valid_images = []
        for img in all_db_images:
            if img.check_files_exist():
                valid_images.append(img.get_disk_filename())
            else:
                print(f"Slideshow: Skipping image ID {img.id} ('{img.display_name}') due to missing file(s).")
        if not valid_images:
            print("Warning: No valid images found for slideshow.")
        if current_config['slideshow']['image_order'] == 'random':
            random.shuffle(valid_images)

        weather_data = None
        weather_error = None
        rss_data = None
        rss_error = None
        weather_config = current_config.get('widgets', {}).get('weather', {})
        openweathermap_api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        if weather_config.get('enabled'):
            if weather_config.get('location') and openweathermap_api_key:
                try:
                    location = weather_config['location']
                    weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={openweathermap_api_key}&units=imperial"
                    response = requests.get(weather_url, timeout=10)
                    response.raise_for_status()
                    weather_data = response.json()
                    print(f"Successfully fetched weather for {location}")
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching weather data: {e}")
                    weather_error = f"Network/API Error: {e}"
                except Exception as e:
                    print(f"Unexpected error processing weather data: {e}")
                    traceback.print_exc()
                    weather_error = f"Processing Error: {e}"
            elif not openweathermap_api_key:
                 print("Weather widget enabled, but OPENWEATHERMAP_API_KEY environment variable is not set.")
                 weather_error = "API Key Missing"
            elif not weather_config.get('location'):
                 print("Weather widget enabled, but no location is set.")
                 weather_error = "Location Missing"

        rss_config = current_config.get('widgets', {}).get('rss', {})
        if rss_config.get('enabled'):
            if rss_config.get('feed_url'):
                try:
                    feed_url = rss_config['feed_url']
                    headers = {'User-Agent': 'ShowGo/1.0'}
                    socket_timeout = 10
                    rss_data_raw = feedparser.parse(feed_url, agent=headers['User-Agent'], socket_timeout=socket_timeout)
                    if rss_data_raw.bozo:
                        bozo_exception_msg = str(rss_data_raw.bozo_exception) if hasattr(rss_data_raw, 'bozo_exception') else "Unknown parsing issue"
                        print(f"Error parsing RSS feed (bozo): {feed_url} - {bozo_exception_msg}")
                        rss_error = f"Feed Parsing Error: {bozo_exception_msg}"
                    elif rss_data_raw.entries:
                        rss_data = [{'title': entry.get('title', 'No Title'), 'link': entry.get('link', '#')} for entry in rss_data_raw.entries[:15]]
                        print(f"Successfully parsed {len(rss_data)} RSS headlines from {feed_url}")
                    else:
                        print(f"RSS feed parsed but no entries found: {feed_url}")
                        rss_error = "Feed Empty"
                except Exception as e:
                    print(f"Error fetching or parsing RSS feed: {e}")
                    traceback.print_exc()
                    rss_error = f"Fetch/Parse Error: {e}"
            else:
                print("RSS widget enabled, but no feed URL is set.")
                rss_error = "Feed URL Missing"
        return render_template('slideshow.html', config=current_config, images=valid_images, weather=weather_data, weather_error=weather_error, rss_headlines=rss_data, rss_error=rss_error, initial_config_timestamp=config_timestamp)

@app.route('/uploads/<path:filename>')
def serve_uploaded_image(filename):
    requested_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    safe_path = os.path.abspath(requested_path)
    if not safe_path.startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
        return "Forbidden", 403
    if not os.path.isfile(safe_path):
        return "Not Found", 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serves thumbnail images, providing a placeholder if not found."""
    print(f"--- serve_thumbnail called for: {filename} ---")
    thumbnail_folder = app.config['THUMBNAIL_FOLDER']
    requested_path = os.path.join(thumbnail_folder, filename)
    safe_path = os.path.abspath(requested_path)

    if not safe_path.startswith(os.path.abspath(thumbnail_folder)):
        print(f"Forbidden access attempt for thumbnail: {filename}")
        return "Forbidden", 403

    if not os.path.isfile(safe_path):
        print(f"Thumbnail not found: {filename}. Serving placeholder.")
        placeholder = os.path.join(STATIC_FOLDER, 'images', 'placeholder_thumb.png')
        if os.path.isfile(placeholder):
            return send_from_directory(os.path.join(STATIC_FOLDER, 'images'), 'placeholder_thumb.png')
        else:
            print("Placeholder thumbnail image not found!")
            return "Not Found", 404

    return send_from_directory(thumbnail_folder, filename)

@app.route('/api/config/check')
def check_config():
    """API endpoint for the client to check for configuration updates."""
    timestamp = get_config_timestamp_from_db()
    if timestamp is None:
         print("Error: check_config failed because get_config_timestamp_from_db returned None.")
         return jsonify({'error': 'Could not retrieve configuration status from server.', 'timestamp': 0}), 500
    else:
         print(f"API check_config returning timestamp: {timestamp}")
         return jsonify({'timestamp': timestamp})

# --- Configuration Routes Refactor ---
@app.route('/config')
@auth.login_required
def config_redirect():
    """Redirects /config to the default general settings page."""
    return redirect(url_for('config_general'))

@app.route('/config/set-initial-password', methods=['GET', 'POST'])
@auth.login_required
def config_set_initial_password():
    """Handles the initial setting of the administrator password."""
    with app.app_context():
        if get_setting('auth_password_changed', False):
            flash("Password has already been set.", "info")
            return redirect(url_for('config_general'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not new_password or not confirm_password:
            flash("New password fields are required.", "error")
            return redirect(url_for('config_set_initial_password'))
        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "error")
            return redirect(url_for('config_set_initial_password'))
        if new_password == "showgo":
            flash("New password cannot be the default password.", "error")
            return redirect(url_for('config_set_initial_password'))
        try:
            new_hash = generate_password_hash(new_password)
            saved_hash = save_setting('auth_password_hash', new_hash)
            saved_flag = save_setting('auth_password_changed', True)
            if saved_hash and saved_flag:
                flash("Password set successfully! You can now configure ShowGo.", "success")
                return redirect(url_for('config_general'))
            else:
                flash("Error saving new password configuration.", "error")
        except Exception as e:
            print(f"Error processing initial password change: {e}")
            traceback.print_exc()
            flash("An unexpected error occurred while changing the password.", "error")
        return redirect(url_for('config_set_initial_password'))

    username = get_setting('auth_username', 'admin')
    return render_template('config_initial_password.html', username=username)

@app.route('/config/general', methods=['GET', 'POST'])
@auth.login_required
@check_password_changed
def config_general():
    """Displays and handles saving of general slideshow/widget/display settings."""
    if request.method == 'POST':
        settings_saved = True
        try:
            allowed_transitions = ['fade', 'slide', 'kenburns']
            transition = request.form.get('transition_effect', 'fade')
            if transition not in allowed_transitions:
                flash(f"Invalid transition effect '{transition}'. Defaulting to 'fade'.", "warning")
                transition = 'fade'
            settings_saved &= save_setting('slideshow_transition_effect', transition)
            settings_saved &= save_setting('slideshow_duration_seconds', int(request.form.get('duration_seconds', 10)))
            settings_saved &= save_setting('slideshow_image_order', request.form.get('image_order', 'sequential'))
            settings_saved &= save_setting('slideshow_image_scaling', request.form.get('image_scaling', 'cover'))
            settings_saved &= save_setting('watermark_enabled', 'watermark_enabled' in request.form)
            settings_saved &= save_setting('watermark_text', request.form.get('watermark_text', ''))
            settings_saved &= save_setting('watermark_position', request.form.get('watermark_position', 'bottom-right'))
            settings_saved &= save_setting('widgets_time_enabled', 'time_widget_enabled' in request.form)
            settings_saved &= save_setting('widgets_weather_enabled', 'weather_widget_enabled' in request.form)
            settings_saved &= save_setting('widgets_weather_location', request.form.get('weather_location', ''))
            settings_saved &= save_setting('widgets_rss_enabled', 'rss_widget_enabled' in request.form)
            settings_saved &= save_setting('widgets_rss_feed_url', request.form.get('rss_feed_url', ''))
            settings_saved &= save_setting('burn_in_prevention_enabled', 'burn_in_prevention_enabled' in request.form)
            settings_saved &= save_setting('burn_in_prevention_elements', request.form.getlist('burn_in_elements'))
            settings_saved &= save_setting('burn_in_prevention_interval_seconds', int(request.form.get('burn_in_interval_seconds', 15)))
            settings_saved &= save_setting('burn_in_prevention_strength_pixels', int(request.form.get('burn_in_strength_pixels', 3)))
            if settings_saved:
                flash("Configuration saved successfully!", "success")
            else:
                flash("An error occurred while saving some settings. Check logs.", "error")
        except ValueError:
            flash("Invalid input value provided (e.g., duration, interval, strength must be numbers).", "error")
        except Exception as e:
            print(f"Error processing save settings request: {e}")
            traceback.print_exc()
            flash("An unexpected error occurred while saving settings.", "error")
        return redirect(url_for('config_general'))

    with app.app_context():
        current_config_dict = _settings_cache if _settings_cache is not None else load_settings_from_db()
        if current_config_dict is None:
            raise InternalServerError("Failed to load application configuration.")
        current_config = {
             "slideshow": { "duration_seconds": current_config_dict.get("slideshow_duration_seconds", 10), "transition_effect": current_config_dict.get("slideshow_transition_effect", "fade"), "image_order": current_config_dict.get("slideshow_image_order", "sequential"), "image_scaling": current_config_dict.get("slideshow_image_scaling", "cover") },
             "watermark": { "enabled": current_config_dict.get("watermark_enabled", False), "text": current_config_dict.get("watermark_text", ""), "position": current_config_dict.get("watermark_position", "bottom-right") },
             "widgets": { "time": {"enabled": current_config_dict.get("widgets_time_enabled", True)}, "weather": { "enabled": current_config_dict.get("widgets_weather_enabled", True), "location": current_config_dict.get("widgets_weather_location", "") }, "rss": { "enabled": current_config_dict.get("widgets_rss_enabled", False), "feed_url": current_config_dict.get("widgets_rss_feed_url", "") } },
             "burn_in_prevention": { "enabled": current_config_dict.get("burn_in_prevention_enabled", False), "elements": current_config_dict.get("burn_in_prevention_elements", ["watermark"]), "interval_seconds": current_config_dict.get("burn_in_prevention_interval_seconds", 15), "strength_pixels": current_config_dict.get("burn_in_prevention_strength_pixels", 3) },
        }
    return render_template('config_general.html', config=current_config, active_page='general')

@app.route('/config/images')
@auth.login_required
@check_password_changed
def config_images():
    """Displays image management interface and handles validation warnings."""
    with app.app_context():
        all_db_images, db_uuids = get_database_images()
        missing_db_entries = find_missing_files(all_db_images)
        orphaned_uuid_files, unexpected_files, unexpected_dirs = find_unexpected_items(db_uuids)
        displayable_images = [img for img in all_db_images if img not in missing_db_entries]
        displayable_images.sort(key=lambda img: img.uploaded_at, reverse=True)

    return render_template('config_images.html', images=displayable_images, missing_db_entries=missing_db_entries, orphaned_uuid_files=orphaned_uuid_files, unexpected_files=unexpected_files, unexpected_dirs=unexpected_dirs, active_page='images')

@app.route('/config/upload', methods=['POST'])
@auth.login_required
@check_password_changed
def upload_image():
    """Handles image uploads, saves with UUID, stores info in DB."""
    if not PIL_AVAILABLE:
        flash("Image processing library (Pillow) not installed. Cannot generate thumbnails.", "error")
    if 'image_files' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('config_images'))

    files = request.files.getlist('image_files')
    uploaded_count = 0
    error_count = 0
    thumb_error_count = 0
    if not files or files[0].filename == '':
        flash('No selected file.', 'error')
        return redirect(url_for('config_images'))

    for file in files:
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower()
            uuid_hex = uuid.uuid4().hex
            disk_filename = f"{uuid_hex}.{file_ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], disk_filename)
            try:
                file.save(save_path)
                thumb_disk_filename = f"{uuid_hex}{THUMBNAIL_EXT}"
                thumb_dest_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumb_disk_filename)
                thumb_success, _ = generate_thumbnail(save_path, thumb_dest_path, THUMBNAIL_SIZE)
                if not thumb_success:
                    thumb_error_count += 1
                    print(f"Warning: Failed to generate thumbnail for {original_filename}")
                display_name_default = os.path.splitext(original_filename)[0]
                new_image = ImageFile(uuid_filename=uuid_hex, original_filename=original_filename, display_name=display_name_default, extension=file_ext)
                db.session.add(new_image)
                db.session.commit()
                uploaded_count += 1
            except RequestEntityTooLarge as e:
                print(f"Upload failed for {original_filename}: {e}")
                flash('Upload failed: Total size exceeds limit.', 'error')
                db.session.rollback()
                return redirect(url_for('config_images'))
            except Exception as e:
                print(f"Error processing file {original_filename}: {e}")
                traceback.print_exc()
                flash(f'Error processing file {original_filename}.', 'error')
                error_count += 1
                db.session.rollback()
        elif file and file.filename != '':
            flash(f'File type not allowed for {secure_filename(file.filename)}.', 'error')
            error_count += 1

    if uploaded_count > 0:
        success_msg = f'Successfully processed {uploaded_count} image(s).'
        flash(success_msg, 'success')
    if thumb_error_count > 0:
        flash(f'Failed to generate thumbnails for {thumb_error_count} image(s). Check logs.', 'warning')
    if error_count > 0:
        flash(f'Failed to upload or process {error_count} file(s).', 'error')
    return redirect(url_for('config_images'))

@app.route('/config/delete', methods=['POST'])
@auth.login_required
@check_password_changed
def delete_images():
    """Handles deleting selected images from DB and disk."""
    image_ids_to_delete = request.form.getlist('selected_images')
    deleted_count = 0
    error_count = 0
    if not image_ids_to_delete:
        flash("No images selected for deletion.", "warning")
        return redirect(url_for('config_images'))

    for image_id in image_ids_to_delete:
        try:
            image_id_int = int(image_id)
            image_record = db.session.get(ImageFile, image_id_int)
            if image_record:
                disk_filename = image_record.get_disk_filename()
                thumbnail_filename = image_record.get_thumbnail_filename()
                original_path = os.path.join(app.config['UPLOAD_FOLDER'], disk_filename)
                thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumbnail_filename)
                try:
                    if os.path.isfile(original_path):
                        os.remove(original_path)
                    else:
                        print(f"Warning: Original file not found during deletion: {original_path}")
                    if os.path.isfile(thumbnail_path):
                        os.remove(thumbnail_path)
                    else:
                        print(f"Warning: Thumbnail file not found during deletion: {thumbnail_path}")
                except OSError as e:
                     print(f"Error deleting files for image ID {image_id}: {e}")
                     flash(f"Error deleting files for '{image_record.display_name}', removing DB record anyway.", "warning")

                db.session.delete(image_record)
                deleted_count += 1
            else:
                print(f"Image record not found in DB for ID: {image_id}")
                error_count += 1
        except ValueError:
             print(f"Invalid image ID received: {image_id}")
             error_count += 1
        except Exception as e:
             print(f"Error processing deletion for image ID {image_id}: {e}")
             traceback.print_exc()
             error_count += 1
             db.session.rollback()

    try:
        db.session.commit()
    except Exception as e:
         print(f"Error committing deletions to DB: {e}")
         traceback.print_exc()
         flash("Database error during deletion.", "error")
         db.session.rollback()
         deleted_count = 0
         error_count = len(image_ids_to_delete)

    if deleted_count > 0:
        flash(f"Successfully deleted {deleted_count} image(s).", "success")
    if error_count > 0:
        flash(f"Error occurred while deleting {error_count} image(s). Check logs.", "error")
    return redirect(url_for('config_images'))

# --- Cleanup Routes ---
@app.route('/config/cleanup/missing-db', methods=['POST'])
@auth.login_required
@check_password_changed
def cleanup_missing_db_route():
    """Removes database entries for images whose files are missing."""
    image_ids = request.form.getlist('missing_image_ids')
    if not image_ids:
        flash("No missing image entries selected for removal.", "warning")
        return redirect(url_for('config_images'))

    print(f"Attempting to remove DB entries for missing image IDs: {image_ids}")
    deleted_count, error_count = remove_missing_db_entries(image_ids)

    if error_count > 0:
        flash(f"Removed {deleted_count} missing database entries, but encountered errors with {error_count} entries. Check logs.", "error")
    elif deleted_count > 0:
        flash(f"Successfully removed {deleted_count} database entries for missing images.", "success")
    else:
        flash("No database entries were removed (perhaps they were already gone?).", "info")
    return redirect(url_for('config_images'))

@app.route('/config/cleanup/unexpected-items', methods=['POST'])
@auth.login_required
@check_password_changed
def cleanup_unexpected_items_route():
    """Finds and deletes unexpected files AND directories."""
    print("Starting unexpected items cleanup (including directories)...")
    items_to_delete = []
    with app.app_context():
        _, db_uuids = get_database_images()
        orphaned_uuid_files, unexpected_files, unexpected_dirs = find_unexpected_items(db_uuids)
        items_to_delete.extend(orphaned_uuid_files)
        items_to_delete.extend(unexpected_files)
        items_to_delete.extend(unexpected_dirs)

        if not items_to_delete:
             flash("No unexpected items found to clean up.", "info")
             return redirect(url_for('config_images'))

        print(f"Found {len(items_to_delete)} unexpected items (files and directories) to delete.")
        deleted_files, deleted_dirs, error_count = cleanup_unexpected_items(items_to_delete)

        deleted_items_msg = []
        if deleted_files > 0:
            deleted_items_msg.append(f"{deleted_files} file(s)")
        if deleted_dirs > 0:
            deleted_items_msg.append(f"{deleted_dirs} director(y/ies)")

        if error_count > 0:
            if deleted_items_msg:
                 flash(f"Deleted {' and '.join(deleted_items_msg)}, but encountered errors deleting {error_count} item(s). Check logs.", "error")
            else:
                 flash(f"Cleanup failed. Encountered errors deleting {error_count} item(s). Check logs.", "error")
        elif deleted_items_msg:
            flash(f"Successfully deleted {' and '.join(deleted_items_msg)}.", "success")
        else:
             flash("Cleanup finished, but no items were deleted (perhaps they were removed by another process?).", "warning")
    return redirect(url_for('config_images'))

# --- Password Update Route ---
@app.route('/config/update-password', methods=['POST'])
@auth.login_required
@check_password_changed
def update_password():
    """Handles updating the admin password via the modal."""
    redirect_url = url_for('config_general') # Default redirect
    current_password = request.form.get('update_current_password')
    new_password = request.form.get('update_new_password')
    confirm_password = request.form.get('update_confirm_password')
    if not current_password or not new_password or not confirm_password:
        flash("All fields are required to update password.", "error")
        return redirect(redirect_url)
    if new_password != confirm_password:
        flash("New password and confirmation do not match.", "error")
        return redirect(redirect_url)

    stored_password_hash = get_setting('auth_password_hash')
    if not stored_password_hash or not check_password_hash(stored_password_hash, current_password):
        flash("Incorrect current password.", "error")
        return redirect(redirect_url)
    if check_password_hash(stored_password_hash, new_password):
        flash("New password cannot be the same as the current password.", "error")
        return redirect(redirect_url)

    try:
        new_hash = generate_password_hash(new_password)
        if save_setting('auth_password_hash', new_hash):
            flash("Password updated successfully!", "success")
        else:
            flash("Error saving updated password configuration.", "error")
    except Exception as e:
        print(f"Error processing password update: {e}")
        traceback.print_exc()
        flash("An unexpected error occurred while updating the password.", "error")
    return redirect(redirect_url)

# --- Logout Route ---
@app.route('/logout')
def logout():
    """Logs the user out (by rendering a page, browser handles auth clearing)."""
    return render_template('logout.html')

# --- Custom Error Handlers ---
@app.errorhandler(404)
@app.errorhandler(NotFound)
def page_not_found(error):
    """Renders the custom 404 error page."""
    return render_template('404.html'), 404

@app.errorhandler(500)
@app.errorhandler(InternalServerError)
@app.errorhandler(Exception)
def internal_server_error(error):
    """Renders the custom 500 error page and logs the error."""
    original_exception = getattr(error, "original_exception", error)
    print(f"!!! 500 Error Encountered: {original_exception} !!!")
    traceback.print_exc()
    try:
        db.session.rollback()
        print("Database session rolled back due to 500 error.")
    except Exception as db_err:
        print(f"Error rolling back database session: {db_err}")
    return render_template('500.html'), 500

@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def request_entity_too_large(error):
    """Handles the 'Request Entity Too Large' error (file upload size)."""
    flash(f"Upload failed: File(s) exceed the maximum allowed size ({app.config['MAX_CONTENT_LENGTH'] // 1024 // 1024} MB).", "error")
    return redirect(url_for('config_images'))

# --- init-db command ---
@app.cli.command('init-db')
def init_db_command():
    """Initializes the database by calling the shared function."""
    with app.app_context():
        initialize_database()

# --- Running the App ---
if __name__ == '__main__':
    if not PIL_AVAILABLE:
        print("-------------------------------------------------------\nWARNING: Pillow library not installed. Thumbnails disabled.\n         pip install Pillow\n-------------------------------------------------------")
    print(f"Base directory: {BASE_DIR}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Thumbnail folder: {THUMBNAIL_FOLDER}")
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    if not os.environ.get('OPENWEATHERMAP_API_KEY'):
        print("------------------------------------------------------------------\nWARNING: OPENWEATHERMAP_API_KEY environment variable not set.\n         Weather widget will not function without it.\n         Add it to your .env file or environment.\n------------------------------------------------------------------")
    # Consider adding host='0.0.0.0' if running in Docker or needing external access
    app.run(debug=True, host='0.0.0.0')
