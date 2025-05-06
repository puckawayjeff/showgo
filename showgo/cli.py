# showgo/cli.py
# Flask CLI commands for the ShowGo application

import click
from flask import Blueprint
from .utils import initialize_database # Import the shared init function

# Create a Blueprint for CLI commands
db_cli_bp = Blueprint('db_cli', __name__, cli_group='db')

@db_cli_bp.cli.command('init')
def init_db_command():
    """Creates database tables and populates default settings."""
    print("Running database initialization via CLI...")
    if initialize_database():
        print("Database initialization command completed successfully.")
    else:
        print("Database initialization command failed. Check logs for errors.")

# You can add more CLI commands here later if needed
# Example:
# @db_cli_bp.cli.command('clear-images')
# def clear_images_command():
#     """Removes all images from the database and filesystem."""
#     # Add logic here...
#     print("Image clearing command executed.")

