# showgo/config.py
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Load environment variables from .env file at the root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print("Warning: .env file not found.")


# --- Default Settings (Moved to Module Level) ---
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
    "widgets_rss_scroll_speed": "medium", # *** NEW DEFAULT ***
    "auth_username": "admin",
    "auth_password_hash": generate_password_hash("showgo"),
    "auth_password_changed": False,
    "burn_in_prevention_enabled": False,
    "burn_in_prevention_elements": ["watermark"],
    "burn_in_prevention_interval_seconds": 15,
    "burn_in_prevention_strength_pixels": 3
}


# --- Base Configuration Class ---
class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-default-secret-key-replace-me'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database configuration
    DB_USER = os.environ.get('MYSQL_USER')
    DB_PASSWORD = os.environ.get('MYSQL_PASSWORD')
    DB_HOST = os.environ.get('MYSQL_HOST')
    DB_NAME = os.environ.get('MYSQL_DB')

    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
        print("WARNING: Database connection parameters missing in environment variables.")
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Fallback
    else:
        SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'

    # Application directories
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    THUMBNAIL_FOLDER = os.path.join(BASE_DIR, 'thumbnails')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'showgo', 'static')

    # Upload/Thumbnail settings
    MAX_CONTENT_LENGTH = 256 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    THUMBNAIL_SIZE = (150, 150)
    THUMBNAIL_FORMAT = 'PNG'
    THUMBNAIL_EXT = f".{THUMBNAIL_FORMAT.lower()}"

    # Make defaults accessible via app config if needed, though direct import is preferred now
    DEFAULT_SETTINGS_DB = DEFAULT_SETTINGS_DB

