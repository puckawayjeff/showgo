# app.py
# Main application file for the ShowGo Slideshow Kiosk

import os
import json
import random  # For random image order
import requests  # For weather API calls
import feedparser  # For RSS feed parsing
import traceback  # For detailed error logging
from datetime import datetime  # For time widget (potentially)

# Make sure render_template, request, redirect, url_for, flash, send_from_directory, jsonify are imported
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    jsonify,
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
STATIC_FOLDER = os.path.join(BASE_DIR, "static")  # Define static folder path

# Define allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
THUMBNAIL_SIZE = (150, 150)  # Max width/height for thumbnails

# Ensure necessary directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)
os.makedirs(
    os.path.join(STATIC_FOLDER, "images"), exist_ok=True
)  # Ensure static images dir exists

# --- Default Configuration ---
# (Keep DEFAULT_CONFIG definition the same as previous version)
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
# (Keep allowed_file and generate_thumbnail functions the same)
def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_thumbnail(source_path, dest_path, size):
    """Generates a thumbnail for an image using Pillow."""
    if not PIL_AVAILABLE:
        return False, None
    try:
        if not os.path.isfile(source_path):
            return False, None
        with Image.open(source_path) as img:
            if img.format == "GIF" and getattr(img, "is_animated", False):
                img.seek(0)
                img = img.convert("RGB")
            img.thumbnail(size)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            thumb_format = "PNG"
            base, _ = os.path.splitext(dest_path)
            dest_path_with_ext = f"{base}.{thumb_format.lower()}"
            img.save(dest_path_with_ext, thumb_format)
            return True, dest_path_with_ext
    except UnidentifiedImageError:
        print(f"--- ERROR: Cannot identify image file {source_path}")
        return False, None
    except FileNotFoundError:
        print(f"--- ERROR: File not found during Image.open: {source_path}")
        return False, None
    except Exception as e:
        print(
            f"--- ERROR: Generic exception generating thumbnail for {os.path.basename(source_path)}: {e}"
        )
        traceback.print_exc()
        return False, None


# --- Configuration Loading/Saving Functions ---
# (Keep load_config and save_config functions the same)
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
                # Ensure auth structure exists if loading older config
                if "auth" not in config:
                    config["auth"] = DEFAULT_CONFIG["auth"].copy()
                    needs_resave = True
                # Migration/Cleanup for password
                if "password" in config["auth"]:
                    if "password_hash" not in config["auth"]:
                        config["auth"]["password_hash"] = generate_password_hash(
                            config["auth"]["password"]
                        )
                    del config["auth"]["password"]
                    needs_resave = True
                if needs_resave:
                    save_config(config)
                return config
        except json.JSONDecodeError:
            print(
                f"Error decoding JSON from {CONFIG_FILE}. Using default configuration."
            )
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading config file: {e}. Using default configuration.")
            traceback.print_exc()
            return DEFAULT_CONFIG.copy()
    else:
        print("Config file not found. Saving default configuration.")
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()


def save_config(config_data):
    """Saves the configuration dictionary to config.json."""
    if (
        "auth" in config_data
        and "password_hash" in config_data["auth"]
        and "password" in config_data["auth"]
    ):
        del config_data["auth"]["password"]
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


# --- Flask App Initialization ---
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["THUMBNAIL_FOLDER"] = THUMBNAIL_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024 * 1024
app.config["SHOWGO_CONFIG"] = load_config()
app.secret_key = "dev-secret-key"  # Change in production! Used for flash messages

# --- Authentication Setup ---
# (Keep auth setup and verify_password the same)
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


