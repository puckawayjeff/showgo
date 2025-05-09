# showgo/main_bp.py
# Blueprint for core slideshow viewer and related routes/API

import os
import random
import requests
import feedparser
import traceback
from flask import (Blueprint, render_template, current_app, send_from_directory,
                   jsonify, make_response, url_for) # *** ADDED url_for ***
from .extensions import db
from .models import MediaFile, Setting
from .utils import get_setting, get_config_timestamp_from_db, get_database_media, load_settings_from_db
from .config import DEFAULT_SETTINGS_DB # Import defaults

# Create Blueprint
main_bp = Blueprint('main_bp', __name__)

# --- Routes ---

@main_bp.route('/')
def slideshow_viewer():
    """ Route for the main slideshow display page. """
    # current_config_dict holds settings values from the database
    current_config_dict = load_settings_from_db()
    if current_config_dict is None: # Should not happen if initialize_database works
         print("CRITICAL ERROR: load_settings_from_db returned None unexpectedly. Using hardcoded defaults.")
         current_config_dict = DEFAULT_SETTINGS_DB.copy()

    config_timestamp = get_config_timestamp_from_db()

    # Use DEFAULT_SETTINGS_DB as the ultimate fallback for each key
    defaults = DEFAULT_SETTINGS_DB

    # Construct the full_config object to pass to the template.
    # This ensures all expected keys are present, using DB values or defaults.
    full_config = {
        "slideshow": {
            "duration_seconds": current_config_dict.get("slideshow_duration_seconds", defaults['slideshow_duration_seconds']),
            "transition_effect": current_config_dict.get("slideshow_transition_effect", defaults['slideshow_transition_effect']),
            "image_order": current_config_dict.get("slideshow_image_order", defaults['slideshow_image_order']),
            "image_scaling": current_config_dict.get("slideshow_image_scaling", defaults['slideshow_image_scaling']),
            "video_scaling": current_config_dict.get("slideshow_video_scaling", defaults['slideshow_video_scaling']),
            "video_autoplay": current_config_dict.get("slideshow_video_autoplay", defaults['slideshow_video_autoplay']),
            "video_loop": current_config_dict.get("slideshow_video_loop", defaults['slideshow_video_loop']),
            "video_muted": current_config_dict.get("slideshow_video_muted", defaults['slideshow_video_muted']),
            "video_show_controls": current_config_dict.get("slideshow_video_show_controls", defaults['slideshow_video_show_controls']),
        },
        "overlay": { # Changed from "watermark"
            "enabled": current_config_dict.get("overlay_enabled", defaults['overlay_enabled']),
            "text": current_config_dict.get("overlay_text", defaults['overlay_text']),
            "position": current_config_dict.get("overlay_position", defaults['overlay_position']),
            "font_size": current_config_dict.get("overlay_font_size", defaults['overlay_font_size']),
            "font_color": current_config_dict.get("overlay_font_color", defaults['overlay_font_color']),
            "logo_enabled": current_config_dict.get("overlay_logo_enabled", defaults['overlay_logo_enabled']),
            "display_mode": current_config_dict.get("overlay_display_mode", defaults['overlay_display_mode']),
            "background_color": current_config_dict.get("overlay_background_color", defaults['overlay_background_color']),
            "padding": current_config_dict.get("overlay_padding", defaults['overlay_padding']),
            "logo_url": None # Default to None, will be set if logo exists
        },
        "widgets": {
            "time": {"enabled": current_config_dict.get("widgets_time_enabled", defaults['widgets_time_enabled'])},
            "weather": {
                "enabled": current_config_dict.get("widgets_weather_enabled", defaults['widgets_weather_enabled']),
                "location": current_config_dict.get("widgets_weather_location", defaults['widgets_weather_location'])
            },
            "rss": {
                "enabled": current_config_dict.get("widgets_rss_enabled", defaults['widgets_rss_enabled']),
                "feed_url": current_config_dict.get("widgets_rss_feed_url", defaults['widgets_rss_feed_url']),
                "scroll_speed": current_config_dict.get("widgets_rss_scroll_speed", defaults['widgets_rss_scroll_speed'])
            }
        },
        "burn_in_prevention": {
            "enabled": current_config_dict.get("burn_in_prevention_enabled", defaults['burn_in_prevention_enabled']),
            "elements": current_config_dict.get("burn_in_prevention_elements", defaults['burn_in_prevention_elements']),
            "interval_seconds": current_config_dict.get("burn_in_prevention_interval_seconds", defaults['burn_in_prevention_interval_seconds']),
            "strength_pixels": current_config_dict.get("burn_in_prevention_strength_pixels", defaults['burn_in_prevention_strength_pixels'])
        },
    }

    # Check if overlay logo exists and set its URL
    if full_config["overlay"]["logo_enabled"]:
        # Use app.config for these fixed configuration values
        logo_filename = current_app.config.get('OVERLAY_LOGO_FILENAME', 'overlay_logo.png')
        assets_folder = current_app.config.get('ASSETS_FOLDER') # Path to static/assets
        logo_path_on_disk = os.path.join(assets_folder, logo_filename)

        if os.path.isfile(logo_path_on_disk):
            # Generate URL for the static asset within the 'assets' subfolder
            full_config["overlay"]["logo_url"] = url_for('static', filename=f'assets/{logo_filename}')
            # Add a cache-busting query parameter
            try:
                mtime = os.path.getmtime(logo_path_on_disk)
                full_config["overlay"]["logo_url"] += f"?v={int(mtime)}"
            except OSError:
                pass # If mtime fails, use URL without version
        else:
            print(f"Overlay logo enabled in settings, but '{logo_filename}' not found in '{assets_folder}'. Disabling logo for this view.")
            full_config["overlay"]["logo_enabled"] = False # Effectively disable if file not found

    # Get Validated Media List
    all_db_media, _ = get_database_media()
    valid_media_list = []
    for media in all_db_media:
        if media.check_files_exist():
            valid_media_list.append({
                'filename': media.get_disk_filename(),
                'type': media.media_type
            })
        else:
            print(f"Slideshow: Skipping media ID {media.id} ('{media.display_name}') due to missing file(s).")

    if not valid_media_list:
        print("Warning: No valid media files found for slideshow.")
    if full_config['slideshow']['image_order'] == 'random':
        random.shuffle(valid_media_list)

    # Fetch Weather / RSS
    weather_data = None
    weather_error = None
    rss_data = None
    rss_error = None
    weather_widget_config = full_config.get('widgets', {}).get('weather', {})
    openweathermap_api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
    if weather_widget_config.get('enabled'):
        location = weather_widget_config.get('location')
        if location and openweathermap_api_key:
            try:
                weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={openweathermap_api_key}&units=imperial"
                response = requests.get(weather_url, timeout=10)
                response.raise_for_status()
                weather_data = response.json()
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

    rss_widget_config = full_config.get('widgets', {}).get('rss', {})
    if rss_widget_config.get('enabled'):
        feed_url = rss_widget_config.get('feed_url')
        if feed_url:
            try:
                headers = {'User-Agent': f"ShowGo/{current_app.config.get('VERSION', '1.0')}"}
                rss_data_raw = feedparser.parse(feed_url, agent=headers['User-Agent'])
                if rss_data_raw.bozo:
                    bozo_exception_msg = str(rss_data_raw.bozo_exception) if hasattr(rss_data_raw, 'bozo_exception') else "Unknown parsing issue"
                    print(f"Error parsing RSS feed (bozo): {feed_url} - {bozo_exception_msg}")
                    rss_error = f"Feed Parsing Error: {bozo_exception_msg}"
                elif rss_data_raw.entries:
                    rss_data = [{'title': entry.get('title', 'No Title'), 'link': entry.get('link', '#')} for entry in rss_data_raw.entries[:15]]
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
                           config=full_config, # Pass the fully constructed config
                           media_items=valid_media_list,
                           weather=weather_data,
                           weather_error=weather_error,
                           rss_headlines=rss_data,
                           rss_error=rss_error,
                           initial_config_timestamp=config_timestamp)


@main_bp.route('/uploads/<path:filename>')
def serve_uploaded_media(filename):
    """Serves original uploaded media files (images and videos) with caching."""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    response = make_response(send_from_directory(upload_folder, filename))
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


@main_bp.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serves thumbnail images, providing a placeholder if not found, with caching."""
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
            resp_placeholder = make_response(send_from_directory(static_folder_images, 'placeholder_thumb.png'))
            resp_placeholder.headers['Cache-Control'] = 'public, max-age=3600'
            return resp_placeholder
        else:
            print("Placeholder thumbnail image not found!")
            return "Not Found", 404

    response = make_response(send_from_directory(thumbnail_folder, filename))
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


@main_bp.route('/api/config/check')
def check_config():
    """API endpoint for the client to check for configuration updates."""
    timestamp = get_config_timestamp_from_db()
    if timestamp is None:
         print("Error: check_config failed because get_config_timestamp_from_db returned None.")
         return jsonify({'error': 'Could not retrieve configuration status from server.', 'timestamp': 0}), 500
    else:
         return jsonify({'timestamp': timestamp})
