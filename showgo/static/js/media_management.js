// Media Management Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeVideoSettings();
    initializeWebPQualitySlider();
    initializeMediaGrid();
    initializeUploadForm();
    initializeCleanupForms();
});

function initializeVideoSettings() {
    const durationLimitCheckbox = document.querySelector('input[name="video_duration_limit_enabled"]');
    const durationLimitControls = document.getElementById('duration-limit-controls');
    const durationInput = document.getElementById('video_duration_limit');
    const randomStartCheckbox = document.querySelector('input[name="video_random_start_enabled"]');

    if (durationLimitCheckbox && durationLimitControls && durationInput && randomStartCheckbox) {
        durationLimitCheckbox.addEventListener('change', function() {
            // Enable/disable and adjust opacity of duration controls
            const isEnabled = this.checked;
            durationLimitControls.classList.toggle('opacity-50', !isEnabled);
            durationInput.disabled = !isEnabled;
            
            // Enable/disable random start checkbox based on duration limit
            randomStartCheckbox.disabled = !isEnabled;
            if (!isEnabled) {
                randomStartCheckbox.checked = false;
            }
        });

        // Ensure duration is reasonable when changed
        durationInput.addEventListener('change', function() {
            const value = parseInt(this.value, 10);
            if (value < 1) this.value = 1;
            if (value > 3600) this.value = 3600;
        });
    }
}

function initializeWebPQualitySlider() {
    const convertToWebPCheckbox = document.getElementById('convert_to_webp');
    const webpQualityGroup = document.getElementById('webp_quality_group');
    const webpQualitySlider = document.getElementById('webp_quality');
    const webpQualityValue = document.getElementById('webp_quality_value');

    if (convertToWebPCheckbox && webpQualityGroup && webpQualitySlider && webpQualityValue) {
        // Set initial visibility
        webpQualityGroup.style.display = convertToWebPCheckbox.checked ? 'block' : 'none';

        // Update visibility when checkbox changes
        convertToWebPCheckbox.addEventListener('change', function() {
            webpQualityGroup.style.display = this.checked ? 'block' : 'none';
        });

        // Update displayed value when slider changes
        webpQualitySlider.addEventListener('input', function() {
            webpQualityValue.textContent = this.value;
        });
    }
}

function initializeMediaGrid() {
    const grid = document.getElementById('media-grid');
    const deleteButton = document.getElementById('delete-button');
    const selectedCountSpan = document.getElementById('selected-count');
    const deleteForm = document.getElementById('delete-media-form');
    const selectionControls = document.getElementById('selection-controls');
    const selectAllBtn = document.getElementById('select-all');
    const selectNoneBtn = document.getElementById('select-none');
    const mediaCheckboxes = document.querySelectorAll('.media-checkbox');

    if (grid && deleteButton && selectedCountSpan && deleteForm && selectionControls && selectAllBtn && selectNoneBtn && mediaCheckboxes.length > 0) {
        function updateDeleteButtonState() {
            const checkedCheckboxes = grid.querySelectorAll('.media-checkbox:checked');
            const count = checkedCheckboxes.length;

            selectedCountSpan.textContent = count;
            deleteButton.disabled = count === 0;
            
            // Show/hide selection controls based on selected items
            if (count > 0) {
                selectionControls.classList.remove('hidden');
            } else {
                selectionControls.classList.add('hidden');
            }

            // Update thumbnail styling
            grid.querySelectorAll('.thumbnail-item').forEach(item => {
                const checkbox = item.querySelector('.media-checkbox');
                if (checkbox) {
                    item.classList.toggle('is-selected', checkbox.checked);
                }
            });
        }

        // Select All button
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', function() {
                mediaCheckboxes.forEach(checkbox => checkbox.checked = true);
                updateDeleteButtonState();
            });
        }

        // Select None button
        if (selectNoneBtn) {
            selectNoneBtn.addEventListener('click', function() {
                mediaCheckboxes.forEach(checkbox => checkbox.checked = false);
                updateDeleteButtonState();
            });
        }

        // Click handler for thumbnails
        grid.addEventListener('click', function(event) {
            const thumbItem = event.target.closest('.thumbnail-item');
            if (thumbItem) {
                const checkbox = thumbItem.querySelector('.media-checkbox');
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });

        // Change handler for checkboxes
        mediaCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateDeleteButtonState);
        });

        // Delete confirmation
        deleteForm.addEventListener('submit', function(event) {
            const selectedCount = parseInt(selectedCountSpan.textContent, 10);
            if (selectedCount > 0) {
                if (!confirm(`Are you sure you want to delete ${selectedCount} selected media file(s)? This cannot be undone.`)) {
                    event.preventDefault();
                }
            } else {
                event.preventDefault();
            }
        });

        // Initial state update
        updateDeleteButtonState();
    }
}

function initializeUploadForm() {
    const uploadForm = document.getElementById('upload-media-form');
    const uploadButton = document.getElementById('upload-button');
    const uploadSpinner = document.getElementById('upload-spinner');

    if (uploadForm && uploadButton && uploadSpinner) {
        uploadForm.addEventListener('submit', function(event) {
            const fileInput = document.getElementById('media_files');
            if (fileInput && fileInput.files.length > 0) {
                uploadSpinner.classList.remove('hidden');
                uploadButton.disabled = true;
                uploadButton.textContent = 'Uploading...';
            } else {
                event.preventDefault();
                console.warn("Upload attempt with no files selected.");
            }
        });
    }
}

function initializeCleanupForms() {
    const cleanupMissingDbForm = document.getElementById('cleanup-missing-db-form');
    if (cleanupMissingDbForm) {
        cleanupMissingDbForm.addEventListener('submit', function(event) {
            const count = cleanupMissingDbForm.querySelectorAll(
                'input[name="missing_media_ids"]'
            ).length;
            if (!confirm(
                `Are you sure you want to remove ${count} database entries for media with missing files? This cannot be undone.`
            )) {
                event.preventDefault();
            }
        });
    }
} 