# **ShowGo - Web-Based Slideshow Kiosk**

ShowGo is a self-hosted, web-based photo and video slideshow application designed for digital signage or personal use. It allows users to upload media and configure various display options through a web interface.

**License:** Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) - See LICENSE.md.

## **Features**

* **Web-Based Configuration:** Manage all settings through a password-protected web UI (`/config`).  
* **Media Upload & Management:**  
  * Upload multiple images (JPG, PNG, GIF, WEBP) and videos (MP4, WEBM, OGG).  
  * **Video Codec Validation:** Uploaded videos are checked for web-friendly codecs (H.264, VP9, AV1 for video; AAC, Opus, MP3, Vorbis for audio).  
  * View thumbnails for images and videos (video thumbnails generated using `ffmpeg` from ~10% mark).  
  * Delete media items.  
* **Slideshow Display:** View the configured slideshow at the root URL (`/`).  
* **Customizable Display:**  
  * Set image display duration.  
  * Choose image transition effects (`fade`, `slide`, `kenburns`).  
  * Configure video playback (scaling, autoplay, loop, mute, controls).  
  * Choose media order (sequential or random).  
  * Select image/video scaling (`cover` or `contain`).  
  * **Overlay Branding:**  
    * Display custom text and/or an uploaded logo (PNG).  
    * Configurable position, font size, font color, background color, and padding.  
    * Multiple display modes (text only, logo only, logo & text side-by-side, logo above text).  
* **Widgets:**  
  * Digital Clock  
  * Weather display (requires free OpenWeatherMap API key)  
  * RSS feed ticker (configurable URL and scroll speed)  
* **Display Protection:**  
  * Optional burn-in prevention (slight pixel shift for static elements, including overlay).  
* **Error Handling & Robustness:**  
  * Custom pages for 404 (Not Found) and 500 (Server Error).  
  * Silent failure for Weather/RSS widgets (errors logged to console).  
  * Automatic creation of necessary folders (`instance`, `uploads`, `thumbnails`, `static/assets`).  
  * Client-side caching for media files to reduce bandwidth.  
  * Slideshow automatically reloads if configuration or media library changes.  
* **Filesystem Validation:** Detects and allows cleanup of missing media files or orphaned files/thumbnails via the config UI.  
* **Database Self-Healing:** Attempts to recreate missing tables (`settings`, `media_files`) on startup or during operation.  
* **Environment Variable Configuration:** Key settings (secret key, API keys) are managed via a `.env` file.  
* **Application Factory Pattern & Blueprints:** Structured and modular codebase.  
* **SQLite Database:** Uses a simple, file-based SQLite database for easy setup and deployment.

## **Project Structure**

```bash
your_project_root/  
├── run.py             # Main script to run the Flask development server  
├── .env               # Environment variables (SECRET_KEY, API keys) - CREATE THIS  
├── requirements.txt   # Python dependencies  
├── instance/          # Instance folder (created automatically)  
│   └── showgo.db      # SQLite database file (created automatically)  
├── uploads/           # Media uploads (created automatically)  
├── thumbnails/        # Media thumbnails (created automatically)  
└── showgo/            # Main application package  
    ├── __init__.py    # App factory (create_app)  
    ├── config.py      # Configuration classes & Default Settings  
    ├── extensions.py  # Flask extension instances (db, auth)  
    ├── models.py      # SQLAlchemy models (Setting, MediaFile)  
    ├── utils.py       # Helper functions (DB init, validation, ffmpeg, etc.)  
    ├── cli.py         # CLI commands (init-db)  
    ├── main_bp.py     # Blueprint for main routes (/, /uploads, /api)  
    ├── config_bp.py   # Blueprint for config routes (/config/*, /logout)  
    ├── errors.py      # Error handler functions  
    ├── static/        # Static files (CSS, JS, placeholder images)  
    │   ├── assets/    # For uploaded assets like overlay_logo.png (created automatically)  
    │   │   └── overlay_logo.png # Example, created on upload  
    │   ├── css/  
    │   │   └── config_styles.css  
    │   ├── js/  
    │   │   └── slideshow.js  
    │   └── images/  
    │       └── placeholder_thumb.png  
    └── templates/     # HTML Templates  
        ├── config_base.html  
        ├── config_general.html  
        ├── config_media.html  
        ├── config_initial_password.html  
        ├── slideshow.html  
        ├── logout.html  
        ├── 404.html  
        └── 500.html
```

## **Setup and Installation**

1. **Prerequisites:**  
    * Python 3.x  
    * `pip` (Python package installer)  
    * `ffmpeg` and `ffprobe`: These must be installed on your system and accessible in the system's PATH for video thumbnail generation and codec validation.  
        * On Linux: `sudo apt update && sudo apt install ffmpeg`  
        * On Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add the `bin` folder to your system PATH.  
        * On macOS: `brew install ffmpeg`

2. **Clone the Repository:**  

    ```git
    git clone <repository_url>
    cd showgo
    ```

3. **Create a Virtual Environment:**  

    ```python
    python -m venv venv  
    # Activate the environment  
    # Windows:  
    .\venv\Scripts\activate  
    # Linux/macOS:
    source venv/bin/activate
    ```

4. **Install Dependencies:**  

    ```python
    pip install -r requirements.txt
    ```

5. **Configure Environment Variables:**
    * Create a file named `.env` in the project root directory (where `run.py` is).
    * Add the following variables, replacing the placeholder values:

        ```bash
        # Flask Secret Key (generate a strong random key)  
        SECRET_KEY='your_strong_random_secret_key'
        
        # OpenWeatherMap API Key (Optional, for weather widget)  
        # Get a free key from https://openweathermap.org/
        OPENWEATHERMAP_API_KEY='your_openweathermap_api_key'  
        ```

6. **Initialize Database (Optional but Recommended):**  
    * While the application attempts to create the database and tables automatically on first run, you can initialize it manually using the Flask CLI:

        ```bash
        flask db init
        ```

    * This will create the `instance/showgo.db` file and the necessary tables if they don't exist.

## **Running the Application**

1. **Activate Virtual Environment** (if not already active).  
2. **Run the Development Server:**  

    ```bash
    flask --app run run
    ```

    * The app should be accessible at `http://127.0.0.1:5000` (or `http://0.0.0.0:5000`).  
    * The SQLite database file (`instance/showgo.db`) and other necessary folders (`uploads`, `thumbnails`, `static/assets`) will be created automatically if they don't exist.

## **Usage**

1. **View Slideshow:** Access the root URL (e.g., `http://127.0.0.1:5000/`).  
2. **Access Configuration:** Navigate to `/config` (e.g., `http://127.0.0.1:5000/config`).  
3. **Login:** Use the default credentials:  
    * Username: `admin`  
    * Password: `showgo`  
4. **Set Initial Password:** You will be prompted to change the default password immediately upon first login.  
5. **Configure:** Use the sidebar to navigate between "General Settings" and "Media Management". Upload images/videos and adjust settings as desired.  
6. **Logout:** Use the "Logout" link in the sidebar.

## **Contributing**

TBD. Not currently open to contributors or even expecting any interest at this point.

## **License**

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License - see the LICENSE.md file for details.
