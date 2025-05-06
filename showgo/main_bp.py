# showgo/main_bp.py
# Blueprint for core slideshow viewer and related routes/API

import os
import random
import requests
import feedparser
import traceback
from flask import (Blueprint, render_template, current_app, send_from_directory,
                   jsonify)
from .extensions import db # Assuming db is initialized elsewhere
from .models import ImageFile, Setting # Import models
# *** CORRECTED IMPORT: Added load_settings_from_db ***
from .utils import get_setting, get_config_timestamp_from_db, get_database_images, load_settings_from_db
# *** ADDED IMPORT for DEFAULT_SETTINGS_DB ***
from .config import DEFAULT_SETTINGS_DB

# Create Blueprint
main_bp = Blueprint('main_bp', __name__)

# --- Routes ---

@main_bp.route('/')
def slideshow_viewer():
    """ Route for the main slideshow display page. """
    config = current_app.config
    current_config_dict = load_settings_from_db()
    if current_config_dict is None:
         print("CRITICAL ERROR: load_settings_from_db returned None unexpectedly.")
         current_config_dict = DEFAULT_SETTINGS_DB

    config_timestamp = get_config_timestamp_from_db()

    # Construct config, using imported DEFAULT_SETTINGS_DB for fallbacks
    current_config = {
        "slideshow": {
            "duration_seconds": current_config_dict.get("slideshow_duration_seconds", DEFAULT_SETTINGS_DB['slideshow_duration_seconds']),
            "transition_effect": current_config_dict.get("slideshow_transition_effect", DEFAULT_SETTINGS_DB['slideshow_transition_effect']),
            "image_order": current_config_dict.get("slideshow_image_order", DEFAULT_SETTINGS_DB['slideshow_image_order']),
            "image_scaling": current_config_dict.get("slideshow_image_scaling", DEFAULT_SETTINGS_DB['slideshow_image_scaling'])
        },
        "watermark": {
            "enabled": current_config_dict.get("watermark_enabled", DEFAULT_SETTINGS_DB['watermark_enabled']),
            "text": current_config_dict.get("watermark_text", DEFAULT_SETTINGS_DB['watermark_text']),
            "position": current_config_dict.get("watermark_position", DEFAULT_SETTINGS_DB['watermark_position'])
        },
        "widgets": {
            "time": {"enabled": current_config_dict.get("widgets_time_enabled", DEFAULT_SETTINGS_DB['widgets_time_enabled'])},
            "weather": {
                "enabled": current_config_dict.get("widgets_weather_enabled", DEFAULT_SETTINGS_DB['widgets_weather_enabled']),
                "location": current_config_dict.get("widgets_weather_location", DEFAULT_SETTINGS_DB['widgets_weather_location'])
            },
            "rss": {
                "enabled": current_config_dict.get("widgets_rss_enabled", DEFAULT_SETTINGS_DB['widgets_rss_enabled']),
                "feed_url": current_config_dict.get("widgets_rss_feed_url", DEFAULT_SETTINGS_DB['widgets_rss_feed_url'])
            }
        },
        "burn_in_prevention": {
            "enabled": current_config_dict.get("burn_in_prevention_enabled", DEFAULT_SETTINGS_DB['burn_in_prevention_enabled']),
            "elements": current_config_dict.get("burn_in_prevention_elements", DEFAULT_SETTINGS_DB['burn_in_prevention_elements']),
            "interval_seconds": current_config_dict.get("burn_in_prevention_interval_seconds", DEFAULT_SETTINGS_DB['burn_in_prevention_interval_seconds']),
            "strength_pixels": current_config_dict.get("burn_in_prevention_strength_pixels", DEFAULT_SETTINGS_DB['burn_in_prevention_strength_pixels'])
        },
    }

    # --- Get Validated Image List ---
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

    # --- Fetch Weather / RSS with Error Capture ---
    weather_data = None
    weather_error = None
    rss_data = None
    rss_error = None

    weather_widget_config = current_config.get('widgets', {}).get('weather', {})
    openweathermap_api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
    if weather_widget_config.get('enabled'):
        location = weather_widget_config.get('location')
        if location and openweathermap_api_key:
            try:
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
        elif not location:
             print("Weather widget enabled, but no location is set.")
             weather_error = "Location Missing"

    rss_widget_config = current_config.get('widgets', {}).get('rss', {})
    if rss_widget_config.get('enabled'):
        feed_url = rss_widget_config.get('feed_url')
        if feed_url:
            try:
                headers = {'User-Agent': f"ShowGo/{current_app.config.get('VERSION', '1.0')}"}
                # *** REMOVED socket_timeout argument ***
                rss_data_raw = feedparser.parse(feed_url, agent=headers['User-Agent'])
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

    return render_template('slideshow.html',
                           config=current_config,
                           images=valid_images,
                           weather=weather_data,
                           weather_error=weather_error,
                           rss_headlines=rss_data,
                           rss_error=rss_error,
                           initial_config_timestamp=config_timestamp)


@main_bp.route('/uploads/<path:filename>')
def serve_uploaded_image(filename):
    """Serves original uploaded images."""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, filename)


@main_bp.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serves thumbnail images, providing a placeholder if not found."""
    thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
    static_folder_images = os.path.join(current_app.static_folder, 'images')

    requested_path = os.path.join(thumbnail_folder, filename)
    safe_path = os.path.abspath(requested_path)

    if not safe_path.startswith(os.path.abspath(thumbnail_folder)):
        print(f"Forbidden access attempt for thumbnail: {filename}")
        return "Forbidden", 403

    if not os.path.isfile(safe_path):
        print(f"Thumbnail not found: {filename}. Serving placeholder.")
        placeholder = os.path.join(static_folder_images, 'placeholder_thumb.png')
        if os.path.isfile(placeholder):
            return send_from_directory(static_folder_images, 'placeholder_thumb.png')
        else:
            print("Placeholder thumbnail image not found!")
            return "Not Found", 404

    return send_from_directory(thumbnail_folder, filename)


@main_bp.route('/api/config/check')
def check_config():
    """API endpoint for the client to check for configuration updates."""
    timestamp = get_config_timestamp_from_db() # Use util
    if timestamp is None:
         print("Error: check_config failed because get_config_timestamp_from_db returned None.")
         return jsonify({'error': 'Could not retrieve configuration status from server.', 'timestamp': 0}), 500
    else:
         # print(f"API check_config returning timestamp: {timestamp}") # Keep debug off
         return jsonify({'timestamp': timestamp})

