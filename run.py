# run.py
# Main entry point to run the ShowGo application.

import os
from showgo import create_app # Import the factory function

# Optional: Load environment variables here if needed before app creation
# from dotenv import load_dotenv
# load_dotenv()

# Create the Flask app instance using the factory
app = create_app()

if __name__ == '__main__':
    # Get host and debug settings (consider environment variables for production)
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # Add startup checks back here if desired (e.g., PIL, API key)
    # These could also live within create_app or be logged elsewhere.
    # Example check (needs PIL_AVAILABLE imported or checked differently):
    # if not app.config.get('PIL_AVAILABLE', False):
    #    print("-------------------------------------------------------\nWARNING: Pillow library not installed. Thumbnails disabled.\n         pip install Pillow\n-------------------------------------------------------")
    print(f"Starting ShowGo on {host} (Debug: {debug})")
    app.run(host=host, port=5000, debug=debug)

