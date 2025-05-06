# showgo/utils.py
# Helper functions for the ShowGo application

import os
import shutil
import traceback
from datetime import datetime, timezone
from flask import current_app, flash
from sqlalchemy.exc import ProgrammingError, OperationalError

# Import db and models carefully to avoid circular imports if needed later
# If utils need db directly, import from extensions
from .extensions import db
from .models import Setting, ImageFile
from .config import DEFAULT_SETTINGS_DB # Import defaults for fallback

# --- Pillow Check ---
try:
    from PIL import Image, UnidentifiedImageError
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # Define dummy classes if Pillow is not available
    class UnidentifiedImageError(Exception): pass
    class Image: pass

# --- File Handling Helpers (Moved from old app.py) ---

def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    # Access configuration via current_app proxy
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set())
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_thumbnail(source_path, dest_path, size):
    """Generates a thumbnail for an image using Pillow."""
    # Check if Pillow is available (using the flag set at import time)
    if not PIL_AVAILABLE:
        print("WARNING: Pillow not available, cannot generate thumbnail.")
        return False, None
    try:
        if not os.path.isfile(source_path):
            print(f"ERROR: Source file not found for thumbnail generation: {source_path}")
            return False, None
        with Image.open(source_path) as img:
            # Handle animated GIFs (use first frame)
            if img.format == 'GIF' and getattr(img, 'is_animated', False):
                img.seek(0)
                # Convert to RGB if it's not already (needed for saving as PNG/JPG)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            img.thumbnail(size) # Use the size tuple directly
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            # Get format from config via current_app
            thumb_format = current_app.config.get('THUMBNAIL_FORMAT', 'PNG')
            img.save(dest_path, thumb_format)
            print(f"Generated thumbnail: {dest_path}")
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
# --- End File Handling Helpers ---


# --- Database Initialization/Self-Healing Function ---
def initialize_database():
    """Creates tables if they don't exist and ensures default settings are populated."""
    print("Attempting database initialization/check...")
    try:
        # Ensure operations are within an app context
        with current_app.app_context():
            db.create_all()
            print("Tables checked/created.")

            settings_added = 0
            for key, default_value in DEFAULT_SETTINGS_DB.items():
                # Use session.get for primary key lookup
                setting = db.session.get(Setting, key)
                if setting is None:
                    print(f"Adding missing default setting: {key}")
                    setting = Setting(key=key, value=default_value)
                    db.session.add(setting)
                    settings_added += 1

            if settings_added > 0:
                db.session.commit()
                print(f"Added {settings_added} default settings.")
                # Invalidate cache implicitly by not having one at this level
            else:
                print("All default settings present.")

            # Cleanup old API key setting
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
        # Attempt rollback even on connection error, might fail but worth trying
        try:
            db.session.rollback()
        except Exception as rb_err:
            print(f"Error during rollback after OperationalError: {rb_err}")
        return False # Indicate failure
    except Exception as e:
        print(f"ERROR during database initialization: {e}")
        traceback.print_exc()
        db.session.rollback()
        return False # Indicate failure

# --- Configuration Loading/Saving ---
def get_setting(key, default=None):
    """Gets a setting value from database, with fallback and recovery."""
    # No persistent cache used here; relies on DB query or defaults
    try:
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            return setting.value
    except ProgrammingError as e:
        # Check for MySQL specific error code for "Table doesn't exist"
        is_missing_table_err = e.orig and getattr(e.orig, 'errno', None) == 1146
        if is_missing_table_err:
            print(f"WARNING: Settings table missing when getting '{key}'. Attempting recovery.")
            # Attempt recovery (which includes db.create_all)
            if initialize_database():
                print(f"Recovery successful. Retrying get_setting for '{key}'.")
                try:
                    # Retry the query once after initialization
                    setting = Setting.query.filter_by(key=key).first()
                    if setting:
                        return setting.value
                except Exception as retry_e:
                    # Log error during retry
                    print(f"ERROR getting setting '{key}' after recovery attempt: {retry_e}")
            else:
                # Log recovery failure
                print(f"ERROR: Database recovery failed during get_setting for '{key}'.")
        else:
             # Log other ProgrammingErrors
             print(f"Unhandled ProgrammingError getting setting '{key}': {e}")
             traceback.print_exc()
    except Exception as e:
        # Log any other unexpected exceptions during query
        print(f"Error getting setting '{key}': {e}")
        traceback.print_exc() # Log full traceback for unexpected errors

    # Fallback logic: use provided default, then config default
    # Use current_app safely
    app_config = current_app.config if current_app else {}
    default_settings = app_config.get('DEFAULT_SETTINGS_DB', {})
    return default if default is not None else default_settings.get(key)


