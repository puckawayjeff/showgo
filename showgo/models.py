# showgo/models.py

import os
from .extensions import db # Import db instance from extensions
from datetime import datetime, timezone
from flask import current_app # Use current_app to access config

class Setting(db.Model):
    """Represents a configuration setting stored in the database."""
    __tablename__ = 'settings'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Setting {self.key}>'

# *** Class Renamed from ImageFile to MediaFile ***
class MediaFile(db.Model):
    """Represents an uploaded media file (image or video)."""
    # *** Table Renamed for clarity ***
    __tablename__ = 'media_files'
    id = db.Column(db.Integer, primary_key=True)
    uuid_filename = db.Column(db.String(36), unique=True, nullable=False) # UUID part without extension
    original_filename = db.Column(db.String(255), nullable=False) # Original uploaded filename
    display_name = db.Column(db.String(255), nullable=False) # User-editable name (defaults to original)
    extension = db.Column(db.String(10), nullable=False) # File extension (e.g., 'jpg', 'mp4')
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # *** ADDED media_type field ***
    media_type = db.Column(db.String(10), nullable=False, default='image') # Stores 'image' or 'video'

    def get_disk_filename(self):
        """Returns the full filename used on disk (uuid + extension)."""
        return f"{self.uuid_filename}.{self.extension}"

    def get_thumbnail_filename(self):
        """
        Returns the expected thumbnail filename used on disk (uuid + configured thumb ext).
        Note: Actual thumbnail generation might fail for videos without specific libraries.
        """
        # Use current_app safely to access config
        thumb_ext = '.png' # Default
        if current_app:
            thumb_ext = current_app.config.get('THUMBNAIL_EXT', '.png')
        return f"{self.uuid_filename}{thumb_ext}"

    def get_upload_path(self):
        """Returns the full absolute path to the original uploaded file."""
        # Use current_app safely to access config
        upload_folder = './uploads' # Default
        if current_app:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', './uploads')
        return os.path.join(os.path.abspath(upload_folder), self.get_disk_filename())

    def get_thumbnail_path(self):
        """Returns the full absolute path to the thumbnail file."""
         # Use current_app safely to access config
        thumbnail_folder = './thumbnails' # Default
        if current_app:
            thumbnail_folder = current_app.config.get('THUMBNAIL_FOLDER', './thumbnails')
        return os.path.join(os.path.abspath(thumbnail_folder), self.get_thumbnail_filename())

    def check_files_exist(self):
        """
        Checks if the original media file exists on disk.
        Thumbnail check is optional here as it might not exist for videos yet.
        """
        return os.path.isfile(self.get_upload_path())

    def __repr__(self):
        return f'<MediaFile {self.id}: {self.display_name} ({self.get_disk_filename()}) Type: {self.media_type}>'

