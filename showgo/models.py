# showgo/models.py

import os # *** ADDED os import ***
from .extensions import db # Import db instance from extensions
from datetime import datetime, timezone
from flask import current_app # Use current_app to access config

class Setting(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Setting {self.key}>'

class ImageFile(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    uuid_filename = db.Column(db.String(36), unique=True, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    extension = db.Column(db.String(10), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def get_disk_filename(self):
        """Returns the filename used on disk (uuid + extension)."""
        return f"{self.uuid_filename}.{self.extension}"

    def get_thumbnail_filename(self):
        """Returns the thumbnail filename used on disk (uuid + .png)."""
        # Access config via current_app proxy
        thumb_ext = current_app.config.get('THUMBNAIL_EXT', '.png')
        return f"{self.uuid_filename}{thumb_ext}"

    def get_upload_path(self):
        """Returns the full path to the original uploaded file."""
        upload_folder = current_app.config.get('UPLOAD_FOLDER', './uploads') # Provide default
        # Use the imported os module
        return os.path.join(upload_folder, self.get_disk_filename())

    def get_thumbnail_path(self):
        """Returns the full path to the thumbnail file."""
        thumbnail_folder = current_app.config.get('THUMBNAIL_FOLDER', './thumbnails') # Provide default
        # Use the imported os module
        return os.path.join(thumbnail_folder, self.get_thumbnail_filename())

    def check_files_exist(self):
        """Checks if both original and thumbnail files exist on disk."""
        # Use the imported os module
        return os.path.isfile(self.get_upload_path()) and os.path.isfile(self.get_thumbnail_path())

    def __repr__(self):
        return f'<ImageFile {self.id}: {self.display_name} ({self.get_disk_filename()})>'

