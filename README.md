# ShowGo - Web-Based Photo Slideshow Kiosk

ShowGo is a simple, self-hosted web application designed to display a configurable photo slideshow on a dedicated screen (like a TV connected to a PC, or even an old tablet, running a browser in kiosk mode). It provides a web interface for uploading images and configuring slideshow settings, widgets (time, weather, RSS), and watermarks.

Built with Python, Flask, Pillow, SQLAlchemy, and Tailwind CSS. Designed to be deployed easily using Docker.

## Target Audience

Small businesses or individuals needing a simple, remotely manageable digital signage solution for photos. Also suitable for repurposing old Android/iOS tablets as dedicated photo frames or simple displays.

## Features

* Web-based slideshow view suitable for full-screen display on PCs or tablets.
* Password-protected web interface for configuration (dark mode theme).
* Forced default password change on first login.
* Image uploading (multiple files) using UUIDs for storage filenames.
* Database storage (MySQL) for configuration and image metadata (display names, etc.).
* Image management (view thumbnails with display names, delete selected).
* Thumbnail generation for preview.
* Configurable slideshow settings:
  * Image display duration
  * Transition effects (currently fade)
  * Image order (sequential or random)
  * Image scaling ('Fill'/'cover' or 'Fit'/'contain')
* Optional Widgets:
  * Current Time (updates every second)
  * Local Weather (via OpenWeatherMap or similar API - requires API key)
  * RSS Feed Ticker (scrolls recent headlines)
* Optional Watermark overlay (text) with configurable position.
* Optional screen burn-in prevention (pixel shifting) for configurable static elements.
* Slideshow auto-reloads when configuration is changed remotely.
* Fullscreen toggle via double-tap (touch), double-click (mouse), or Enter key.
* Cursor hidden when in fullscreen; text selection disabled on slideshow page.
* Docker container for easy deployment.

## Project Status

* **Phase 1: Basic Setup & Core Backend (Complete)**
  * Project structure created.
  * Flask app initialized with basic routes.
  * MySQL database integration via Flask-SQLAlchemy.
  * Database models for Settings and ImageFiles.
  * Configuration loading/saving via database.
  * Basic HTTP Authentication implemented.
  * `flask init-db` command for setup.
* **Phase 2: Configuration Interface Frontend (Complete)**
  * HTML structure for config page created (`config.html`).
  * Tailwind CSS integration (including dark mode).
  * Image upload form using UUIDs and DB storage.
  * Thumbnail display grid using display names from DB.
  * Image deletion functionality (updates DB and removes files).
  * Forms for all slideshow, widget, and overlay settings (save to DB).
  * Forced password change workflow and subsequent update form.
* **Phase 3: Slideshow Display Page (Complete)**
  * Backend data preparation for slideshow (images from DB, config from DB, weather, RSS).
  * HTML structure for slideshow page created (`slideshow.html`).
  * Routes for serving full-size (UUID) and thumbnail (UUID) images.
  * JavaScript logic for image cycling, transitions, scaling, widget updates (time, RSS ticker), watermark display, pixel shifting, fullscreen toggles, cursor hiding, text selection disabling, and config polling/reload.
* **Phase 4: Dockerization & Refinement (Complete)**
  * `requirements.txt` created.
  * `Dockerfile` created for building container image with Gunicorn.
  * `.dockerignore` file created.
* Phase 5: Refinements & Future Enhancements (Next)

## Setup & Running (Development)

1. **Prerequisites:**
    * Python 3.x
    * MySQL Server (running and accessible)
    * Git
2. **Clone the repository:**

    ```bash
    git clone [https://github.com/puckawayjeff/showgo.git](https://github.com/puckawayjeff/showgo.git)
    cd showgo
    ```

3. **Create and activate a Python virtual environment:**

    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

4. **Configure Database Connection:**
    * Set environment variables for your MySQL connection (used by `app.py`):
        * `DB_USER` (e.g., `showgo_user`)
        * `DB_PASSWORD` (e.g., `showgo_pass`)
        * `DB_HOST` (e.g., `localhost` or `10.0.0.244`)
        * `DB_NAME` (e.g., `showgo_db`)
        * `SECRET_KEY` (set to a long, random string for session security)
    * Ensure the specified database exists on your MySQL server.
5. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

6. **Initialize the Database:**
    * Run the Flask command to create tables and populate default settings:

        ```bash
        flask init-db
        ```

7. **(Optional) Configure API Keys:** Log in to the config page (`/config`) after the first run and add your OpenWeatherMap API key in the settings if you want to use the weather widget.

8. **Run the Flask development server:**

    ```bash
    python app.py
    ```

9. Access the application in your browser:
    * Slideshow Viewer: `http://<your-ip>:5000/`
    * Config Page: `http://<your-ip>:5000/config` (First login: `admin`/`showgo`, forces password change)

## Running with Docker (Recommended for Deployment)

1. **Build the Docker image:**

    ```bash
    docker build -t showgo-app .
    ```

2. **Run the Docker container:**
    * You **must** provide the database connection details and a secret key as environment variables to the container.
    * Mount volumes for persistent storage.

    ```bash
    docker run -d \
      -p 5000:5000 \
      --name showgo-instance \
      -v ./uploads:/app/uploads \
      -v ./thumbnails:/app/thumbnails \
      -e DB_USER="your_db_user" \
      -e DB_PASSWORD="your_db_password" \
      -e DB_HOST="your_db_host_accessible_from_docker" \
      -e DB_NAME="your_db_name" \
      -e SECRET_KEY="your_strong_random_secret_key" \
      showgo-app
    ```

    * **Note:** The container needs access to the MySQL database specified by `DB_HOST`. If running MySQL in another Docker container, use Docker networking. If running on the host, `host.docker.internal` might work as the host address on some systems.
    * The first time you run the container against an empty database, you need to initialize it: `docker exec showgo-instance flask init-db`.

## Deployment Notes

* Always use a proper WSGI server like Gunicorn (included in Dockerfile).
* Use a reverse proxy (e.g., Nginx) in front of the application/container for production (handling HTTPS, static files, request buffering). Configure `client_max_body_size` in the proxy if large uploads are needed.
* **Security:** Use strong passwords. Manage `SECRET_KEY` and database credentials securely via environment variables or a secrets management system.
* For tablet displays, use a kiosk browser app or guided access/screen pinning. Disable display sleep.

## Future Enhancements (Planned Goals)

1. **Video Support:** Upload/playback, mute option, media type selection.
2. **Night Mode:** Configurable screen dimming schedule (manual/auto).
3. **Collections / Tagging:** Database support, UI for management, `/collections` index, `/collection/<id>` routes.
4. **External Sources Integration:** Explore Google Drive, etc. (complex).
5. **WebSockets:** Real-time client telemetry and control (blank screen, announcements, remote collection changes).
6. **Refinements:** UI/UX improvements, more transitions, better error handling/logging, config via environment variables.
7. **(Potential) Hosted SaaS Version:** Explore commercial multi-tenant offering.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). See the [LICENSE.md](LICENSE.md) file for details.
