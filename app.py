# app.py
# Main application file for the ShowGo Slideshow Kiosk

import os
import json

# Make sure render_template, request, redirect, url_for, flash, send_from_directory are imported
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
)
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Import secure_filename for safe file handling
from werkzeug.utils import secure_filename

# Import Pillow for thumbnail generation
try:
    from PIL import Image, UnidentifiedImageError

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: Pillow library not found. Thumbnail generation will be skipped.")

    # Define dummy classes if Pillow is not available to avoid NameErrors later
    class UnidentifiedImageError(Exception):
        pass

    class Image:
        pass  # Dummy class


# Import werkzeug exceptions for specific error handling
from werkzeug.exceptions import RequestEntityTooLarge

# --- Configuration ---
# Define base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define paths for uploads and configuration relative to the base directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, "thumbnails")
CONFIG_FOLDER = os.path.join(BASE_DIR, "config")
CONFIG_FILE = os.path.join(CONFIG_FOLDER, "config.json")

# Define allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
THUMBNAIL_SIZE = (150, 150)  # Max width/height for thumbnails

# Ensure necessary directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)

# --- Default Configuration ---
DEFAULT_CONFIG = {
    "slideshow": {
        "duration_seconds": 10,
        "transition_effect": "fade",
        "image_order": "sequential",
    },
    "watermark": {
        "enabled": False,
        "text": "© Your Company",
        "position": "bottom-right",
        "move": True,
    },
    "widgets": {
        "time": {"enabled": True},
        "weather": {"enabled": True, "location": "Oshkosh, WI", "api_key": ""},
        "rss": {"enabled": False, "feed_url": ""},
    },
    "auth": {"username": "admin", "password_hash": generate_password_hash("password")},
}

# --- Helper Functions ---


def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_thumbnail(source_path, dest_path, size):
    """Generates a thumbnail for an image using Pillow."""
    if not PIL_AVAILABLE:
        # print("Skipping thumbnail generation: Pillow not available.") # Less verbose
        return False, None

    # print(f"--- Attempting to generate thumbnail for: {source_path}") # DEBUG
    try:
        if not os.path.isfile(source_path):
            # print(f"--- Source file not found: {source_path}") # DEBUG
            return False, None

        with Image.open(source_path) as img:
            # print(f"--- Opened image: {source_path} (Format: {img.format}, Size: {img.size})") # DEBUG
            if img.format == "GIF" and getattr(img, "is_animated", False):
                # print("--- Handling animated GIF (using first frame)") # DEBUG
                img.seek(0)
                img = img.convert("RGB")

            img.thumbnail(size)
            # print(f"--- Resized image to fit within: {size}") # DEBUG

            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            # print(f"--- Ensured destination directory exists: {dest_dir}") # DEBUG

            thumb_format = "PNG"  # Save thumbnails as PNG
            base, _ = os.path.splitext(dest_path)
            dest_path_with_ext = f"{base}.{thumb_format.lower()}"
            # print(f"--- Determined thumbnail save path: {dest_path_with_ext}") # DEBUG

            img.save(dest_path_with_ext, thumb_format)
            # print(f"--- SUCCESS: Generated thumbnail: {dest_path_with_ext}") # DEBUG
            return True, dest_path_with_ext  # Return success and actual path

    except UnidentifiedImageError:
        print(f"--- ERROR: Cannot identify image file {source_path}")  # DEBUG
        return False, None
    except FileNotFoundError:
        print(f"--- ERROR: File not found during Image.open: {source_path}")  # DEBUG
        return False, None
    except Exception as e:
        print(
            f"--- ERROR: Generic exception generating thumbnail for {os.path.basename(source_path)}: {e}"
        )  # DEBUG
        import traceback

        traceback.print_exc()
        return False, None


