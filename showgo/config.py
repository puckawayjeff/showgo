# showgo/config.py
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone

# Load environment variables from .env file at the root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print("Warning: .env file not found (needed for SECRET_KEY).")


# --- Default Settings ---
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg'}
ALLOWED_VIDEO_CODECS = {'h264', 'vp9', 'av1'}
ALLOWED_AUDIO_CODECS = {'aac', 'opus', 'mp3', 'vorbis'}

DEFAULT_SETTINGS_DB = {
    # Slideshow General
    "slideshow_duration_seconds": 10,
    "slideshow_transition_effect": "kenburns",
    "slideshow_image_order": "random",
    "slideshow_image_scaling": "cover",

    # Video Specific
    "slideshow_video_scaling": "contain",
    "slideshow_video_autoplay": True,
    "slideshow_video_loop": False,
    "slideshow_video_muted": True,
    "slideshow_video_show_controls": False,

    # *** RENAMED & EXPANDED: Overlay Branding (formerly Watermark) ***
    "overlay_enabled": False,
    "overlay_text": "ShowGo Display", # Default text
    "overlay_position": "bottom-right", # Options: top-left, top-center, top-right, middle-left, center, middle-right, bottom-left, bottom-center, bottom-right
    "overlay_font_size": "24px", # Default font size (e.g., 16px, 1.5em, etc.)
    "overlay_font_color": "#FFFFFF", # Default font color (hex)
    "overlay_logo_enabled": False, # Whether to display the uploaded logo
    # Display mode: 'text_only', 'logo_only', 'logo_and_text_side' (logo left, text right), 'logo_and_text_below' (logo top, text bottom)
    "overlay_display_mode": "text_only",
    "overlay_background_color": "rgba(0, 0, 0, 0.5)", # Optional background for the overlay box
    "overlay_padding": "10px", # Padding within the overlay box

    # Widgets
    "widgets_time_enabled": True,
    "widgets_weather_enabled": True,
    "widgets_weather_location": "Oshkosh",
    "widgets_rss_enabled": False,
    "widgets_rss_feed_url": "https://feeds.bbci.co.uk/news/rss.xml?edition=us",
    "widgets_rss_scroll_speed": "medium",

    # Auth
    "auth_username": "admin",
    "auth_password_hash": generate_password_hash("showgo"),
    "auth_password_changed": False,

    # Burn-in Prevention
    "burn_in_prevention_enabled": False,
    # *** Update default element to shift if watermark name changes ***
    "burn_in_prevention_elements": ["overlay"], # Changed from "watermark"
    "burn_in_prevention_interval_seconds": 15,
    "burn_in_prevention_strength_pixels": 3,

    # Media Timestamp
    "media_last_changed": datetime.now(timezone.utc).timestamp()
}


# --- Base Configuration Class ---
class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-default-secret-key-replace-me'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application directories
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    INSTANCE_FOLDER_PATH = os.path.join(BASE_DIR, 'instance')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    THUMBNAIL_FOLDER = os.path.join(BASE_DIR, 'thumbnails')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'showgo', 'static')
    # *** NEW: Define a folder for static assets like the overlay logo ***
    ASSETS_FOLDER = os.path.join(STATIC_FOLDER, 'assets')
    OVERLAY_LOGO_FILENAME = 'overlay_logo.png' # Predefined filename for the logo

    # SQLite Database configuration
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_FOLDER_PATH, 'showgo.db')}"
    print(f"Using SQLite database at: {SQLALCHEMY_DATABASE_URI}")

    # Ensure essential folders exist
    try:
        os.makedirs(INSTANCE_FOLDER_PATH, exist_ok=True)
        print(f"Instance folder checked/created: {INSTANCE_FOLDER_PATH}")
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        print(f"Uploads folder checked/created: {UPLOAD_FOLDER}")
        os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
        print(f"Thumbnails folder checked/created: {THUMBNAIL_FOLDER}")
        # *** ADDED: Ensure ASSETS_FOLDER exists ***
        os.makedirs(ASSETS_FOLDER, exist_ok=True)
        print(f"Assets folder checked/created: {ASSETS_FOLDER}")
    except OSError as e:
        print(f"ERROR: Could not create essential directory: {e}")

    # Upload/Thumbnail settings
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024 # 512MB
    ALLOWED_IMAGE_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS
    ALLOWED_VIDEO_EXTENSIONS = ALLOWED_VIDEO_EXTENSIONS
    ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_VIDEO_EXTENSIONS)
    ALLOWED_VIDEO_CODECS = ALLOWED_VIDEO_CODECS
    ALLOWED_AUDIO_CODECS = ALLOWED_AUDIO_CODECS
    THUMBNAIL_SIZE = (150, 150)
    THUMBNAIL_FORMAT = 'PNG' # Thumbnails will remain PNG
    THUMBNAIL_EXT = f".{THUMBNAIL_FORMAT.lower()}"

    # Make defaults accessible via app config
    DEFAULT_SETTINGS_DB = DEFAULT_SETTINGS_DB