# --- UPDATED Slideshow Viewer Route ---
@app.route("/")
def slideshow_viewer():
    """
    Route for the main slideshow display page. Fetches data and renders template.
    """
    current_config = app.config["SHOWGO_CONFIG"]
    image_files = []
    weather_data = None
    rss_data = None

    # --- Get Image List ---
    try:
        if os.path.isdir(app.config["UPLOAD_FOLDER"]):
            image_files = [
                f
                for f in os.listdir(app.config["UPLOAD_FOLDER"])
                if os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], f))
                and allowed_file(f)
            ]
            # Apply sorting/randomization based on config
            if current_config["slideshow"]["image_order"] == "random":
                random.shuffle(image_files)
            else:  # Default to sequential (alphabetical)
                image_files.sort()
        else:
            print(f"Upload directory not found: {app.config['UPLOAD_FOLDER']}")

    except Exception as e:
        print(f"Error listing upload directory for slideshow: {e}")
        # Decide if we should show an error on the slideshow page or just run without images
        pass  # Continue with empty image_files list

    # --- Fetch Weather Data (if enabled) ---
    weather_config = current_config.get("widgets", {}).get("weather", {})
    if (
        weather_config.get("enabled")
        and weather_config.get("api_key")
        and weather_config.get("location")
    ):
        try:
            # Example using OpenWeatherMap API (replace with your preferred API structure)
            # Units=imperial for Fahrenheit
            api_key = weather_config["api_key"]
            location = weather_config["location"]
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=imperial"
            response = requests.get(weather_url, timeout=10)  # Add timeout
            response.raise_for_status()  # Raise exception for bad status codes (4xx or 5xx)
            weather_data = response.json()
            # print(f"Weather data fetched: {weather_data}") # Debug
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            # Keep weather_data as None, slideshow can handle this
        except Exception as e:
            print(f"Unexpected error processing weather data: {e}")
            traceback.print_exc()

    # --- Fetch RSS Data (if enabled) ---
    rss_config = current_config.get("widgets", {}).get("rss", {})
    if rss_config.get("enabled") and rss_config.get("feed_url"):
        try:
            feed_url = rss_config["feed_url"]
            # Set a user-agent to avoid potential blocking
            headers = {
                "User-Agent": "ShowGo/1.0 (https://github.com/puckawayjeff/showgo)"
            }
            # feedparser handles fetching internally, but we can pass headers via agent kwarg
            rss_data_raw = feedparser.parse(feed_url, agent=headers["User-Agent"])

            # Check for parsing errors indicated by feedparser
            if rss_data_raw.bozo and isinstance(rss_data_raw.bozo_exception, Exception):
                print(f"Error parsing RSS feed (bozo): {rss_data_raw.bozo_exception}")
                rss_data = None  # Treat as error
            elif rss_data_raw.entries:
                # Extract relevant info (e.g., first 5 titles)
                rss_data = [
                    {
                        "title": entry.get("title", "No Title"),
                        "link": entry.get("link", "#"),
                    }
                    for entry in rss_data_raw.entries[:5]
                ]  # Limit to 5 entries
                # print(f"RSS data fetched: {rss_data}") # Debug
            else:
                print(f"RSS feed parsed but no entries found: {feed_url}")
                rss_data = []  # No entries found

        except Exception as e:
            print(f"Error fetching or parsing RSS feed: {e}")
            traceback.print_exc()
            # Keep rss_data as None

    # Pass all data to the template
    return render_template(
        "slideshow.html",
        config=current_config,
        images=image_files,
        weather=weather_data,
        rss_headlines=rss_data,
    )


# --- NEW ROUTE for Serving Uploaded Images ---
@app.route("/uploads/<path:filename>")
def serve_uploaded_image(filename):
    """Serves images directly from the uploads folder."""
    # Basic security check (similar to thumbnails)
    requested_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    safe_path = os.path.abspath(requested_path)

    if not safe_path.startswith(os.path.abspath(app.config["UPLOAD_FOLDER"])):
        print(f"Attempt to access invalid upload path: {filename}")
        return "Forbidden", 403

    if not os.path.isfile(safe_path):
        print(f"Uploaded image not found: {safe_path}")
        return "Not Found", 404

    # print(f"Serving uploaded image: {safe_path}") # Less verbose
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# --- Config page route ---
# (Keep config_page route the same as previous version)
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


# --- Upload, Thumbnail, Delete, Save Settings routes ---
# (Keep upload_image, serve_thumbnail, delete_images, save_settings routes the same)
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
        placeholder = os.path.join(STATIC_FOLDER, "images", "placeholder_thumb.png")
        if os.path.isfile(placeholder):
            return send_from_directory(
                os.path.join(STATIC_FOLDER, "images"), "placeholder_thumb.png"
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


@app.route("/config/save", methods=["POST"])
@auth.login_required
def save_settings():
    """Handles saving the configuration settings."""
    try:
        current_config = app.config["SHOWGO_CONFIG"]
        current_config["slideshow"]["duration_seconds"] = int(
            request.form.get("duration_seconds", 10)
        )
        current_config["slideshow"]["transition_effect"] = request.form.get(
            "transition_effect", "fade"
        )
        current_config["slideshow"]["image_order"] = request.form.get(
            "image_order", "sequential"
        )
        current_config["watermark"]["enabled"] = "watermark_enabled" in request.form
        current_config["watermark"]["text"] = request.form.get("watermark_text", "")
        current_config["watermark"]["position"] = request.form.get(
            "watermark_position", "bottom-right"
        )
        current_config["watermark"]["move"] = "watermark_move" in request.form
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
        if save_config(current_config):
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