# --- Configuration Loading/Saving Functions ---
def load_config():
    """Loads configuration from config.json, falling back to defaults."""
    needs_resave = False  # Flag to indicate if migration happened
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded_settings = json.load(f)
                # Merge with defaults carefully to ensure all keys/subkeys exist
                config = DEFAULT_CONFIG.copy()
                for key, default_value in DEFAULT_CONFIG.items():
                    if key in loaded_settings:
                        if isinstance(default_value, dict):
                            # Merge dictionaries deeply (1 level for simplicity here)
                            config[key] = default_value.copy()
                            # Ensure sub-dictionaries exist before updating
                            if isinstance(loaded_settings.get(key), dict):
                                config[key].update(loaded_settings[key])
                            # Deeper merge for widgets
                            if key == "widgets":
                                for widget_key, widget_default in default_value.items():
                                    # Ensure sub-sub-dictionaries exist before updating
                                    if (
                                        widget_key in config[key]
                                        and isinstance(config[key][widget_key], dict)
                                        and isinstance(
                                            loaded_settings.get(key, {}).get(
                                                widget_key
                                            ),
                                            dict,
                                        )
                                    ):
                                        config[key][widget_key].update(
                                            loaded_settings[key][widget_key]
                                        )
                                    elif widget_key in loaded_settings.get(
                                        key, {}
                                    ):  # Handle case where default is dict but loaded is not
                                        config[key][widget_key] = loaded_settings[key][
                                            widget_key
                                        ]

                        else:
                            config[key] = loaded_settings[key]
                    # else: # Key from default not found in loaded, keep default (already handled by copy)
                    #      config[key] = default_value

                # Ensure auth structure exists if loading older config
                if "auth" not in config:
                    config["auth"] = DEFAULT_CONFIG["auth"].copy()
                    needs_resave = True  # Need to save the added auth section

                # Migration/Cleanup for password
                if "password" in config["auth"]:
                    if "password_hash" not in config["auth"]:
                        print("Hashing plain text password found in config...")
                        config["auth"]["password_hash"] = generate_password_hash(
                            config["auth"]["password"]
                        )
                    print("Removing plain text password from config...")
                    del config["auth"]["password"]
                    needs_resave = True

                if needs_resave:
                    # print("Resaving config after load/migration...") # Less verbose
                    save_config(config)

                # print("Configuration loaded from file.") # Less verbose
                return config
        except json.JSONDecodeError:
            print(
                f"Error decoding JSON from {CONFIG_FILE}. Using default configuration."
            )
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading config file: {e}. Using default configuration.")
            import traceback

            traceback.print_exc()
            return DEFAULT_CONFIG.copy()
    else:
        print("Config file not found. Saving default configuration.")
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()


def save_config(config_data):
    """Saves the configuration dictionary to config.json."""
    # Ensure plain password is removed if hash exists
    if (
        "auth" in config_data
        and "password_hash" in config_data["auth"]
        and "password" in config_data["auth"]
    ):
        # print("Removing plain text password before saving.") # Less verbose
        del config_data["auth"]["password"]

    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
        # print(f"Configuration saved to {CONFIG_FILE}") # Less verbose
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


# --- Flask App Initialization ---
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["THUMBNAIL_FOLDER"] = THUMBNAIL_FOLDER
# Increase max content length to allow larger batch uploads (e.g., 256MB)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024 * 1024
app.config["SHOWGO_CONFIG"] = load_config()
app.secret_key = "dev-secret-key"  # Change in production! Used for flash messages

# --- Authentication Setup ---
auth = HTTPBasicAuth(realm="ShowGo Configuration Access")


@auth.verify_password
def verify_password(username, password):
    """Checks username/password against the loaded configuration."""
    config_auth = app.config["SHOWGO_CONFIG"].get("auth", {})
    stored_username = config_auth.get("username")
    stored_password_hash = config_auth.get("password_hash")
    if username == stored_username and stored_password_hash:
        return check_password_hash(stored_password_hash, password)
    return False


# --- Routes ---


@app.route("/")
def slideshow_viewer():
    """
    Route for the main slideshow display page. (No auth required)
    """
    current_config = app.config["SHOWGO_CONFIG"]
    # Still showing JSON for now, will create slideshow.html later
    return f"<h1>Slideshow Viewer</h1><pre>{json.dumps(current_config, indent=2)}</pre>"


