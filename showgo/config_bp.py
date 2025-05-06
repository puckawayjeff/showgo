# showgo/config_bp.py
# Blueprint for configuration pages and actions

import os
import traceback
import uuid
from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, make_response, current_app)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge

# Import extensions, models, utils from the application package (.)
from .extensions import db, auth
from .models import ImageFile, Setting
from .utils import (get_setting, save_setting, initialize_database,
                    get_database_images, find_missing_files, find_unexpected_items,
                    cleanup_unexpected_items, remove_missing_db_entries,
                    allowed_file, generate_thumbnail)

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

# --- Routes ---

@config_bp.route('/')
@auth.login_required
def config_redirect():
    """Redirects base blueprint route to the general settings page."""
    return redirect(url_for('.config_general'))

@config_bp.route('/set-initial-password', methods=['GET', 'POST'])
@auth.login_required
def config_set_initial_password():
    """Handles the initial setting of the administrator password."""
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
        settings_saved = True
        try:
            # --- Save Slideshow Settings ---
            allowed_transitions = ['fade', 'slide', 'kenburns']
            transition = request.form.get('transition_effect', 'fade')
            if transition not in allowed_transitions:
                flash(f"Invalid transition effect '{transition}'. Defaulting to 'fade'.", "warning")
                transition = 'fade'
            settings_saved &= save_setting('slideshow_transition_effect', transition)
            settings_saved &= save_setting('slideshow_duration_seconds', int(request.form.get('duration_seconds', 10)))
            settings_saved &= save_setting('slideshow_image_order', request.form.get('image_order', 'sequential'))
            settings_saved &= save_setting('slideshow_image_scaling', request.form.get('image_scaling', 'cover'))

            # --- Save Watermark Settings ---
            settings_saved &= save_setting('watermark_enabled', 'watermark_enabled' in request.form)
            settings_saved &= save_setting('watermark_text', request.form.get('watermark_text', ''))
            settings_saved &= save_setting('watermark_position', request.form.get('watermark_position', 'bottom-right'))

            # --- Save Widget Settings ---
            settings_saved &= save_setting('widgets_time_enabled', 'time_widget_enabled' in request.form)
            settings_saved &= save_setting('widgets_weather_enabled', 'weather_widget_enabled' in request.form)
            settings_saved &= save_setting('widgets_weather_location', request.form.get('weather_location', ''))
            settings_saved &= save_setting('widgets_rss_enabled', 'rss_widget_enabled' in request.form)
            settings_saved &= save_setting('widgets_rss_feed_url', request.form.get('rss_feed_url', ''))

            # *** Save RSS Scroll Speed ***
            allowed_speeds = ['slow', 'medium', 'fast']
            scroll_speed = request.form.get('rss_scroll_speed', 'medium')
            if scroll_speed not in allowed_speeds:
                flash(f"Invalid RSS scroll speed '{scroll_speed}'. Defaulting to 'medium'.", "warning")
                scroll_speed = 'medium'
            settings_saved &= save_setting('widgets_rss_scroll_speed', scroll_speed)
            # *** END Save RSS Scroll Speed ***

            # --- Save Burn-in Settings ---
            settings_saved &= save_setting('burn_in_prevention_enabled', 'burn_in_prevention_enabled' in request.form)
            settings_saved &= save_setting('burn_in_prevention_elements', request.form.getlist('burn_in_elements'))
            settings_saved &= save_setting('burn_in_prevention_interval_seconds', int(request.form.get('burn_in_interval_seconds', 15)))
            settings_saved &= save_setting('burn_in_prevention_strength_pixels', int(request.form.get('burn_in_strength_pixels', 3)))

            # --- Final Flash Message ---
            if settings_saved:
                flash("Configuration saved successfully!", "success")
            else:
                flash("An error occurred while saving some settings. Check logs.", "error")
        except ValueError:
            flash("Invalid input value provided (e.g., duration, interval, strength must be numbers).", "error")
        except Exception as e:
            print(f"Error processing save settings request: {e}")
            traceback.print_exc()
            flash("An unexpected error occurred while saving settings.", "error")
        return redirect(url_for('.config_general')) # Use relative endpoint

    # GET Request Logic
    current_config = {
         "slideshow": {
             "duration_seconds": get_setting("slideshow_duration_seconds", 10),
             "transition_effect": get_setting("slideshow_transition_effect", "fade"),
             "image_order": get_setting("slideshow_image_order", "sequential"),
             "image_scaling": get_setting("slideshow_image_scaling", "cover") },
         "watermark": {
             "enabled": get_setting("watermark_enabled", False),
             "text": get_setting("watermark_text", ""),
             "position": get_setting("watermark_position", "bottom-right") },
         "widgets": {
             "time": {"enabled": get_setting("widgets_time_enabled", True)},
             "weather": {
                 "enabled": get_setting("widgets_weather_enabled", True),
                 "location": get_setting("widgets_weather_location", "") },
             "rss": {
                 "enabled": get_setting("widgets_rss_enabled", False),
                 "feed_url": get_setting("widgets_rss_feed_url", ""),
                 "scroll_speed": get_setting("widgets_rss_scroll_speed", "medium") # *** Get RSS Speed ***
                 } },
         "burn_in_prevention": {
             "enabled": get_setting("burn_in_prevention_enabled", False),
             "elements": get_setting("burn_in_prevention_elements", ["watermark"]),
             "interval_seconds": get_setting("burn_in_prevention_interval_seconds", 15),
             "strength_pixels": get_setting("burn_in_prevention_strength_pixels", 3) },
    }
    return render_template('config_general.html', config=current_config, active_page='general')

