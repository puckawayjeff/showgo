# showgo/utils.py
# Helper functions for the ShowGo application

import os
import shutil
import traceback
import json # For parsing ffprobe output
import subprocess # For running ffmpeg/ffprobe
from datetime import datetime, timezone
from flask import current_app, flash
# Import specific exceptions for more targeted handling if needed
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError
from sqlalchemy import func # Import func for max()

# Import db and models carefully
from .extensions import db
from .models import Setting # Keep Setting import
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

# --- File Handling Helpers ---

def get_media_type(filename):
    """Determines if a file is an image or video based on its extension."""
    if not filename or '.' not in filename:
        return None
    ext = filename.rsplit('.', 1)[1].lower()
    # Use current_app safely within the function
    image_exts = current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', set()) if current_app else set()
    video_exts = current_app.config.get('ALLOWED_VIDEO_EXTENSIONS', set()) if current_app else set()
    if ext in image_exts:
        return 'image'
    elif ext in video_exts:
        return 'video'
    else:
        return None

def allowed_file(filename):
    """Checks if the filename has an allowed image or video extension."""
    # Use current_app safely within the function
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set()) if current_app else set()
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def _get_video_duration(source_path):
    """Uses ffprobe to get the duration of a video file in seconds."""
    command = [
        'ffprobe',
        '-v', 'quiet', # Suppress verbose output
        '-print_format', 'json', # Output format
        '-show_format', # Request format information (includes duration)
        source_path
    ]
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(process.stdout)
        # Extract duration safely
        duration = float(data['format']['duration'])
        return duration
    except FileNotFoundError:
        print("ERROR: ffprobe command not found. Ensure ffmpeg is installed and in PATH.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"ERROR: ffprobe failed for {os.path.basename(source_path)}: {e.stderr}")
        return None
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: Could not parse ffprobe output for {os.path.basename(source_path)}: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error getting video duration for {os.path.basename(source_path)}: {e}")
        traceback.print_exc()
        return None

def generate_thumbnail(source_path, dest_path, size, media_type='image'):
    """Generates a thumbnail for an image (Pillow) or video (ffmpeg)."""
    dest_dir = os.path.dirname(dest_path)
    os.makedirs(dest_dir, exist_ok=True) # Ensure destination directory exists

    if media_type == 'video':
        print(f"Attempting video thumbnail generation for: {os.path.basename(source_path)}")
        duration = _get_video_duration(source_path)
        if duration is None or duration <= 0:
            print(f"Could not get valid duration for {os.path.basename(source_path)}, skipping thumbnail.")
            return False, None

        seek_time = max(0.1, duration * 0.1)
        ffmpeg_command = [
            'ffmpeg', '-ss', str(seek_time), '-i', source_path,
            '-vframes', '1', '-vf', f'scale={size[0]}:-1',
            '-q:v', '3', '-y', dest_path
        ]
        try:
            print(f"Running ffmpeg command: {' '.join(ffmpeg_command)}")
            process = subprocess.run(ffmpeg_command, capture_output=True, text=True, check=True)
            print(f"Successfully generated video thumbnail: {dest_path}")
            return True, dest_path
        except FileNotFoundError:
            print("ERROR: ffmpeg command not found. Ensure ffmpeg is installed and in PATH.")
            return False, None
        except subprocess.CalledProcessError as e:
            print(f"ERROR: ffmpeg failed for {os.path.basename(source_path)}:")
            print(f"Stderr: {e.stderr}")
            # Attempt to delete potentially corrupted output file
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError:
                    pass # Ignore error during cleanup attempt
            return False, None
        except Exception as e:
             print(f"ERROR: Unexpected error generating video thumbnail for {os.path.basename(source_path)}: {e}")
             traceback.print_exc()
             return False, None

    elif media_type == 'image':
        if not PIL_AVAILABLE:
            print("WARNING: Pillow not available, cannot generate image thumbnail.")
            return False, None
        try:
            if not os.path.isfile(source_path):
                print(f"ERROR: Source image file not found: {source_path}")
                return False, None
            with Image.open(source_path) as img:
                if img.format == 'GIF' and getattr(img, 'is_animated', False):
                    img.seek(0)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                img.thumbnail(size)
                thumb_format = current_app.config.get('THUMBNAIL_FORMAT', 'PNG') if current_app else 'PNG'
                if thumb_format.upper() == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                     img = img.convert('RGB')
                img.save(dest_path, thumb_format)
                return True, dest_path
        except UnidentifiedImageError:
            print(f"ERROR: Cannot identify image file {source_path}")
            return False, None
        except FileNotFoundError:
            print(f"ERROR: File not found during Image.open: {source_path}")
            return False, None
        except Exception as e:
            print(f"ERROR: Generic exception generating image thumbnail: {e}")
            traceback.print_exc()
            return False, None
    else:
        print(f"ERROR: Unknown media type '{media_type}' for thumbnail generation.")
        return False, None
# --- End File Handling Helpers ---


# --- Database Initialization/Self-Healing Function ---
def initialize_database():
    """Creates tables if they don't exist and ensures default settings are populated."""
    print("Attempting database initialization/check...")
    try:
        if not current_app:
            print("ERROR: Cannot initialize database outside application context.")
            return False

        with current_app.app_context():
            # Create all tables defined in models (idempotent)
            # This is safe to run even if tables exist
            db.create_all()
            print("Tables checked/created.")

            # Populate default settings
            defaults = current_app.config.get('DEFAULT_SETTINGS_DB', DEFAULT_SETTINGS_DB)
            settings_merged = False
            for key, default_value in defaults.items():
                # Use merge for idempotency: adds if not exists, updates if exists (based on PK)
                setting = Setting(key=key, value=default_value)
                db.session.merge(setting)
                settings_merged = True # Mark that we attempted merges

            if settings_merged:
                try:
                    db.session.commit() # Commit all merges/adds at once
                    print("Default settings checked/merged.")
                except IntegrityError:
                    db.session.rollback()
                    print("Warning: Integrity error during default settings merge, rolled back.")
                except Exception as commit_err:
                     db.session.rollback()
                     print(f"ERROR committing default settings: {commit_err}")
                     traceback.print_exc()
                     return False # Fail initialization if defaults can't be saved

            # Cleanup old API key setting (still relevant)
            old_api_key_setting = db.session.get(Setting, 'widgets_weather_api_key')
            if old_api_key_setting:
                print("Removing obsolete 'widgets_weather_api_key' setting...")
                db.session.delete(old_api_key_setting)
                db.session.commit()
                print("Obsolete setting removed.")

            return True # Indicate success

    except OperationalError as op_err:
        print(f"FATAL: Database connection/operation error during init: {op_err}")
        traceback.print_exc()
        return False # Indicate failure

    except Exception as e:
        print(f"ERROR during DB init: {e}")
        traceback.print_exc()
        try:
            if db.session is not None:
                db.session.rollback()
        except Exception as rb_err:
            print(f"Rollback error after generic Exception: {rb_err}")
        return False # Indicate failure

# --- Configuration Loading/Saving ---
def get_setting(key, default=None):
    """Gets a setting value from database, with fallback and recovery."""
    try:
        if not current_app:
            return default
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            return setting.value
    except ProgrammingError as e:
        print(f"Database programming error getting setting '{key}': {e}. Attempting recovery.")
        if initialize_database():
            print(f"Recovery ok. Retrying get '{key}'.")
            try:
                setting = Setting.query.filter_by(key=key).first()
                return setting.value if setting else default
            except Exception as retry_e:
                print(f"ERROR getting '{key}' post-recovery: {retry_e}")
        else:
            print(f"ERROR: DB recovery failed getting '{key}'.")
    except OperationalError as op_e:
         print(f"Database operational error getting setting '{key}': {op_e}")
    except Exception as e:
        print(f"Error getting setting '{key}': {e}")
        traceback.print_exc()

    # Fallback logic
    app_config = current_app.config if current_app else {}
    default_settings = app_config.get('DEFAULT_SETTINGS_DB', DEFAULT_SETTINGS_DB)
    return default if default is not None else default_settings.get(key)

def load_settings_from_db():
    """Loads all settings, attempting recovery if table is missing. Returns merged dict."""
    defaults = current_app.config.get('DEFAULT_SETTINGS_DB', DEFAULT_SETTINGS_DB) if current_app else DEFAULT_SETTINGS_DB.copy()
    settings_dict = defaults.copy()
    if not current_app:
        return settings_dict

    try:
        settings = Setting.query.all()
        db_settings_dict = {setting.key: setting.value for setting in settings}
        settings_dict.update(db_settings_dict)
    except ProgrammingError as e:
        print(f"Database programming error loading settings: {e}. Attempting recovery.")
        if initialize_database():
            print("Recovery ok. Retrying settings load.")
            try:
                settings = Setting.query.all()
                db_settings_dict = {setting.key: setting.value for setting in settings}
                settings_dict = defaults.copy()
                settings_dict.update(db_settings_dict)
            except Exception as retry_e:
                print(f"ERROR loading settings post-recovery: {retry_e}")
                traceback.print_exc()
                print("Falling back to defaults.")
                settings_dict = defaults.copy()
        else:
            print("ERROR: DB recovery failed. Falling back to defaults.")
            settings_dict = defaults.copy()
    except OperationalError as op_e:
         print(f"Database operational error loading settings: {op_e}")
         print("Falling back to defaults.")
         settings_dict = defaults.copy()
    except Exception as e:
        print(f"Error loading settings from DB: {e}. Falling back to defaults.")
        traceback.print_exc()
        settings_dict = defaults.copy()
    return settings_dict

def save_setting(key, value):
    """Saves a setting, attempting recovery if table is missing."""
    if not current_app:
        print("ERROR: Cannot save setting without app context.")
        return False
    try:
        setting = db.session.get(Setting, key)
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return True
    except ProgrammingError as e:
         print(f"Database programming error saving setting '{key}': {e}. Attempting recovery.")
         db.session.rollback()
         if initialize_database():
             print(f"Recovery ok. Retrying save '{key}'.")
             try:
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
                 print(f"ERROR saving '{key}' post-recovery: {retry_e}")
                 traceback.print_exc()
                 return False
         else:
             print(f"ERROR: DB recovery failed saving '{key}'.")
             return False
    except OperationalError as op_e:
         db.session.rollback()
         print(f"Database operational error saving setting '{key}': {op_e}")
         return False
    except Exception as e:
        db.session.rollback()
        print(f"Error saving setting '{key}': {e}")
        traceback.print_exc()
        return False

def get_config_timestamp_from_db():
     """Gets the most recent timestamp reflecting changes to settings or media library."""
     if not current_app:
         print("ERROR: Cannot get timestamp without app context.")
         return None

     latest_setting_ts = 0.0
     media_changed_ts = 0.0

     try:
          latest_setting = Setting.query.order_by(Setting.last_updated.desc()).first()
          if latest_setting and isinstance(latest_setting.last_updated, datetime):
              latest_setting_ts = latest_setting.last_updated.timestamp()

          media_ts_value = get_setting('media_last_changed', 0.0)
          if isinstance(media_ts_value, (int, float)):
              media_changed_ts = float(media_ts_value)
          else:
              print(f"Warning: Invalid type for 'media_last_changed': {type(media_ts_value)}.")
              media_changed_ts = 0.0 # Default to 0 if type is wrong

          most_recent_ts = max(latest_setting_ts, media_changed_ts)
          return most_recent_ts

     except ProgrammingError as e:
          print(f"Database programming error getting timestamp: {e}. Attempting recovery.")
          if initialize_database():
              print("Recovery ok. Retrying timestamp check.")
              return get_config_timestamp_from_db() # Retry
          else:
              print("ERROR: DB recovery failed during timestamp check.")
              return None
     except OperationalError as op_e:
          print(f"Database operational error getting timestamp: {op_e}")
          return None
     except Exception as e:
          print(f"ERROR in get_config_timestamp_from_db: {e}")
          traceback.print_exc()
          return None

# --- Filesystem Validation Helpers ---
def get_database_media():
    """Gets all MediaFile records, attempting recovery if table is missing."""
    from .models import MediaFile # Import locally
    if not current_app:
        print("ERROR: Cannot get media without app context.")
        return [], set()
    try:
        all_media = MediaFile.query.all()
        db_uuids = {media.uuid_filename for media in all_media}
        return all_media, db_uuids
    except ProgrammingError as e:
         print(f"Database programming error getting media: {e}. Attempting recovery.")
         if initialize_database():
             print("Recovery ok. Retrying media query.")
             try:
                 all_media = MediaFile.query.all()
                 db_uuids = {media.uuid_filename for media in all_media}
                 return all_media, db_uuids
             except Exception as retry_e:
                 print(f"ERROR querying media post-recovery: {retry_e}")
                 traceback.print_exc()
                 return [], set()
         else:
             print("ERROR: DB recovery failed during media query.")
             return [], set()
    except OperationalError as op_e:
         print(f"Database operational error getting media: {op_e}")
         return [], set()
    except Exception as e:
        print(f"Error querying database media: {e}")
        traceback.print_exc()
        return [], set()

def find_missing_media_files(db_media):
    """Checks database media against the filesystem and returns those with missing primary files."""
    missing = []
    if not current_app:
        print("ERROR: Cannot check files without app context.")
        return missing
    for media in db_media:
        if not media.check_files_exist():
            media.missing_info = []
            if not os.path.isfile(media.get_upload_path()):
                media.missing_info.append(f"Original ({media.get_disk_filename()})")
            missing.append(media)
    return missing

def find_unexpected_items(db_uuids):
    """Scans uploads and thumbnails folders for items not corresponding to DB entries."""
    orphaned_uuid_files = []
    unexpected_files = []
    unexpected_dirs = []
    if not current_app:
        print("ERROR: Cannot find unexpected items without app context.")
        return [], [], []

    upload_folder = current_app.config['UPLOAD_FOLDER']
    thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
    thumbnail_ext = current_app.config['THUMBNAIL_EXT']
    allowed_media_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set())

    # Scan Uploads Folder
    if os.path.isdir(upload_folder):
        try:
            for item_name in os.listdir(upload_folder):
                item_path = os.path.join(upload_folder, item_name)
                item_info = {'folder': 'uploads', 'name': item_name}
                if os.path.isdir(item_path):
                    unexpected_dirs.append(item_info)
                elif os.path.isfile(item_path):
                    uuid_part, ext = os.path.splitext(item_name)
                    ext_lower = ext.lower().lstrip('.')
                    is_uuid_format = len(uuid_part) == 32 and all(c in '0123456789abcdef' for c in uuid_part)
                    is_known_media_ext = ext_lower in allowed_media_extensions
                    if is_uuid_format and is_known_media_ext and uuid_part not in db_uuids:
                        orphaned_uuid_files.append(item_info)
                    elif not is_uuid_format and item_name.lower() not in ['.ds_store', 'thumbs.db']:
                        unexpected_files.append(item_info)
        except OSError as e:
            print(f"Error reading directory {upload_folder}: {e}")
    else:
        print(f"Warning: Upload directory not found: {upload_folder}")

    # Scan Thumbnails Folder
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
                    is_expected_thumb_ext = ext.lower() == thumbnail_ext
                    if is_uuid_format and is_expected_thumb_ext and uuid_part not in db_uuids:
                         if not any(f['name'] == item_name and f['folder'] == 'thumbnails' for f in orphaned_uuid_files):
                             orphaned_uuid_files.append(item_info)
                    elif not is_uuid_format and item_name.lower() not in ['.ds_store', 'thumbs.db']:
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
    if not current_app:
        print("ERROR: Cannot cleanup without app context.")
        return 0, 0, len(items_to_delete)

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

