# Dockerfile for ShowGo Flask Application

# Use an official Python runtime as a parent image
# Choose a specific version for reproducibility (e.g., 3.11-slim)
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed system dependencies (if any - Pillow might need some)
# Example for Debian/Ubuntu based images (like python:3.11-slim):
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libjpeg-dev zlib1g-dev \
#  && rm -rf /var/lib/apt/lists/*
# Note: Check Pillow documentation for specific OS dependencies if needed.
# For simplicity, we'll try without extra system deps first.

# Install Python dependencies specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn (Production WSGI Server)
RUN pip install --no-cache-dir gunicorn

# Copy the rest of the application code into the container at /app
# This includes app.py, static/, templates/, config/ (initially)
# Make sure .dockerignore excludes venv, uploads, thumbnails etc. if needed
COPY . .

# Ensure necessary directories exist within the container image
# Although they might be mounted as volumes later, creating them ensures they exist
# if volumes aren't mounted immediately or for initial setup.
# Note: UPLOAD_FOLDER, THUMBNAIL_FOLDER, CONFIG_FOLDER are defined relative
# to BASE_DIR in app.py, which is /app here.
RUN mkdir -p /app/uploads && \
    mkdir -p /app/thumbnails && \
    mkdir -p /app/config

# Make port 5000 available to the world outside this container
# (Gunicorn will bind to this port inside the container)
EXPOSE 5000

# Define environment variables (optional but good practice)
ENV FLASK_APP=app.py
# Add any other environment variables needed, e.g., for secrets later

# Command to run the application using Gunicorn
# -w 4: Use 4 worker processes (adjust based on server resources)
# -b 0.0.0.0:5000: Bind to all network interfaces on port 5000
# app:app : Look for the Flask app instance named 'app' in the 'app.py' module
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