@app.route("/config")
@auth.login_required
def config_page():
    """
    Route for the configuration interface. Requires authentication.
    Renders the config.html template and passes the list of images.
    """
    current_config = app.config["SHOWGO_CONFIG"]
    image_files = []  # Initialize empty list
    try:
        if os.path.isdir(app.config["UPLOAD_FOLDER"]):
            image_files = sorted(
                [
                    f
                    for f in os.listdir(app.config["UPLOAD_FOLDER"])
                    if os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], f))
                    and allowed_file(f)
                ]
            )
        else:
            print(f"Upload directory not found: {app.config['UPLOAD_FOLDER']}")
            pass  # Keep image_files empty

    except Exception as e:
        print(f"Error listing upload directory: {e}")
        flash("Error retrieving image list.", "error")

    return render_template("config.html", config=current_config, images=image_files)


@app.route("/config/upload", methods=["POST"])
@auth.login_required
def upload_image():
    """Handles image uploads from the config page."""
    if not PIL_AVAILABLE:
        flash(
            "Image processing library (Pillow) not installed. Cannot generate thumbnails.",
            "error",
        )

    if "image_files" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("config_page"))

    files = request.files.getlist("image_files")
    uploaded_count = 0
    error_count = 0
    thumb_error_count = 0

    if not files or files[0].filename == "":
        flash("No selected file.", "error")
        return redirect(url_for("config_page"))

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(save_path):
                filename = f"{base}_{counter}{ext}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                counter += 1

            try:
                file.save(save_path)
                uploaded_count += 1

                if PIL_AVAILABLE:
                    thumb_filename = filename
                    thumb_dest_path = os.path.join(
                        app.config["THUMBNAIL_FOLDER"], thumb_filename
                    )
                    success, actual_thumb_path = generate_thumbnail(
                        save_path, thumb_dest_path, THUMBNAIL_SIZE
                    )
                    if not success:
                        thumb_error_count += 1

            except RequestEntityTooLarge as e:
                print(f"Upload failed for {filename}: {e}")
                flash(
                    "Upload failed: Total size of files exceeds the server limit.",
                    "error",
                )
                return redirect(url_for("config_page"))
            except Exception as e:
                print(f"Error saving file {filename}: {e}")
                flash(f"Error saving file {filename}.", "error")
                error_count += 1

        elif file and file.filename != "":
            flash(
                f"File type not allowed for {secure_filename(file.filename)}.", "error"
            )
            error_count += 1

    if uploaded_count > 0:
        success_msg = f"Successfully uploaded {uploaded_count} image(s)."
        if thumb_error_count > 0:
            success_msg += (
                f" Failed to generate thumbnails for {thumb_error_count} image(s)."
            )
            flash(success_msg, "warning")
        else:
            flash(success_msg, "success")

    if error_count > 0:
        flash(f"Failed to upload {error_count} file(s) or invalid type.", "error")

    return redirect(url_for("config_page"))


@app.route("/thumbnails/<path:filename>")
def serve_thumbnail(filename):
    """Serves thumbnail images."""
    requested_path = os.path.join(app.config["THUMBNAIL_FOLDER"], filename)
    safe_path = os.path.abspath(requested_path)

    if not safe_path.startswith(os.path.abspath(app.config["THUMBNAIL_FOLDER"])):
        return "Forbidden", 403

    if not os.path.isfile(safe_path):
        placeholder = os.path.join(
            BASE_DIR, "static", "images", "placeholder_thumb.png"
        )
        if os.path.isfile(placeholder):
            return send_from_directory(
                os.path.join(BASE_DIR, "static", "images"), "placeholder_thumb.png"
            )
        else:
            return "Not Found", 404

    return send_from_directory(app.config["THUMBNAIL_FOLDER"], filename)


