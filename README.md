# **ShowGo \- Web-Based Photo Slideshow Kiosk**

ShowGo is a simple, self-hosted web application designed to display a configurable photo slideshow on a dedicated screen (like a TV connected to a PC running a browser in kiosk mode). It provides a web interface for uploading images and configuring slideshow settings, widgets (time, weather, RSS), and watermarks.

Built with Python, Flask, and Tailwind CSS. Designed to be deployed easily using Docker.

## **Target Audience**

Small businesses (like print shops, cafes, lobbies) or individuals needing a simple, remotely manageable digital signage solution for photos.

## **Features (Planned)**

* Web-based slideshow view suitable for full-screen display.  
* Password-protected web interface for configuration.  
* Image uploading and management (view thumbnails, delete).  
* Configurable slideshow settings:  
  * Image display duration  
  * Transition effects (starting with fade)  
  * Image order (sequential or random)  
* Optional Widgets:  
  * Current Time  
  * Local Weather (via OpenWeatherMap or similar API)  
  * RSS Feed Headlines  
* Optional Watermark overlay (text or image) with movement to prevent burn-in.  
* Docker container for easy deployment.

## **Project Status**

* **Phase 1: Basic Setup & Core Backend (Complete)**  
  * Project structure created.  
  * Flask app initialized with basic routes.  
  * Configuration loading/saving via config.json.  
  * Basic HTTP Authentication added to /config route.  
* Phase 2: Configuration Interface Frontend (Next)

## **Setup & Running (Development)**

1. **Clone the repository:**  
   git clone https://github.com/puckawayjeff/showgo.git  
   cd showgo

2. **Create and activate a Python virtual environment:**  
   python \-m venv venv  
   \# Windows  
   venv\\Scripts\\activate  
   \# macOS/Linux  
   source venv/bin/activate

   *(Note: The venv directory should not be committed to Git. Ensure it's listed in your .gitignore file if you have one.)*  
3. **Install dependencies:**  
   pip install \-r requirements.txt

4. **Run the Flask development server:**  
   python app.py

5. Access the application in your browser:  
   * Slideshow Viewer: http://\<your-ip\>:5000/  
   * Config Page: http://\<your-ip\>:5000/config (Requires authentication \- default: admin/password)

*(More details on configuration and deployment will be added as the project progresses)*
