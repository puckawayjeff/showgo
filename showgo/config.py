# showgo/config.py
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone # Import datetime

# Load environment variables from .env file at the root
# Keep this for SECRET_KEY and potentially other future keys
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print("Warning: .env file not found (needed for SECRET_KEY).")


# --- Default Settings (No change needed here) ---
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg'}
DEFAULT_SETTINGS_DB = {
    "slideshow_duration_seconds": 10, "slideshow_transition_effect": "kenburns",
    "slideshow_image_order": "random", "slideshow_image_scaling": "cover",
    "slideshow_video_scaling": "contain", "slideshow_video_autoplay": True,
    "slideshow_video_loop": False, "slideshow_video_muted": True,
    "slideshow_video_show_controls": False, "watermark_enabled": False,
    "watermark_text": "ShowGo Slideshow", "watermark_position": "top-right",
    "widgets_time_enabled": True, "widgets_weather_enabled": True,
    "widgets_weather_location": "Oshkosh", "widgets_rss_enabled": False,
    "widgets_rss_feed_url": "https://feeds.bbci.co.uk/news/rss.xml?edition=us",
    "widgets_rss_scroll_speed": "medium", "auth_username": "admin",
    "auth_password_hash": generate_password_hash("showgo"),
    "auth_password_changed": False, "burn_in_prevention_enabled": False,
    "burn_in_prevention_elements": ["watermark"],
    "burn_in_prevention_interval_seconds": 15,
    "burn_in_prevention_strength_pixels": 3,
    "media_last_changed": datetime.now(timezone.utc).timestamp()
}


# --- Base Configuration Class ---
class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-default-secret-key-replace-me'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application directories
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # *** ADDED: Define instance folder path ***
    # Typically one level above the 'showgo' package, alongside run.py
    INSTANCE_FOLDER_PATH = os.path.join(BASE_DIR, 'instance')

    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    THUMBNAIL_FOLDER = os.path.join(BASE_DIR, 'thumbnails')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'showgo', 'static')

    # *** UPDATED: Database configuration for SQLite ***
    # Store the SQLite DB file in the instance folder
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_FOLDER_PATH, 'showgo.db')}"
    print(f"Using SQLite database at: {SQLALCHEMY_DATABASE_URI}")

    # *** REMOVED: MySQL specific variables ***
    # DB_USER = os.environ.get('MYSQL_USER')
    # DB_PASSWORD = os.environ.get('MYSQL_PASSWORD')
    # DB_HOST = os.environ.get('MYSQL_HOST')
    # DB_NAME = os.environ.get('MYSQL_DB')
    # SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'

    # Ensure the instance folder exists
    try:
        os.makedirs(INSTANCE_FOLDER_PATH, exist_ok=True)
        print(f"Instance folder checked/created: {INSTANCE_FOLDER_PATH}")
    except OSError as e:
        print(f"Error creating instance folder '{INSTANCE_FOLDER_PATH}': {e}")


    # Upload/Thumbnail settings (No change needed here)
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS
    ALLOWED_VIDEO_EXTENSIONS = ALLOWED_VIDEO_EXTENSIONS
    ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_VIDEO_EXTENSIONS)
    THUMBNAIL_SIZE = (150, 150)
    THUMBNAIL_FORMAT = 'PNG'
    THUMBNAIL_EXT = f".{THUMBNAIL_FORMAT.lower()}"

    # Make defaults accessible via app config
    DEFAULT_SETTINGS_DB = DEFAULT_SETTINGS_DB