def load_settings_from_db():
    """Loads all settings, attempting recovery if table is missing. Returns merged dict."""
    settings_dict = {}
    defaults = current_app.config.get('DEFAULT_SETTINGS_DB', {})
    try:
        settings = Setting.query.all()
        db_settings_dict = {setting.key: setting.value for setting in settings}
        # Start with defaults, then update with values from DB
        settings_dict = defaults.copy()
        settings_dict.update(db_settings_dict)
        print("Settings loaded from database and merged with defaults.")
    except ProgrammingError as e:
        is_missing_table_err = e.orig and getattr(e.orig, 'errno', None) == 1146
        if is_missing_table_err:
            print("WARNING: Settings table missing. Attempting recovery.")
            if initialize_database():
                print("Recovery successful. Retrying settings load.")
                try:
                    # Retry the load after recovery
                    settings = Setting.query.all()
                    db_settings_dict = {setting.key: setting.value for setting in settings}
                    settings_dict = defaults.copy()
                    settings_dict.update(db_settings_dict)
                    print("Settings loaded successfully after recovery.")
                except Exception as retry_e:
                    print(f"ERROR loading settings after recovery attempt: {retry_e}")
                    traceback.print_exc()
                    print("Falling back to default settings after failed recovery.")
                    settings_dict = defaults.copy()
            else:
                print("ERROR: Database recovery failed. Falling back to default settings.")
                settings_dict = defaults.copy()
        else:
             print(f"Unhandled ProgrammingError loading settings: {e}")
             traceback.print_exc()
             print("Falling back to default settings due to unhandled DB error.")
             settings_dict = defaults.copy()
    except Exception as e:
        print(f"Error loading settings from DB: {e}. Falling back to defaults.")
        traceback.print_exc()
        settings_dict = defaults.copy()
    return settings_dict

def save_setting(key, value):
    """Saves a setting, attempting recovery if table is missing."""
    try:
        setting = db.session.get(Setting, key)
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        # Invalidate cache implicitly or explicitly if needed
        return True
    except ProgrammingError as e:
         is_missing_table_err = e.orig and getattr(e.orig, 'errno', None) == 1146
         if is_missing_table_err:
            print(f"WARNING: Settings table missing when saving '{key}'. Attempting recovery.")
            if initialize_database():
                 print(f"Recovery successful. Retrying save_setting for '{key}'.")
                 try:
                     # Re-fetch or re-add after potential rollback in initialize_database
                     setting = db.session.get(Setting, key)
                     if setting:
                         setting.value = value
                     else:
                         setting = Setting(key=key, value=value)
                         db.session.add(setting)
                     db.session.commit()
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
     try:
          latest_setting = Setting.query.order_by(Setting.last_updated.desc()).first()
          if latest_setting and isinstance(latest_setting.last_updated, datetime):
              return latest_setting.last_updated.timestamp()
          else:
              return 0.0
     except ProgrammingError as e:
          is_missing_table_err = e.orig and getattr(e.orig, 'errno', None) == 1146
          if is_missing_table_err:
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
                     return None # Indicate error after failed retry
            else:
                print("ERROR: Database recovery failed during timestamp check.")
                return None # Indicate error
          else:
              print(f"Unhandled ProgrammingError getting timestamp: {e}")
              traceback.print_exc()
              return None
     except Exception as e:
          print(f"ERROR in get_config_timestamp_from_db: {e}")
          traceback.print_exc()
          return None # Indicate error

# --- Filesystem Validation Helpers ---
def get_database_images():
    """Gets all ImageFile records, attempting recovery if table is missing."""
    try:
        all_images = ImageFile.query.all()
        db_uuids = {img.uuid_filename for img in all_images}
        return all_images, db_uuids
    except ProgrammingError as e:
         is_missing_table_err = e.orig and getattr(e.orig, 'errno', None) == 1146
         if is_missing_table_err:
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
        if not img.check_files_exist():
            img.missing_info = []
            if not os.path.isfile(img.get_upload_path()):
                img.missing_info.append(f"Original ({img.get_disk_filename()})")
            if not os.path.isfile(img.get_thumbnail_path()):
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
    upload_folder = current_app.config['UPLOAD_FOLDER']
    thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
    thumbnail_ext = current_app.config['THUMBNAIL_EXT']

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
                    elif item_name.lower() not in ['.ds_store', 'thumbs.db']:
                        unexpected_files.append(item_info)
        except OSError as e:
            print(f"Error reading directory {upload_folder}: {e}")
    else:
         print(f"Warning: Upload directory not found: {upload_folder}")

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
                    is_expected_ext = ext.lower() == thumbnail_ext
                    if is_uuid_format and is_expected_ext:
                        if uuid_part not in db_uuids:
                             if not any(f['name'] == item_name and f['folder'] == 'thumbnails' for f in orphaned_uuid_files):
                                 orphaned_uuid_files.append(item_info)
                    elif item_name.lower() not in ['.ds_store', 'thumbs.db']:
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
    upload_folder = current_app.config['UPLOAD_FOLDER']
    thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']

    for item in items_to_delete:
        base_path = upload_folder if item.get('folder') == 'uploads' else thumbnail_folder
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
                print(f"Warning: Unexpected item not found for deletion: {item['folder']}/{item['name']}")
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