# ... (rest of config_bp.py remains the same: config_images, upload_image, delete_images, cleanup routes, update_password, logout) ...
@config_bp.route('/images')
@auth.login_required
@check_password_changed
def config_images():
    all_db_images, db_uuids = get_database_images()
    missing_db_entries = find_missing_files(all_db_images)
    orphaned_uuid_files, unexpected_files, unexpected_dirs = find_unexpected_items(db_uuids)
    displayable_images = [img for img in all_db_images if img not in missing_db_entries]
    displayable_images.sort(key=lambda img: img.uploaded_at, reverse=True)
    return render_template('config_images.html', images=displayable_images, missing_db_entries=missing_db_entries, orphaned_uuid_files=orphaned_uuid_files, unexpected_files=unexpected_files, unexpected_dirs=unexpected_dirs, active_page='images')

@config_bp.route('/upload', methods=['POST'])
@auth.login_required
@check_password_changed
def upload_image():
    pil_available = current_app.config.get('PIL_AVAILABLE', False)
    upload_folder = current_app.config['UPLOAD_FOLDER']
    thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
    thumbnail_size = current_app.config.get('THUMBNAIL_SIZE', (150, 150))
    thumbnail_ext = current_app.config.get('THUMBNAIL_EXT', '.png')
    if not pil_available: flash("Image processing library (Pillow) not installed. Cannot generate thumbnails.", "error")
    if 'image_files' not in request.files: flash('No file part in the request.', 'error'); return redirect(url_for('.config_images'))
    files = request.files.getlist('image_files'); uploaded_count = 0; error_count = 0; thumb_error_count = 0
    if not files or files[0].filename == '': flash('No selected file.', 'error'); return redirect(url_for('.config_images'))
    for file in files:
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename); file_ext = original_filename.rsplit('.', 1)[1].lower(); uuid_hex = uuid.uuid4().hex; disk_filename = f"{uuid_hex}.{file_ext}"; save_path = os.path.join(upload_folder, disk_filename)
            try:
                file.save(save_path); thumb_disk_filename = f"{uuid_hex}{thumbnail_ext}"; thumb_dest_path = os.path.join(thumbnail_folder, thumb_disk_filename); thumb_success, _ = generate_thumbnail(save_path, thumb_dest_path, thumbnail_size)
                if not thumb_success: thumb_error_count += 1; print(f"Warning: Failed to generate thumbnail for {original_filename}")
                display_name_default = os.path.splitext(original_filename)[0]; new_image = ImageFile(uuid_filename=uuid_hex, original_filename=original_filename, display_name=display_name_default, extension=file_ext); db.session.add(new_image); db.session.commit(); uploaded_count += 1
            except RequestEntityTooLarge as e: print(f"Upload failed for {original_filename}: {e}"); flash('Upload failed: Total size exceeds limit.', 'error'); db.session.rollback(); return redirect(url_for('.config_images'))
            except Exception as e: print(f"Error processing file {original_filename}: {e}"); traceback.print_exc(); flash(f'Error processing file {original_filename}.', 'error'); error_count += 1; db.session.rollback()
        elif file and file.filename != '': flash(f'File type not allowed for {secure_filename(file.filename)}.', 'error'); error_count += 1
    if uploaded_count > 0: success_msg = f'Successfully processed {uploaded_count} image(s).'; flash(success_msg, 'success')
    if thumb_error_count > 0: flash(f'Failed to generate thumbnails for {thumb_error_count} image(s). Check logs.', 'warning')
    if error_count > 0: flash(f'Failed to upload or process {error_count} file(s).', 'error')
    return redirect(url_for('.config_images'))

