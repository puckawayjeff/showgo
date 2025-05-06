# showgo/errors.py
# Error handlers for the ShowGo application

import traceback
from flask import render_template, jsonify, flash, redirect, url_for, current_app
from werkzeug.exceptions import NotFound, InternalServerError, RequestEntityTooLarge
from sqlalchemy.exc import OperationalError # Import if needed for specific DB errors
from .extensions import db # Import db instance if needed for rollback

# --- Custom Error Handlers ---

# Note: These handlers are registered in create_app() in __init__.py

def page_not_found(error):
    """Renders the custom 404 error page."""
    # error variable contains Werkzeug exception info
    print(f"404 Error: {error}") # Log the specific 404 error
    return render_template('404.html'), 404

def internal_server_error(error):
    """Renders the custom 500 error page and logs the error."""
    # Log the error for debugging purposes
    # Get original exception if it's wrapped by Werkzeug/Flask
    original_exception = getattr(error, "original_exception", error)
    print(f"!!! 500 Error Encountered: {original_exception} !!!")
    traceback.print_exc() # Print the full traceback to the console

    # Attempt to rollback the database session in case the error left it in a bad state
    try:
        # Check if db is bound to an app context before trying to rollback
        if db.session is not None:
             db.session.rollback()
             print("Database session rolled back due to 500 error.")
        else:
             print("DB session not active, skipping rollback.")
    except Exception as db_err:
        print(f"Error rolling back database session during 500 handling: {db_err}")

    # Render a user-friendly error page
    return render_template('500.html'), 500

def request_entity_too_large(error):
    """Handles the 'Request Entity Too Large' error (file upload size)."""
    # Access MAX_CONTENT_LENGTH from the current app's config
    max_size_mb = current_app.config.get('MAX_CONTENT_LENGTH', 256*1024*1024) // 1024 // 1024
    flash(f"Upload failed: File(s) exceed the maximum allowed size ({max_size_mb} MB).", "error")
    # Redirect back to the image config page
    # Use the correct endpoint name for the blueprint route
    return redirect(url_for('config_bp.config_images'))

