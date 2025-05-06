# ShowGo - Web-Based Slideshow Kiosk

ShowGo is a self-hosted, web-based photo slideshow application designed for digital signage or personal use. It allows users to upload images and configure various display options through a web interface.

**License:** Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) - See LICENSE.md.

## Features

* **Web-Based Configuration:** Manage all settings through a password-protected web UI (`/config`).
* **Image Upload & Management:** Upload multiple images (JPG, PNG, GIF, WEBP). View thumbnails and delete images.
* **Slideshow Display:** View the configured slideshow at the root URL (`/`).
* **Customizable Display:**
    * Set image display duration.
    * Choose image order (sequential or random).
    * Select image scaling (`cover` or `contain`).
    * Select transition effects (`fade`, `slide`, `kenburns`).
    * Optional watermark with configurable text and position.
* **Widgets:**
    * Digital Clock
    * Weather display (requires free OpenWeatherMap API key)
    * RSS feed ticker (configurable URL and scroll speed)
* **Display Protection:**
    * Optional burn-in prevention (slight pixel shift for static elements).
* **Error Handling:**
    * Custom pages for 404 (Not Found) and 500 (Server Error).
    * Silent failure for Weather/RSS widgets (errors logged to console).
* **Filesystem Validation:** Detects and allows cleanup of missing image files or orphaned files/thumbnails via the config UI.
* **Database Self-Healing:** Attempts to recreate missing tables (`settings`, `images`) on startup or during operation.
* **Environment Variable Configuration:** Key settings (database credentials, secret key, API keys) are managed via a `.env` file.
* **Application Factory Pattern:** Uses a structured approach for application creation and configuration.
* **Blueprints:** Code organized into logical components (main display, configuration).

## Project Structure
```bash 
your_project_root/
├── run.py             # Main script to run the Flask development server
├── .env               # Environment variables (DB creds, API keys, SECRET_KEY) - CREATE THIS
├── requirements.txt   # Python dependencies
├── uploads/           # Image uploads (created automatically)
├── thumbnails/        # Image thumbnails (created automatically)
└── showgo/            # Main application package
    ├── __init__.py    # App factory (create_app)
    ├── config.py      # Configuration classes & Default Settings
    ├── extensions.py  # Flask extension instances (db, auth)
    ├── models.py      # SQLAlchemy models (Setting, ImageFile)
    ├── utils.py       # Helper functions (DB init, validation, etc.)
    ├── cli.py         # CLI commands (init-db)
    ├── main_bp.py     # Blueprint for main routes (/, /uploads, /api)
    ├── config_bp.py   # Blueprint for config routes (/config/*, /logout)
    ├── errors.py      # Error handler functions
    ├── static/        # Static files (CSS, JS, placeholder images)
    │   ├── css/
    │   │   └── config_styles.css
    │   ├── js/
    │   │   └── slideshow.js
    │   └── images/
    │       └── placeholder_thumb.png
    └── templates/     # HTML Templates
        ├── config_base.html
        ├── config_general.html
        ├── config_images.html
        ├── config_initial_password.html
        ├── slideshow.html
        ├── logout.html
        ├── 404.html
        └── 500.html
```
## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd showgo
    ```
2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    # Activate the environment
    # Windows:
    .\venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Ensure `requirements.txt` is up-to-date with libraries like Flask, Flask-SQLAlchemy, mysql-connector-python, Pillow, requests, feedparser, Flask-HTTPAuth, Werkzeug, python-dotenv).*
4.  **Database Setup:**
    * Ensure you have a MySQL server running.
    * Create a database (e.g., `showgo_db`) and a user with privileges on that database.
5.  **Configure Environment Variables:**
    * Create a file named `.env` in the project root directory (where `run.py` is).
    * Add the following variables, replacing the placeholder values:
        ```dotenv
        # Flask Secret Key (generate a strong random key)
        SECRET_KEY='your_strong_random_secret_key'

        # Database Credentials
        MYSQL_USER='your_db_user'
        MYSQL_PASSWORD='your_db_password'
        MYSQL_HOST='your_db_host' # e.g., localhost or IP address
        MYSQL_DB='your_db_name'   # e.g., showgo_db

        # OpenWeatherMap API Key (Optional, for weather widget)
        # Get a free key from [https://openweathermap.org/](https://openweathermap.org/)
        OPENWEATHERMAP_API_KEY='your_openweathermap_api_key'
        ```
6.  **Initialize Database Tables:**
    * Run the Flask CLI command to create the necessary tables and populate default settings:
        ```bash
        flask db init
        ```

## Running the Application

1.  **Activate Virtual Environment** (if not already active):
    ```bash
    # Windows: .\venv\Scripts\activate
    # Linux/macOS: source venv/bin/activate
    ```
2.  **Run the Development Server:**
    * Use the `run.py` script with Flask:
        ```bash
        flask --app run run
        ```
    * The app should be accessible at `http://127.0.0.1:5000` (or `http://0.0.0.0:5000` depending on your setup).

## Usage

1.  **View Slideshow:** Access the root URL (e.g., `http://127.0.0.1:5000/`). Initially, it might show "No images uploaded."
2.  **Access Configuration:** Navigate to `/config` (e.g., `http://127.0.0.1:5000/config`).
3.  **Login:** Use the default credentials:
    * Username: `admin`
    * Password: `showgo`
4.  **Set Initial Password:** You will be prompted to change the default password immediately upon first login.
5.  **Configure:** Use the sidebar to navigate between "General Settings" and "Image Management". Upload images and adjust settings as desired.
6.  **Logout:** Use the "Logout" link in the sidebar.

## Contributing

(Optional: Add contribution guidelines if applicable)

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License - see the LICENSE.md file for details.