@config_bp.route('/delete', methods=['POST'])
@auth.login_required
@check_password_changed
def delete_images():
    image_ids_to_delete = request.form.getlist('selected_images'); deleted_count = 0; error_count = 0
    if not image_ids_to_delete: flash("No images selected for deletion.", "warning"); return redirect(url_for('.config_images'))
    upload_folder = current_app.config['UPLOAD_FOLDER']; thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
    for image_id in image_ids_to_delete:
        try:
            image_id_int = int(image_id); image_record = db.session.get(ImageFile, image_id_int)
            if image_record:
                disk_filename = image_record.get_disk_filename(); thumbnail_filename = image_record.get_thumbnail_filename(); original_path = os.path.join(upload_folder, disk_filename); thumbnail_path = os.path.join(thumbnail_folder, thumbnail_filename)
                try:
                    if os.path.isfile(original_path): os.remove(original_path)
                    else: print(f"Warning: Original file not found during deletion: {original_path}")
                    if os.path.isfile(thumbnail_path): os.remove(thumbnail_path)
                    else: print(f"Warning: Thumbnail file not found during deletion: {thumbnail_path}")
                except OSError as e: print(f"Error deleting files for image ID {image_id}: {e}"); flash(f"Error deleting files for '{image_record.display_name}', removing DB record anyway.", "warning")
                db.session.delete(image_record); deleted_count += 1
            else: print(f"Image record not found in DB for ID: {image_id}"); error_count += 1
        except ValueError: print(f"Invalid image ID received: {image_id}"); error_count += 1
        except Exception as e: print(f"Error processing deletion for image ID {image_id}: {e}"); traceback.print_exc(); error_count += 1; db.session.rollback()
    try: db.session.commit()
    except Exception as e: print(f"Error committing deletions to DB: {e}"); traceback.print_exc(); flash("Database error during deletion.", "error"); db.session.rollback(); deleted_count = 0; error_count = len(image_ids_to_delete)
    if deleted_count > 0: flash(f"Successfully deleted {deleted_count} image(s).", "success")
    if error_count > 0: flash(f"Error occurred while deleting {error_count} image(s). Check logs.", "error")
    return redirect(url_for('.config_images'))

@config_bp.route('/cleanup/missing-db', methods=['POST'])
@auth.login_required
@check_password_changed
def cleanup_missing_db_route():
    image_ids = request.form.getlist('missing_image_ids')
    if not image_ids: flash("No missing image entries selected for removal.", "warning"); return redirect(url_for('.config_images'))
    print(f"Attempting to remove DB entries for missing image IDs: {image_ids}")
    deleted_count, error_count = remove_missing_db_entries(image_ids)
    if error_count > 0: flash(f"Removed {deleted_count} missing database entries, but encountered errors with {error_count} entries. Check logs.", "error")
    elif deleted_count > 0: flash(f"Successfully removed {deleted_count} database entries for missing images.", "success")
    else: flash("No database entries were removed (perhaps they were already gone?).", "info")
    return redirect(url_for('.config_images'))

@config_bp.route('/cleanup/unexpected-items', methods=['POST'])
@auth.login_required
@check_password_changed
def cleanup_unexpected_items_route():
    print("Starting unexpected items cleanup (including directories)..."); items_to_delete = []
    _, db_uuids = get_database_images(); orphaned_uuid_files, unexpected_files, unexpected_dirs = find_unexpected_items(db_uuids)
    items_to_delete.extend(orphaned_uuid_files); items_to_delete.extend(unexpected_files); items_to_delete.extend(unexpected_dirs)
    if not items_to_delete: flash("No unexpected items found to clean up.", "info"); return redirect(url_for('.config_images'))
    print(f"Found {len(items_to_delete)} unexpected items (files and directories) to delete.")
    deleted_files, deleted_dirs, error_count = cleanup_unexpected_items(items_to_delete)
    deleted_items_msg = []
    if deleted_files > 0: deleted_items_msg.append(f"{deleted_files} file(s)")
    if deleted_dirs > 0: deleted_items_msg.append(f"{deleted_dirs} director(y/ies)")
    if error_count > 0:
        if deleted_items_msg: flash(f"Deleted {' and '.join(deleted_items_msg)}, but encountered errors deleting {error_count} item(s). Check logs.", "error")
        else: flash(f"Cleanup failed. Encountered errors deleting {error_count} item(s). Check logs.", "error")
    elif deleted_items_msg: flash(f"Successfully deleted {' and '.join(deleted_items_msg)}.", "success")
    else: flash("Cleanup finished, but no items were deleted (perhaps they were removed by another process?).", "warning")
    return redirect(url_for('.config_images'))

@config_bp.route('/update-password', methods=['POST'])
@auth.login_required
@check_password_changed
def update_password():
    redirect_url = url_for('.config_general')
    current_password = request.form.get('update_current_password'); new_password = request.form.get('update_new_password'); confirm_password = request.form.get('update_confirm_password')
    if not current_password or not new_password or not confirm_password: flash("All fields are required to update password.", "error"); return redirect(redirect_url)
    if new_password != confirm_password: flash("New password and confirmation do not match.", "error"); return redirect(redirect_url)
    stored_password_hash = get_setting('auth_password_hash')
    if not stored_password_hash or not check_password_hash(stored_password_hash, current_password): flash("Incorrect current password.", "error"); return redirect(redirect_url)
    if check_password_hash(stored_password_hash, new_password): flash("New password cannot be the same as the current password.", "error"); return redirect(redirect_url)
    try:
        new_hash = generate_password_hash(new_password)
        if save_setting('auth_password_hash', new_hash): flash("Password updated successfully!", "success")
        else: flash("Error saving updated password configuration.", "error")
    except Exception as e: print(f"Error processing password update: {e}"); traceback.print_exc(); flash("An unexpected error occurred while updating the password.", "error")
    return redirect(redirect_url)

@config_bp.route('/logout')
def logout():
    return render_template('logout.html')

