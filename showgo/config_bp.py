# showgo/config_bp.py
# Blueprint for configuration pages and actions

import os
import traceback
import uuid
from functools import wraps
from datetime import datetime, timezone # Import datetime and timezone
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, make_response, current_app)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge

# Import extensions, models, utils from the application package (.)
from .extensions import db, auth
from .models import MediaFile, Setting
from .utils import (get_setting, save_setting, initialize_database,
                    get_database_media, find_missing_media_files,
                    find_unexpected_items, cleanup_unexpected_items,
                    remove_missing_media_db_entries,
                    allowed_file, generate_thumbnail, get_media_type,
                    is_web_friendly_video)
from .config import DEFAULT_SETTINGS_DB # Import defaults for fallback

# Create Blueprint
config_bp = Blueprint('config_bp', __name__)

# --- Decorator ---
def check_password_changed(f):
    """Decorator to ensure the default password has been changed."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        password_changed = get_setting('auth_password_changed', False)
        if not password_changed:
            flash("Please change the default password before accessing configuration.", "warning")
            return redirect(url_for('config_bp.config_set_initial_password'))
        return f(*args, **kwargs)
    return decorated_function

# --- Helper to update media timestamp ---
def _touch_media_timestamp():
    """Updates the media_last_changed setting to the current time."""
    try:
        now_ts = datetime.now(timezone.utc).timestamp()
        save_setting('media_last_changed', now_ts)
    except Exception as e:
        print(f"ERROR: Failed to update media_last_changed timestamp: {e}")

# --- Helper to update general config timestamp (used by settings and logo upload) ---
def _touch_config_timestamp():
    """Touches a general configuration setting to update its last_updated timestamp."""
    try:
        current_value = get_setting('overlay_enabled', False)
        save_setting('overlay_enabled', current_value)
        print(f"Touched general config timestamp by re-saving 'overlay_enabled'.")
    except Exception as e:
        print(f"ERROR: Failed to touch general config timestamp: {e}")


# --- Routes ---

@config_bp.route('/')
@auth.login_required
def config_redirect():
    """Redirects base blueprint route to the general settings page."""
    return redirect(url_for('.config_general'))

@config_bp.route('/set-initial-password', methods=['GET', 'POST'])
@auth.login_required
def config_set_initial_password():
    # ... (content remains the same)
    if get_setting('auth_password_changed', False):
        flash("Password has already been set.", "info")
        return redirect(url_for('.config_general'))
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not new_password or not confirm_password:
            flash("New password fields are required.", "error")
            return redirect(url_for('.config_set_initial_password'))
        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "error")
            return redirect(url_for('.config_set_initial_password'))
        if new_password == "showgo":
            flash("New password cannot be the default password.", "error")
            return redirect(url_for('.config_set_initial_password'))
        try:
            new_hash = generate_password_hash(new_password)
            saved_hash = save_setting('auth_password_hash', new_hash)
            saved_flag = save_setting('auth_password_changed', True)
            if saved_hash and saved_flag:
                flash("Password set successfully! You can now configure ShowGo.", "success")
                return redirect(url_for('.config_general'))
            else:
                flash("Error saving new password configuration.", "error")
        except Exception as e:
            print(f"Error processing initial password change: {e}")
            traceback.print_exc()
            flash("An unexpected error occurred while changing the password.", "error")
        return redirect(url_for('.config_set_initial_password'))
    username = get_setting('auth_username', 'admin')
    return render_template('config_initial_password.html', username=username)


@config_bp.route('/general', methods=['GET', 'POST'])
@auth.login_required
@check_password_changed
def config_general():
    """Displays and handles saving of general slideshow/widget/display settings."""
    if request.method == 'POST':
        # ... (POST logic remains the same as the previous version) ...
        settings_saved_successfully = True
        try:
            # Slideshow General Settings
            allowed_transitions = ['fade', 'slide', 'kenburns']
            transition = request.form.get('transition_effect', DEFAULT_SETTINGS_DB['slideshow_transition_effect'])
            if transition not in allowed_transitions:
                flash(f"Invalid transition effect '{transition}'. Defaulting.", "warning")
                transition = DEFAULT_SETTINGS_DB['slideshow_transition_effect']
            settings_saved_successfully &= save_setting('slideshow_transition_effect', transition)
            settings_saved_successfully &= save_setting('slideshow_duration_seconds', int(request.form.get('duration_seconds', DEFAULT_SETTINGS_DB['slideshow_duration_seconds'])))
            settings_saved_successfully &= save_setting('slideshow_image_order', request.form.get('image_order', DEFAULT_SETTINGS_DB['slideshow_image_order']))
            settings_saved_successfully &= save_setting('slideshow_image_scaling', request.form.get('image_scaling', DEFAULT_SETTINGS_DB['slideshow_image_scaling']))
            # Video Settings
            settings_saved_successfully &= save_setting('slideshow_video_scaling', request.form.get('video_scaling', DEFAULT_SETTINGS_DB['slideshow_video_scaling']))
            settings_saved_successfully &= save_setting('slideshow_video_autoplay', 'video_autoplay' in request.form)
            settings_saved_successfully &= save_setting('slideshow_video_loop', 'video_loop' in request.form)
            settings_saved_successfully &= save_setting('slideshow_video_muted', 'video_muted' in request.form)
            settings_saved_successfully &= save_setting('slideshow_video_show_controls', 'video_show_controls' in request.form)
            # Overlay Branding Settings
            settings_saved_successfully &= save_setting('overlay_enabled', 'overlay_enabled' in request.form)
            settings_saved_successfully &= save_setting('overlay_text', request.form.get('overlay_text', DEFAULT_SETTINGS_DB['overlay_text']))
            settings_saved_successfully &= save_setting('overlay_position', request.form.get('overlay_position', DEFAULT_SETTINGS_DB['overlay_position']))
            settings_saved_successfully &= save_setting('overlay_font_size', request.form.get('overlay_font_size', DEFAULT_SETTINGS_DB['overlay_font_size']))
            settings_saved_successfully &= save_setting('overlay_font_color', request.form.get('overlay_font_color', DEFAULT_SETTINGS_DB['overlay_font_color']))
            settings_saved_successfully &= save_setting('overlay_logo_enabled', 'overlay_logo_enabled' in request.form)
            allowed_display_modes = ['text_only', 'logo_only', 'logo_and_text_side', 'logo_and_text_below']
            display_mode = request.form.get('overlay_display_mode', DEFAULT_SETTINGS_DB['overlay_display_mode'])
            if display_mode not in allowed_display_modes:
                display_mode = DEFAULT_SETTINGS_DB['overlay_display_mode']
            settings_saved_successfully &= save_setting('overlay_display_mode', display_mode)
            settings_saved_successfully &= save_setting('overlay_background_color', request.form.get('overlay_background_color', DEFAULT_SETTINGS_DB['overlay_background_color']))
            settings_saved_successfully &= save_setting('overlay_padding', request.form.get('overlay_padding', DEFAULT_SETTINGS_DB['overlay_padding']))
            # Widget Settings
            settings_saved_successfully &= save_setting('widgets_time_enabled', 'time_widget_enabled' in request.form)
            settings_saved_successfully &= save_setting('widgets_weather_enabled', 'weather_widget_enabled' in request.form)
            settings_saved_successfully &= save_setting('widgets_weather_location', request.form.get('weather_location', DEFAULT_SETTINGS_DB['widgets_weather_location']))
            settings_saved_successfully &= save_setting('widgets_rss_enabled', 'rss_widget_enabled' in request.form)
            settings_saved_successfully &= save_setting('widgets_rss_feed_url', request.form.get('rss_feed_url', DEFAULT_SETTINGS_DB['widgets_rss_feed_url']))
            allowed_speeds = ['slow', 'medium', 'fast']
            scroll_speed = request.form.get('rss_scroll_speed', DEFAULT_SETTINGS_DB['widgets_rss_scroll_speed'])
            if scroll_speed not in allowed_speeds:
                flash(f"Invalid RSS scroll speed '{scroll_speed}'. Defaulting.", "warning")
                scroll_speed = DEFAULT_SETTINGS_DB['widgets_rss_scroll_speed']
            settings_saved_successfully &= save_setting('widgets_rss_scroll_speed', scroll_speed)
            # Burn-in Settings
            settings_saved_successfully &= save_setting('burn_in_prevention_enabled', 'burn_in_prevention_enabled' in request.form)
            settings_saved_successfully &= save_setting('burn_in_prevention_elements', request.form.getlist('burn_in_elements'))
            settings_saved_successfully &= save_setting('burn_in_prevention_interval_seconds', int(request.form.get('burn_in_interval_seconds', DEFAULT_SETTINGS_DB['burn_in_prevention_interval_seconds'])))
            settings_saved_successfully &= save_setting('burn_in_prevention_strength_pixels', int(request.form.get('burn_in_strength_pixels', DEFAULT_SETTINGS_DB['burn_in_prevention_strength_pixels'])))

            if settings_saved_successfully:
                flash("Configuration saved successfully!", "success")
            else:
                flash("An error occurred while saving some settings. Check logs.", "error")
        except ValueError:
            flash("Invalid input value provided (e.g., duration, interval, strength must be numbers).", "error")
        except Exception as e:
            print(f"Error processing save settings request: {e}")
            traceback.print_exc()
            flash("An unexpected error occurred while saving settings.", "error")
        return redirect(url_for('.config_general'))

    # GET Request Logic
    defaults = DEFAULT_SETTINGS_DB
    # This current_config is for the form values (settings from DB)
    current_config_values = {
         "slideshow": {
             "duration_seconds": get_setting("slideshow_duration_seconds", defaults['slideshow_duration_seconds']),
             "transition_effect": get_setting("slideshow_transition_effect", defaults['slideshow_transition_effect']),
             "image_order": get_setting("slideshow_image_order", defaults['slideshow_image_order']),
             "image_scaling": get_setting("slideshow_image_scaling", defaults['slideshow_image_scaling']),
             "video_scaling": get_setting("slideshow_video_scaling", defaults['slideshow_video_scaling']),
             "video_autoplay": get_setting("slideshow_video_autoplay", defaults['slideshow_video_autoplay']),
             "video_loop": get_setting("slideshow_video_loop", defaults['slideshow_video_loop']),
             "video_muted": get_setting("slideshow_video_muted", defaults['slideshow_video_muted']),
             "video_show_controls": get_setting("slideshow_video_show_controls", defaults['slideshow_video_show_controls']),
         },
         "overlay": {
             "enabled": get_setting("overlay_enabled", defaults['overlay_enabled']),
             "text": get_setting("overlay_text", defaults['overlay_text']),
             "position": get_setting("overlay_position", defaults['overlay_position']),
             "font_size": get_setting("overlay_font_size", defaults['overlay_font_size']),
             "font_color": get_setting("overlay_font_color", defaults['overlay_font_color']),
             "logo_enabled": get_setting("overlay_logo_enabled", defaults['overlay_logo_enabled']),
             "display_mode": get_setting("overlay_display_mode", defaults['overlay_display_mode']),
             "background_color": get_setting("overlay_background_color", defaults['overlay_background_color']),
             "padding": get_setting("overlay_padding", defaults['overlay_padding']),
         },
         "widgets": {
             "time": {"enabled": get_setting("widgets_time_enabled", defaults['widgets_time_enabled'])},
             "weather": { "enabled": get_setting("widgets_weather_enabled", defaults['widgets_weather_enabled']), "location": get_setting("widgets_weather_location", defaults['widgets_weather_location']) },
             "rss": { "enabled": get_setting("widgets_rss_enabled", defaults['widgets_rss_enabled']), "feed_url": get_setting("widgets_rss_feed_url", defaults['widgets_rss_feed_url']), "scroll_speed": get_setting("widgets_rss_scroll_speed", defaults['widgets_rss_scroll_speed']) }
         },
         "burn_in_prevention": {
             "enabled": get_setting("burn_in_prevention_enabled", defaults['burn_in_prevention_enabled']),
             "elements": get_setting("burn_in_prevention_elements", defaults['burn_in_prevention_elements']),
             "interval_seconds": get_setting("burn_in_prevention_interval_seconds", defaults['burn_in_prevention_interval_seconds']),
             "strength_pixels": get_setting("burn_in_prevention_strength_pixels", defaults['burn_in_prevention_strength_pixels'])
         },
    }
    logo_path = os.path.join(current_app.config['ASSETS_FOLDER'], current_app.config['OVERLAY_LOGO_FILENAME'])
    logo_exists = os.path.isfile(logo_path)

    return render_template('config_general.html',
                           settings=current_config_values, # Pass settings values under 'settings'
                           logo_exists=logo_exists,
                           # Pass the app config value for OVERLAY_LOGO_FILENAME explicitly
                           APP_CONFIG_OVERLAY_LOGO_FILENAME=current_app.config['OVERLAY_LOGO_FILENAME'],
                           active_page='general')

@config_bp.route('/upload_overlay_logo', methods=['POST'])
@auth.login_required
@check_password_changed
def upload_overlay_logo():
    # ... (content remains the same)
    if 'overlay_logo_file' not in request.files:
        flash('No logo file part in the request.', 'error')
        return redirect(url_for('.config_general'))
    file = request.files['overlay_logo_file']
    if file.filename == '':
        flash('No selected logo file.', 'error')
        return redirect(url_for('.config_general'))
    if file and file.filename.rsplit('.', 1)[1].lower() == 'png':
        filename = current_app.config['OVERLAY_LOGO_FILENAME']
        assets_folder = current_app.config['ASSETS_FOLDER']
        save_path = os.path.join(assets_folder, filename)
        try:
            os.makedirs(assets_folder, exist_ok=True)
            file.save(save_path)
            flash('Overlay logo uploaded successfully!', 'success')
            _touch_config_timestamp()
        except Exception as e:
            print(f"Error saving overlay logo: {e}")
            traceback.print_exc()
            flash('Error saving overlay logo.', 'error')
    else:
        flash('Invalid file type for logo. Please upload a PNG file.', 'error')
    return redirect(url_for('.config_general'))

# (config_media, upload_media, delete_media, cleanup routes, update_password, logout remain unchanged)
# ... (rest of the routes from previous version) ...
@config_bp.route('/media')
@auth.login_required
@check_password_changed
def config_media():
    all_db_media, db_uuids = get_database_media()
    missing_db_entries = find_missing_media_files(all_db_media)
    orphaned_uuid_files, unexpected_files, unexpected_dirs = find_unexpected_items(db_uuids)
    displayable_media = [media for media in all_db_media if media not in missing_db_entries]
    displayable_media.sort(key=lambda media: media.uploaded_at, reverse=True)
    return render_template('config_media.html',
                           media_items=displayable_media,
                           missing_db_entries=missing_db_entries,
                           orphaned_uuid_files=orphaned_uuid_files,
                           unexpected_files=unexpected_files,
                           unexpected_dirs=unexpected_dirs,
                           active_page='media')

@config_bp.route('/upload', methods=['POST'])
@auth.login_required
@check_password_changed
def upload_media():
    pil_available = current_app.config.get('PIL_AVAILABLE', False)
    upload_folder = current_app.config['UPLOAD_FOLDER']
    thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
    thumbnail_size = current_app.config.get('THUMBNAIL_SIZE', (150, 150))
    thumbnail_format = current_app.config.get('THUMBNAIL_FORMAT', 'PNG')
    thumbnail_ext = f".{thumbnail_format.lower()}"
    max_size_mb = current_app.config.get('MAX_CONTENT_LENGTH', 512*1024*1024) // 1024 // 1024
    if not pil_available:
        flash("Warning: Image processing library (Pillow) not installed. Cannot generate image thumbnails.", "warning")
    if 'media_files' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('.config_media'))
    files = request.files.getlist('media_files')
    uploaded_count = 0; error_count = 0; thumb_error_count = 0; media_changed = False
    if not files or files[0].filename == '':
        flash('No selected file.', 'error')
        return redirect(url_for('.config_media'))
    for file in files:
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower()
            uuid_hex = uuid.uuid4().hex
            disk_filename = f"{uuid_hex}.{file_ext}"
            save_path = os.path.join(upload_folder, disk_filename)
            media_type = get_media_type(original_filename)
            if not media_type:
                flash(f"File type not recognized for {original_filename}.", "error")
                error_count += 1
                continue
            try:
                file.save(save_path)
                if media_type == 'video':
                    if not is_web_friendly_video(save_path):
                        flash(f"Video '{original_filename}' contains unsupported video or audio formats and was not added. Please use common web formats (e.g., H.264/AAC in MP4).", "error")
                        error_count += 1
                        if os.path.exists(save_path):
                            try: os.remove(save_path)
                            except OSError as e: print(f"Error cleaning up rejected video file {save_path}: {e}")
                        continue
                thumb_disk_filename = f"{uuid_hex}{thumbnail_ext}"
                thumb_dest_path = os.path.join(thumbnail_folder, thumb_disk_filename)
                thumb_success, _ = generate_thumbnail(save_path, thumb_dest_path, thumbnail_size, media_type)
                if not thumb_success:
                    if media_type == 'image':
                        thumb_error_count += 1
                        print(f"Warning: Failed to generate thumbnail for image {original_filename}")
                    elif media_type == 'video':
                        print(f"Info: Failed to generate thumbnail for video {original_filename} (ffmpeg issue or unsupported format for thumbnailing).")
                display_name_default = os.path.splitext(original_filename)[0]
                new_media = MediaFile(uuid_filename=uuid_hex, original_filename=original_filename, display_name=display_name_default, extension=file_ext, media_type=media_type)
                db.session.add(new_media)
                db.session.commit()
                uploaded_count += 1
                media_changed = True
            except RequestEntityTooLarge as e:
                print(f"Upload failed for {original_filename}: {e}")
                db.session.rollback()
                if os.path.exists(save_path):
                    try: os.remove(save_path)
                    except OSError: pass
                error_count +=1
                break
            except Exception as e:
                print(f"Error processing file {original_filename}: {e}")
                traceback.print_exc()
                flash(f'Error processing file {original_filename}.', 'error')
                error_count += 1
                db.session.rollback()
                if os.path.exists(save_path):
                    try: os.remove(save_path)
                    except OSError: pass
        elif file and file.filename != '':
            flash(f'File type not allowed for {secure_filename(file.filename)}.', 'error')
            error_count += 1
    if media_changed:
        _touch_media_timestamp()
    if uploaded_count > 0:
        flash(f'Successfully processed and added {uploaded_count} media file(s).', 'success')
    if thumb_error_count > 0:
        flash(f'Failed to generate thumbnails for {thumb_error_count} image(s). Check logs.', 'warning')
    if error_count > 0:
        flash(f'Failed to upload or process {error_count} file(s). See messages above or check logs for details.', 'error')
    return redirect(url_for('.config_media'))

@config_bp.route('/delete', methods=['POST'])
@auth.login_required
@check_password_changed
def delete_media():
    media_ids_to_delete = request.form.getlist('selected_media')
    deleted_count = 0; error_count = 0; media_changed = False
    if not media_ids_to_delete: flash("No media selected for deletion.", "warning"); return redirect(url_for('.config_media'))
    upload_folder = current_app.config['UPLOAD_FOLDER']; thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
    for media_id in media_ids_to_delete:
        try:
            media_id_int = int(media_id); media_record = db.session.get(MediaFile, media_id_int)
            if media_record:
                disk_filename = media_record.get_disk_filename(); thumbnail_filename = media_record.get_thumbnail_filename(); original_path = os.path.join(upload_folder, disk_filename); thumbnail_path = os.path.join(thumbnail_folder, thumbnail_filename)
                try:
                    if os.path.isfile(original_path): os.remove(original_path)
                    else: print(f"Warning: Original file not found during deletion: {original_path}")
                    if os.path.isfile(thumbnail_path): os.remove(thumbnail_path)
                except OSError as e: print(f"Error deleting files for media ID {media_id}: {e}"); flash(f"Error deleting files for '{media_record.display_name}', removing DB record anyway.", "warning")
                db.session.delete(media_record); deleted_count += 1; media_changed = True
            else: print(f"Media record not found in DB for ID: {media_id}"); error_count += 1
        except ValueError: print(f"Invalid media ID received: {media_id}"); error_count += 1
        except Exception as e: print(f"Error processing deletion for media ID {media_id}: {e}"); traceback.print_exc(); error_count += 1; db.session.rollback()
    try:
        if media_changed: db.session.commit(); _touch_media_timestamp()
        else: print("No media records found to delete, skipping commit and timestamp update.")
    except Exception as e: print(f"Error committing deletions to DB: {e}"); traceback.print_exc(); flash("Database error during deletion commit.", "error"); db.session.rollback(); deleted_count = 0; error_count = len(media_ids_to_delete); media_changed=False
    if deleted_count > 0: flash(f"Successfully deleted {deleted_count} media file(s).", "success")
    if error_count > 0: flash(f"Error occurred while deleting {error_count} media file(s). Check logs.", "error")
    return redirect(url_for('.config_media'))

@config_bp.route('/cleanup/missing-db', methods=['POST'])
@auth.login_required
@check_password_changed
def cleanup_missing_media_db_route():
    media_ids = request.form.getlist('missing_media_ids')
    if not media_ids: flash("No missing media entries selected for removal.", "warning"); return redirect(url_for('.config_media'))
    print(f"Attempting to remove DB entries for missing media IDs: {media_ids}")
    deleted_count, error_count = remove_missing_media_db_entries(media_ids)
    if deleted_count > 0 and error_count == 0 : _touch_media_timestamp()
    elif deleted_count > 0: print("Partial success removing missing DB entries, timestamp likely updated.")
    if error_count > 0: flash(f"Removed {deleted_count} missing database entries, but encountered errors with {error_count} entries. Check logs.", "error")
    elif deleted_count > 0: flash(f"Successfully removed {deleted_count} database entries for missing media.", "success")
    else: flash("No database entries were removed (perhaps they were already gone?).", "info")
    return redirect(url_for('.config_media'))

@config_bp.route('/cleanup/unexpected-items', methods=['POST'])
@auth.login_required
@check_password_changed
def cleanup_unexpected_items_route():
    print("Starting unexpected items cleanup..."); items_to_delete = []
    _, db_uuids = get_database_media(); orphaned_uuid_files, unexpected_files, unexpected_dirs = find_unexpected_items(db_uuids)
    items_to_delete.extend(orphaned_uuid_files); items_to_delete.extend(unexpected_files); items_to_delete.extend(unexpected_dirs)
    if not items_to_delete: flash("No unexpected items found to clean up.", "info"); return redirect(url_for('.config_media'))
    print(f"Found {len(items_to_delete)} unexpected items to delete.")
    deleted_files, deleted_dirs, error_count = cleanup_unexpected_items(items_to_delete)
    deleted_items_msg = [];
    if deleted_files > 0: deleted_items_msg.append(f"{deleted_files} file(s)")
    if deleted_dirs > 0: deleted_items_msg.append(f"{deleted_dirs} director(y/ies)")
    if error_count > 0:
        if deleted_items_msg: flash(f"Deleted {' and '.join(deleted_items_msg)}, but encountered errors deleting {error_count} item(s). Check logs.", "error")
        else: flash(f"Cleanup failed. Encountered errors deleting {error_count} item(s). Check logs.", "error")
    elif deleted_items_msg: flash(f"Successfully deleted {' and '.join(deleted_items_msg)}.", "success")
    else: flash("Cleanup finished, but no items were deleted.", "warning")
    return redirect(url_for('.config_media'))

@config_bp.route('/update-password', methods=['POST'])
@auth.login_required
@check_password_changed
def update_password():
    redirect_url = url_for('.config_general')
    current_password = request.form.get('update_current_password'); new_password = request.form.get('update_new_password'); confirm_password = request.form.get('update_confirm_password')
    if not all([current_password, new_password, confirm_password]): flash("All fields are required.", "error"); return redirect(redirect_url)
    if new_password != confirm_password: flash("New password and confirmation do not match.", "error"); return redirect(redirect_url)
    stored_password_hash = get_setting('auth_password_hash')
    if not stored_password_hash or not check_password_hash(stored_password_hash, current_password): flash("Incorrect current password.", "error"); return redirect(redirect_url)
    if check_password_hash(stored_password_hash, new_password): flash("New password cannot be the same.", "error"); return redirect(redirect_url)
    try:
        new_hash = generate_password_hash(new_password)
        if save_setting('auth_password_hash', new_hash): flash("Password updated successfully!", "success")
        else: flash("Error saving updated password.", "error")
    except Exception as e: print(f"Error processing password update: {e}"); traceback.print_exc(); flash("An unexpected error occurred.", "error")
    return redirect(redirect_url)

@config_bp.route('/logout')
def logout():
    """Logs the user out (clears browser basic auth via 401)."""
    response = make_response(render_template('logout.html'), 401)
    response.headers['WWW-Authenticate'] = 'Basic realm="ShowGo Configuration Access"'
    return response
