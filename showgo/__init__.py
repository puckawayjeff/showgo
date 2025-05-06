# showgo/__init__.py

import os
import traceback # Keep traceback for potential error logging here too
from flask import Flask
from .config import Config, DEFAULT_SETTINGS_DB # Import configuration and defaults
from .extensions import db, auth # Import initialized extensions
from .models import Setting, MediaFile # Import models to ensure they are known to SQLAlchemy

# Import Blueprints
from .main_bp import main_bp
from .config_bp import config_bp
from .cli import db_cli_bp # Import CLI commands blueprint

# Import utility functions needed during app creation or globally
from .utils import initialize_database, load_settings_from_db # Import DB functions

# Import specific exceptions for error handlers
# *** ADDED RequestEntityTooLarge HERE ***
from werkzeug.exceptions import NotFound, InternalServerError, RequestEntityTooLarge
from sqlalchemy.exc import OperationalError


# Application Factory Function
def create_app(config_class=Config):
    """Creates and configures the Flask application instance."""
    app = Flask(__name__,
                instance_relative_config=False, # Config is in the package
                static_folder='static', # Explicitly set static folder within package
                template_folder='templates' # Explicitly set template folder within package
               )

    # Load configuration from config object
    app.config.from_object(config_class)

    # Initialize Flask extensions that use init_app
    db.init_app(app)
    # auth is initialized in extensions.py and used via decorators

    # --- Load initial settings into cache ---
    # This needs the app context
    try:
        with app.app_context():
            print("Attempting to initialize database and load initial settings cache...")
            # Ensure DB exists and defaults are populated
            if not initialize_database():
                # Handle critical DB init failure if necessary
                print("!!! WARNING: Database initialization failed during startup !!!")
                # Fallback to defaults might happen in load_settings_from_db

            # Load settings, relying on its internal recovery & defaults
            app.config['SHOWGO_CONFIG_DB'] = load_settings_from_db()

            # Check for PIL here if needed, store in app.config
            try:
                from PIL import Image, UnidentifiedImageError
                app.config['PIL_AVAILABLE'] = True
            except ImportError:
                app.config['PIL_AVAILABLE'] = False
                print("WARNING: Pillow library not found during app creation.")
    except Exception as e:
        print(f"FATAL ERROR during app initialization or initial DB load: {e}")
        traceback.print_exc()
        # Decide if app should exit or try to continue with hardcoded defaults
        print("!!! WARNING: App startup failed critically. Exiting. !!!")
        # raise SystemExit(f"App startup failed: {e}") # Or exit more gracefully


    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(config_bp, url_prefix='/config')
    app.register_blueprint(db_cli_bp)

    print("Flask app created and configured.")
    print(f"Registered Blueprints: {list(app.blueprints.keys())}")

    # --- Define verify_password here, associated with the 'auth' instance ---
    @auth.verify_password
    def verify_password(username, password):
        """Verify user credentials against stored settings."""
        from werkzeug.security import check_password_hash
        # Import get_setting from utils INSIDE the function if needed
        from .utils import get_setting

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

    # --- Register global error handlers ---
    # Import the handler functions from the new errors module
    from .errors import page_not_found, internal_server_error, request_entity_too_large

    app.register_error_handler(404, page_not_found)
    app.register_error_handler(NotFound, page_not_found) # Also register specific exception
    app.register_error_handler(500, internal_server_error)
    app.register_error_handler(InternalServerError, internal_server_error) # Also register specific exception
    app.register_error_handler(Exception, internal_server_error) # Catch broader Python exceptions
    app.register_error_handler(413, request_entity_too_large)
    app.register_error_handler(RequestEntityTooLarge, request_entity_too_large) # Also register specific exception
    # --- End Error Handler Registration ---

    return app
