# ShowGo - Web-Based Photo Slideshow Kiosk

ShowGo is a simple, self-hosted web application designed to display a configurable photo slideshow on a dedicated screen (like a TV connected to a PC, or even an old tablet, running a browser in kiosk mode). It provides a web interface for uploading images and configuring slideshow settings, widgets (time, weather, RSS), and watermarks.

Built with Python, Flask, Pillow, and Tailwind CSS. Designed to be deployed easily using Docker.

## Target Audience

Small businesses or individuals needing a simple, remotely manageable digital signage solution for photos. Also suitable for repurposing old Android/iOS tablets as dedicated photo frames or simple displays.

## Features

* Web-based slideshow view suitable for full-screen display on PCs or tablets.
* Password-protected web interface for configuration.
* Image uploading (multiple files) and management (view thumbnails, delete selected).
* Thumbnail generation for preview.
* Configurable slideshow settings:
    * Image display duration
    * Transition effects (currently fade)
    * Image order (sequential or random)
* Optional Widgets:
    * Current Time (updates every second)
    * Local Weather (via OpenWeatherMap or similar API - requires API key)
    * RSS Feed Headlines (cycles through recent headlines)
* Optional Watermark overlay (text) with configurable position and optional movement to prevent burn-in.
* Designed for Docker deployment (Phase 4).

## Project Status

* **Phase 1: Basic Setup & Core Backend (Complete)**
    * Project structure created.
    * Flask app initialized with basic routes.
    * Configuration loading/saving via `config.json`.
    * Basic HTTP Authentication added to `/config` route.
* **Phase 2: Configuration Interface Frontend (Complete)**
    * HTML structure for config page created (`config.html`).
    * Tailwind CSS integration.
    * Image upload form implemented.
    * Thumbnail display grid implemented.
    * Image deletion functionality implemented.
    * Forms for all slideshow, widget, and overlay settings implemented.
    * Configuration saving implemented.
* **Phase 3: Slideshow Display Page (Complete)**
    * Backend data preparation for slideshow (images, config, weather, RSS).
    * HTML structure for slideshow page created (`slideshow.html`).
    * Route for serving full-size uploaded images.
    * JavaScript logic for image cycling, transitions (fade), time widget updates, RSS cycling, and watermark display/movement.
* **Phase 4: Dockerization & Refinement (Complete)**
    * `requirements.txt` created.
    * `Dockerfile` created for building container image with Gunicorn.
    * `.dockerignore` file created.
* Phase 5: Refinements & Future Enhancements (Next)

## Setup & Running (Development)

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/puckawayjeff/showgo.git](https://github.com/puckawayjeff/showgo.git)
    cd showgo
    ```
2.  **Create and activate a Python virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
    *(Note: The `venv` directory should not be committed to Git. Ensure it's listed in your `.gitignore` file.)*

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **(Optional) Configure API Keys/Feeds:** Edit `config/config.json` (created on first run) to add your OpenWeatherMap API key or change the default RSS feed URL if desired.

5.  **Run the Flask development server:**
    ```bash
    python app.py
    ```
6.  Access the application in your browser:
    * Slideshow Viewer: `http://<your-ip>:5000/`
    * Config Page: `http://<your-ip>:5000/config` (Requires authentication - default: `admin`/`password`)

## Running with Docker (Recommended for Deployment)

1.  **Build the Docker image:**
    ```bash
    docker build -t showgo-app .
    ```
2.  **Run the Docker container:**
    ```bash
    docker run -d \
      -p 5000:5000 \
      --name showgo-instance \
      -v ./config:/app/config \
      -v ./uploads:/app/uploads \
      -v ./thumbnails:/app/thumbnails \
      showgo-app
    ```
    * This maps the host ports and mounts local directories for configuration and image persistence.

## Deployment Notes

* When deploying to production, use a proper WSGI server like Gunicorn or uWSGI (included in Dockerfile).
* If using a reverse proxy like Nginx in front of the container, ensure it is configured to handle large request bodies if large batch uploads are expected (e.g., `client_max_body_size` in Nginx).
* **Security:** Change the default admin password. Move sensitive credentials (auth, API keys) out of `config.json` and into environment variables or a more secure configuration management system. Set a strong, random `app.secret_key`.
* For tablet displays, use a kiosk browser app or the device's built-in guided access/screen pinning features for a full-screen experience. Ensure display sleep settings are disabled.

## Future Enhancements (Planned Long-Term Goals)

1.  **Video Support:**
    * Allow uploading common video formats (MP4, WebM).
    * Add configuration options to mute video audio or select media type (photos, videos, both).
    * Implement video playback using the HTML5 `<video>` tag in the slideshow.
    * Handle transitions after video completion.
2.  **Night Mode:**
    * Add option to dim the display during specific hours.
    * Configure schedule manually (start/end times) or automatically based on local sunset/sunrise (requires location).
    * Implement dimming using a CSS overlay with configurable opacity.
3.  **Collections / Tagging:**
    * Implement a database (e.g., SQLite) to store image metadata and collection assignments.
    * Add UI in the config page to create/manage collections and tag uploaded images.
    * Create dynamic routes (e.g., `/collection/<id>`) to display slideshows containing only images from a specific collection.
    * Allow multiple displays to show different collections from the same ShowGo instance.
4.  **Refinements:**
    * Improve UI/UX (loading indicators, better feedback).
    * Add more slideshow transition options.
    * Enhance error handling and logging.
    * Implement password changing functionality.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). See the [LICENSE.md](LICENSE.md) file for details.