def remove_missing_media_db_entries(missing_media_ids):
    """Deletes MediaFile records from the database based on a list of IDs."""
    from .models import MediaFile # Import locally
    deleted_count = 0
    error_count = 0
    if not current_app:
        print("ERROR: Cannot remove DB entries without app context.")
        return 0, len(missing_media_ids)
    if not missing_media_ids:
        return 0, 0

    media_changed = False # Track if commit is needed

    for media_id_str in missing_media_ids:
        try:
            media_id = int(media_id_str)
            media_record = db.session.get(MediaFile, media_id)
            if media_record:
                print(f"Removing DB record for missing media ID {media_id} ('{media_record.display_name}')")
                db.session.delete(media_record)
                deleted_count += 1
                media_changed = True
            else:
                print(f"DB record for missing media ID {media_id} not found (already deleted?).")
        except ValueError:
            print(f"Invalid media ID received for deletion: {media_id_str}")
            error_count += 1
        except Exception as e:
            print(f"Error deleting DB record for missing media ID {media_id_str}: {e}")
            traceback.print_exc()
            error_count += 1
            db.session.rollback() # Rollback this specific error

    if media_changed and error_count == 0:
        try:
            db.session.commit()
        except Exception as e:
            print(f"Error committing deletions of missing DB entries: {e}")
            traceback.print_exc()
            flash("Database error occurred while committing deletions.", "error")
            db.session.rollback()
            return 0, deleted_count + error_count
    elif media_changed: # Handle partial success
        try:
            db.session.commit()
            print(f"Committed deletion of {deleted_count} missing DB entries despite {error_count} errors during processing.")
        except Exception as e:
            print(f"Error committing partial deletions: {e}")
            traceback.print_exc()
            flash("Database error occurred while committing partial deletions.", "error")
            db.session.rollback()
            return 0, deleted_count + error_count

    return deleted_count, error_count
# --- END Validation Helpers ---