@app.route("/config/delete", methods=["POST"])
@auth.login_required
def delete_images():
    """Handles deleting selected images."""
    images_to_delete = request.form.getlist("selected_images")

    if not images_to_delete:
        flash("No images selected for deletion.", "warning")
        return redirect(url_for("config_page"))

    deleted_count = 0
    error_count = 0

    for filename in images_to_delete:
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            print(
                f"Warning: Filename '{filename}' sanitized to '{safe_filename}' during deletion check. Skipping."
            )
            error_count += 1
            continue

        original_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
        thumb_base, _ = os.path.splitext(safe_filename)
        thumb_filename_png = f"{thumb_base}.png"
        thumbnail_path = os.path.join(
            app.config["THUMBNAIL_FOLDER"], thumb_filename_png
        )

        original_deleted = False
        try:
            if os.path.isfile(original_path):
                os.remove(original_path)
                original_deleted = True
            else:
                print(f"Original file not found for deletion: {original_path}")

            if os.path.isfile(thumbnail_path):
                os.remove(thumbnail_path)
            else:
                print(f"Thumbnail file not found for deletion: {thumbnail_path}")

            if original_deleted:
                deleted_count += 1

        except OSError as e:
            print(f"Error deleting file {safe_filename}: {e}")
            error_count += 1

    if deleted_count > 0:
        flash(f"Successfully deleted {deleted_count} image(s).", "success")
    if error_count > 0:
        flash(
            f"Error occurred while deleting {error_count} file(s). Check logs.", "error"
        )

    return redirect(url_for("config_page"))


# --- NEW ROUTE for Saving Settings ---
@app.route("/config/save", methods=["POST"])
@auth.login_required
def save_settings():
    """Handles saving the configuration settings."""
    try:
        # Load the current config to update it
        current_config = app.config["SHOWGO_CONFIG"]  # This is a reference

        # Update Slideshow Settings
        current_config["slideshow"]["duration_seconds"] = int(
            request.form.get("duration_seconds", 10)
        )
        current_config["slideshow"]["transition_effect"] = request.form.get(
            "transition_effect", "fade"
        )
        current_config["slideshow"]["image_order"] = request.form.get(
            "image_order", "sequential"
        )

        # Update Watermark Settings (handle checkboxes - present if checked, absent if not)
        current_config["watermark"]["enabled"] = "watermark_enabled" in request.form
        current_config["watermark"]["text"] = request.form.get("watermark_text", "")
        current_config["watermark"]["position"] = request.form.get(
            "watermark_position", "bottom-right"
        )
        current_config["watermark"]["move"] = "watermark_move" in request.form

        # Update Widget Settings
        current_config["widgets"]["time"]["enabled"] = (
            "time_widget_enabled" in request.form
        )
        current_config["widgets"]["weather"]["enabled"] = (
            "weather_widget_enabled" in request.form
        )
        current_config["widgets"]["weather"]["location"] = request.form.get(
            "weather_location", ""
        )
        current_config["widgets"]["weather"]["api_key"] = request.form.get(
            "weather_api_key", ""
        )
        current_config["widgets"]["rss"]["enabled"] = (
            "rss_widget_enabled" in request.form
        )
        current_config["widgets"]["rss"]["feed_url"] = request.form.get(
            "rss_feed_url", ""
        )

        # --- TODO: Add password change logic here if desired ---
        # Example:
        # new_password = request.form.get('new_password')
        # confirm_password = request.form.get('confirm_password')
        # if new_password and new_password == confirm_password:
        #     current_config['auth']['password_hash'] = generate_password_hash(new_password)
        #     print("Admin password updated.")
        # elif new_password or confirm_password:
        #     flash("Passwords do not match or new password empty.", "error")
        # -------------------------------------------------------

        # Save the updated configuration object back to the file
        if save_config(current_config):
            # Update the config in the running app instance as well
            app.config["SHOWGO_CONFIG"] = current_config
            flash("Configuration saved successfully!", "success")
        else:
            flash("Error saving configuration.", "error")

    except ValueError:
        flash(
            "Invalid input value provided (e.g., duration must be a number).", "error"
        )
    except Exception as e:
        print(f"Error processing save settings request: {e}")
        import traceback

        traceback.print_exc()
        flash("An unexpected error occurred while saving settings.", "error")

    return redirect(url_for("config_page"))


# --- Running the App ---
if __name__ == "__main__":
    if not PIL_AVAILABLE:
        print("-------------------------------------------------------")
        print("WARNING: Pillow library not installed or import failed.")
        print("         pip install Pillow")
        print("         Thumbnail generation will be skipped.")
        print("-------------------------------------------------------")

    print(f"Base directory: {BASE_DIR}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Thumbnail folder: {THUMBNAIL_FOLDER}")
    print(f"Config folder: {CONFIG_FOLDER}")
    app.run(debug=True, host="0.0.0.0")
