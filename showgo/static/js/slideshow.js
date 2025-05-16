// static/js/slideshow.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Loaded. Initializing slideshow script (testing)...");

    // --- DOM Element References ---
    const slideshowContainer = document.getElementById('slideshow-container');
    const imageElement = document.getElementById('slideshow-image');
    const videoElement = document.getElementById('slideshow-video');
    const timeWidget = document.getElementById('time-widget'); // For pixel shift
    const timeDisplay = document.getElementById('time-display'); // For clock update
    const rssTickerContainer = document.getElementById('rss-ticker-container'); // For pixel shift & RSS logic
    const rssTickerContent = document.getElementById('rss-ticker-content');
    const weatherWidget = document.getElementById('weather-widget'); // For pixel shift
    const statusMessageDisplay = document.getElementById('status-message-display');
    const overlayBrandingContainer = document.getElementById('overlay-branding-container');
    const overlayBrandingContent = document.getElementById('overlay-branding-content'); // The inner div

    // --- Check if necessary data and elements exist ---
    if (typeof slideshowData === 'undefined' || slideshowData === null ||
        !slideshowContainer || !imageElement || !videoElement) {
        console.error("Slideshow container, media elements, or data object not found/initialized.");
        if (statusMessageDisplay) { statusMessageDisplay.innerHTML = '<p style="color: red;">Error: Slideshow failed to initialize.</p>'; }
        else if (slideshowContainer) { slideshowContainer.innerHTML = '<p id="status-message-display" style="color: red; text-align: center; padding-top: 20%;">Error: Slideshow failed to initialize.</p>'; }
        return;
    }
    console.log("Slideshow Data (v3.2):", slideshowData);

    // --- Destructure Config and Data ---
    const mediaItems = slideshowData.mediaItems || [];
    const config = slideshowData.config || {}; // Full config object from Flask
    const slideshowConfig = config.slideshow || {};
    const overlayConfig = config.overlay || {}; // Overlay specific settings
    const widgetConfig = config.widgets || {};
    const burnInConfig = config.burn_in_prevention || {};
    const initialTimestamp = slideshowData.initialTimestamp || 0;
    const mediaBaseUrl = slideshowData.mediaBaseUrl || '';

    // Specific config values for easier access
    const imageDuration = (slideshowConfig.duration_seconds || 10) * 1000;
    const transitionEffect = slideshowConfig.transition_effect || 'fade';
    const imageScaling = slideshowConfig.image_scaling || 'cover';
    const videoScaling = slideshowConfig.video_scaling || 'contain';
    const videoAutoplay = slideshowConfig.video_autoplay ?? true;
    const videoLoop = slideshowConfig.video_loop ?? false;
    const videoMuted = slideshowConfig.video_muted ?? true;
    const videoShowControls = slideshowConfig.video_show_controls ?? false;

    // --- Video advanced settings ---
    const videoDurationLimitEnabled = slideshowConfig.video_duration_limit_enabled ?? false;
    const videoDurationLimitSeconds = slideshowConfig.video_duration_limit_seconds ?? 30;
    const videoRandomStartEnabled = slideshowConfig.video_random_start_enabled ?? false;
    let videoDurationTimeoutId = null;

    const timeEnabled = widgetConfig.time?.enabled ?? true;
    const rssIsEnabled = widgetConfig.rss?.enabled ?? false;
    const rssSettings = widgetConfig.rss || {};

    // --- State Variables ---
    let currentMediaIndex = -1;
    let slideshowTimeoutId = null;
    let timeIntervalId = null;
    let pixelShiftIntervalId = null;
    let configCheckIntervalId = null;
    let isTransitioning = false;
    const doubleTapDelay = 400;
    let lastTap = 0;

    const shiftableElementMap = {
        'overlay': overlayBrandingContainer, // Target the main container for shifting
        'time': timeWidget,
        'weather': weatherWidget,
        'rss': rssTickerContainer,
        'status': statusMessageDisplay
    };

    // --- Helper Functions ---
    function preloadMedia(index) {
        if (index < 0 || index >= mediaItems.length) return Promise.resolve();
        const item = mediaItems[index];
        const url = `${mediaBaseUrl}${encodeURIComponent(item.filename)}`;
        if (item.type === 'image') {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = resolve;
                img.onerror = (err) => {
                    console.warn(`[Preload] Failed for image: ${item.filename}`, err);
                    reject(err);
                };
                img.src = url;
            });
        } else {
            return Promise.resolve(); // Not preloading videos for now
        }
    }

    function updateClock() {
        if (!timeDisplay) return;
        try {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            timeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
        } catch (e) {
            console.error("Error updating clock:", e);
            if (timeIntervalId) clearInterval(timeIntervalId);
            timeIntervalId = null;
            timeDisplay.textContent = "??:??:??";
        }
    }

    function applyKenBurnsEffect(element, animationDuration) {
        if (!element) return;
        element.classList.remove('kenburns-active');
        element.style.transition = '';
        const scaleFactor = 1.15;
        const startsZoomed = Math.random() < 0.5;
        const startScale = startsZoomed ? scaleFactor : 1;
        const endScale = startsZoomed ? 1 : scaleFactor;
        const maxTranslateX = ((Math.max(startScale, endScale) - 1) / 2) * 50;
        const maxTranslateY = ((Math.max(startScale, endScale) - 1) / 2) * 50;
        const startX = (Math.random() * maxTranslateX * 2) - maxTranslateX;
        const startY = (Math.random() * maxTranslateY * 2) - maxTranslateY;
        const endX = (Math.random() * maxTranslateX * 2) - maxTranslateX;
        const endY = (Math.random() * maxTranslateY * 2) - maxTranslateY;
        const originX = Math.random() * 50 + 25;
        const originY = Math.random() * 50 + 25;
        element.style.transformOrigin = `${originX}% ${originY}%`;
        element.style.transform = `scale(${startScale}) translate(${startX}%, ${startY}%)`;
        void element.offsetWidth; // Force reflow
        element.style.setProperty('--kb-duration', `${animationDuration / 1000}s`);
        element.classList.add('kenburns-active');
        element.style.transform = `scale(${endScale}) translate(${endX}%, ${endY}%)`;
    }

    function resetKenBurnsEffect(element) {
         if (!element) return;
         element.classList.remove('kenburns-active');
         element.style.transition = 'none';
         element.style.transform = 'scale(1) translate(0, 0)';
         element.style.transformOrigin = 'center center';
         void element.offsetWidth; // Force reflow
         element.style.transition = ''; // Restore default (e.g., for opacity)
    }

    function updateOverlayBranding() {
        // Check if overlay is enabled and the container element exists in the DOM
        if (!overlayConfig.enabled || !overlayBrandingContainer) {
            if (overlayBrandingContainer) overlayBrandingContainer.style.display = 'none'; // Hide if exists but disabled
            return;
        }

        overlayBrandingContainer.style.display = 'flex'; // Make container visible
        if (overlayBrandingContent) { // Check if inner content div exists
            overlayBrandingContent.innerHTML = ''; // Clear previous content

            // Apply styles to the content box
            overlayBrandingContent.style.backgroundColor = overlayConfig.background_color || 'rgba(0,0,0,0.5)';
            overlayBrandingContent.style.padding = overlayConfig.padding || '10px';
            overlayBrandingContent.style.borderRadius = '0.375rem'; // Tailwind 'rounded-md'
            // Potentially add other styles like border if needed from config
        } else {
            console.warn("OverlayBranding: Inner content element not found.");
            return; // Cannot proceed without inner content div
        }


        // Apply positioning to the main container
        const position = overlayConfig.position || 'bottom-right';
        const margin = '20px'; // Default margin from viewport edge

        // Reset all position properties first for clean state
        overlayBrandingContainer.style.top = 'auto';
        overlayBrandingContainer.style.left = 'auto';
        overlayBrandingContainer.style.right = 'auto';
        overlayBrandingContainer.style.bottom = 'auto';
        overlayBrandingContainer.style.transform = 'none'; // Reset transform for centering

        // Set flex alignment on the container itself for positioning content box
        switch (position) {
            case 'top-left': overlayBrandingContainer.style.top = margin; overlayBrandingContainer.style.left = margin; overlayBrandingContainer.style.justifyContent = 'flex-start'; overlayBrandingContainer.style.alignItems = 'flex-start'; break;
            case 'top-center': overlayBrandingContainer.style.top = margin; overlayBrandingContainer.style.left = '50%'; overlayBrandingContainer.style.transform = 'translateX(-50%)'; overlayBrandingContainer.style.justifyContent = 'center'; overlayBrandingContainer.style.alignItems = 'flex-start'; break;
            case 'top-right': overlayBrandingContainer.style.top = margin; overlayBrandingContainer.style.right = margin; overlayBrandingContainer.style.justifyContent = 'flex-end'; overlayBrandingContainer.style.alignItems = 'flex-start'; break;
            case 'middle-left': overlayBrandingContainer.style.top = '50%'; overlayBrandingContainer.style.left = margin; overlayBrandingContainer.style.transform = 'translateY(-50%)'; overlayBrandingContainer.style.justifyContent = 'flex-start'; overlayBrandingContainer.style.alignItems = 'center'; break;
            case 'center': overlayBrandingContainer.style.top = '50%'; overlayBrandingContainer.style.left = '50%'; overlayBrandingContainer.style.transform = 'translate(-50%, -50%)'; overlayBrandingContainer.style.justifyContent = 'center'; overlayBrandingContainer.style.alignItems = 'center'; break;
            case 'middle-right': overlayBrandingContainer.style.top = '50%'; overlayBrandingContainer.style.right = margin; overlayBrandingContainer.style.transform = 'translateY(-50%)'; overlayBrandingContainer.style.justifyContent = 'flex-end'; overlayBrandingContainer.style.alignItems = 'center'; break;
            case 'bottom-left': overlayBrandingContainer.style.bottom = margin; overlayBrandingContainer.style.left = margin; overlayBrandingContainer.style.justifyContent = 'flex-start'; overlayBrandingContainer.style.alignItems = 'flex-end'; break;
            case 'bottom-center': overlayBrandingContainer.style.bottom = margin; overlayBrandingContainer.style.left = '50%'; overlayBrandingContainer.style.transform = 'translateX(-50%)'; overlayBrandingContainer.style.justifyContent = 'center'; overlayBrandingContainer.style.alignItems = 'flex-end'; break;
            case 'bottom-right': default: overlayBrandingContainer.style.bottom = margin; overlayBrandingContainer.style.right = margin; overlayBrandingContainer.style.justifyContent = 'flex-end'; overlayBrandingContainer.style.alignItems = 'flex-end'; break;
        }

        // Create and append elements based on display_mode
        const displayMode = overlayConfig.display_mode || 'text_only';
        const showText = displayMode.includes('text') && overlayConfig.text;
        const showLogo = displayMode.includes('logo') && overlayConfig.logo_enabled && overlayConfig.logo_url;

        let textElement = null;
        let logoElement = null;

        if (showText) {
            textElement = document.createElement('span');
            textElement.className = 'text'; // For potential CSS targeting
            textElement.textContent = overlayConfig.text;
            textElement.style.fontSize = overlayConfig.font_size || '24px';
            textElement.style.color = overlayConfig.font_color || '#FFFFFF';
        }

        if (showLogo) {
            logoElement = document.createElement('img');
            logoElement.className = 'logo'; // For CSS targeting (max-height, etc. in HTML style tag)
            logoElement.src = overlayConfig.logo_url; // URL includes cache-buster
            logoElement.alt = "Overlay Logo";
        }

        // Set flex direction for the inner content box and append elements
        if (displayMode === 'logo_and_text_below') {
            overlayBrandingContent.style.flexDirection = 'column';
            overlayBrandingContent.style.textAlign = 'center'; // Center text if it wraps
            if (logoElement) {
                logoElement.style.marginBottom = '5px'; // Space between logo and text
                overlayBrandingContent.appendChild(logoElement);
            }
            if (textElement) {
                overlayBrandingContent.appendChild(textElement);
            }
        } else if (displayMode === 'logo_and_text_side') {
            overlayBrandingContent.style.flexDirection = 'row';
            overlayBrandingContent.style.textAlign = 'left'; // Default for side-by-side
            if (logoElement) {
                logoElement.style.marginRight = '10px'; // Space between logo and text
                overlayBrandingContent.appendChild(logoElement);
            }
            if (textElement) {
                overlayBrandingContent.appendChild(textElement);
            }
        } else if (displayMode === 'logo_only' && logoElement) {
            overlayBrandingContent.style.flexDirection = 'row'; // or column, doesn't matter much
            overlayBrandingContent.appendChild(logoElement);
        } else if (displayMode === 'text_only' && textElement) {
            overlayBrandingContent.style.flexDirection = 'row';
            overlayBrandingContent.appendChild(textElement);
        }
        console.log("Overlay branding updated with content.");
    }

    function applyPixelShift() {
        if (!burnInConfig || !burnInConfig.enabled || !burnInConfig.elements || burnInConfig.elements.length === 0) {
            if (pixelShiftIntervalId) { clearInterval(pixelShiftIntervalId); pixelShiftIntervalId = null; }
            Object.values(shiftableElementMap).forEach(element => {
                if (element && element.style) element.style.transform = '';
            });
            return;
        }
        const strength = burnInConfig.strength_pixels || 3;
        const offsetX = Math.floor(Math.random() * (2 * strength + 1)) - strength;
        const offsetY = Math.floor(Math.random() * (2 * strength + 1)) - strength;

        burnInConfig.elements.forEach(elementId => {
            const element = shiftableElementMap[elementId];
            // Ensure element exists and has a style property before attempting to transform
            if (element && element.style) {
                if (elementId === 'rss') { // RSS only shifts vertically
                    element.style.transform = `translate(0px, ${offsetY}px)`;
                } else { // Other elements shift in both X and Y
                    element.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
                }
            } else if (elementId === 'overlay' && !overlayBrandingContainer) {
                // If overlay is targeted but doesn't exist (e.g., disabled), do nothing.
            } else if (!element) {
                // Log if a configured element for shifting is not found.
                console.warn(`Pixel shift: Element with ID '${elementId}' not found in shiftableElementMap or DOM.`);
            }
        });
    }

    // --- Core Slideshow Logic ---
    function showNextMedia() {
        if (isTransitioning || !mediaItems || mediaItems.length === 0) {
            if (!mediaItems || mediaItems.length === 0) {
                 if(slideshowTimeoutId) clearTimeout(slideshowTimeoutId); slideshowTimeoutId = null;
                 imageElement.classList.remove('active'); videoElement.classList.remove('active');
                 if(statusMessageDisplay) statusMessageDisplay.style.display = 'block';
            }
            return;
        }
        isTransitioning = true;
        if(statusMessageDisplay) statusMessageDisplay.style.display = 'none';
        if (slideshowTimeoutId) clearTimeout(slideshowTimeoutId); slideshowTimeoutId = null;

        currentMediaIndex = (currentMediaIndex + 1) % mediaItems.length;
        const currentItem = mediaItems[currentMediaIndex];
        const mediaUrl = `${mediaBaseUrl}${encodeURIComponent(currentItem.filename)}`;
        console.log(`[Slideshow] Showing media ${currentMediaIndex + 1}/${mediaItems.length}: ${currentItem.filename} (Type: ${currentItem.type})`);

        const activeElement = imageElement.classList.contains('active') ? imageElement : (videoElement.classList.contains('active') ? videoElement : null);
        if (activeElement) {
            activeElement.classList.remove('active');
            if (activeElement === imageElement) resetKenBurnsEffect(imageElement);
            if (activeElement === videoElement) { videoElement.pause(); videoElement.src = ""; /* Clear src to stop download/processing */ }
        }

        setTimeout(() => { // Delay for fade-out transition of previous item
            if (currentItem.type === 'image') {
                videoElement.style.display = 'none'; imageElement.style.display = 'block';
                imageElement.style.objectFit = imageScaling; imageElement.alt = currentItem.filename;
                const tempImg = new Image();
                tempImg.onload = () => {
                    imageElement.src = mediaUrl;
                    if (transitionEffect === 'kenburns') {
                        setTimeout(() => applyKenBurnsEffect(imageElement, imageDuration), 50);
                    }
                    imageElement.classList.add('active'); isTransitioning = false;
                    slideshowTimeoutId = setTimeout(showNextMedia, imageDuration);
                    preloadMedia((currentMediaIndex + 1) % mediaItems.length).catch(err => console.warn(`[Preload] Image preload failed`, err));
                };
                tempImg.onerror = () => {
                    console.error(`[Slideshow] Failed to load image: ${currentItem.filename}`);
                    imageElement.alt = `Error loading ${currentItem.filename}`; imageElement.src = "";
                    imageElement.classList.remove('active'); isTransitioning = false;
                    slideshowTimeoutId = setTimeout(showNextMedia, 100); // Try next quickly
                };
                tempImg.src = mediaUrl;
            } else if (currentItem.type === 'video') {
                imageElement.style.display = 'none';
                videoElement.style.display = 'block';
                videoElement.style.objectFit = videoScaling;
                videoElement.src = mediaUrl;
                videoElement.autoplay = videoAutoplay;
                videoElement.loop = videoLoop;
                videoElement.muted = videoMuted;
                videoElement.controls = videoShowControls;
                videoElement.load();

                if (videoDurationTimeoutId) { clearTimeout(videoDurationTimeoutId); videoDurationTimeoutId = null; }

                // Handler for when metadata is loaded (duration is known)
                const loadedMetadataHandler = () => {
                    console.log('loadedmetadata fired', {
                        duration: videoElement.duration,
                        videoDurationLimitEnabled,
                        videoRandomStartEnabled,
                        videoDurationLimitSeconds
                    });
                    videoElement.removeEventListener('loadedmetadata', loadedMetadataHandler);
                    // Random start logic
                    if (videoRandomStartEnabled && videoDurationLimitEnabled) {
                        const duration = videoElement.duration;
                        if (!isNaN(duration) && duration > videoDurationLimitSeconds) {
                            const maxStart = duration - videoDurationLimitSeconds;
                            const randomStart = Math.random() * maxStart;
                            console.log('Setting random start time:', randomStart);
                            videoElement.currentTime = randomStart;
                        } else {
                            console.log('Random start skipped: invalid duration or duration too short');
                        }
                    } else {
                        console.log('Random start not enabled');
                    }
                };

                // Handler for when video can play
                const canPlayHandler = () => {
                    console.log('canPlayHandler fired');
                    videoElement.removeEventListener('canplay', canPlayHandler);
                    videoElement.removeEventListener('error', errorHandler);
                    videoElement.classList.add('active');
                    isTransitioning = false;
                    console.log(`[Slideshow] Video ready: ${currentItem.filename}`);

                    if (videoAutoplay) {
                        videoElement.play().catch(e => console.warn(`Autoplay for ${currentItem.filename} prevented:`, e));
                    }

                    // Duration limit logic
                    if (videoDurationLimitEnabled) {
                        console.log('Setting duration limit timeout for', videoDurationLimitSeconds, 'seconds');
                        videoDurationTimeoutId = setTimeout(() => {
                            console.log('Duration limit reached, advancing to next media');
                            videoElement.pause();
                            videoElement.classList.remove('active');
                            showNextMedia();
                        }, videoDurationLimitSeconds * 1000);
                    } else if (videoLoop) {
                        slideshowTimeoutId = setTimeout(showNextMedia, imageDuration);
                    }

                    preloadMedia((currentMediaIndex + 1) % mediaItems.length).catch(err => console.warn(`[Preload] Video related preload failed`, err));
                };

                const errorHandler = (e) => {
                    videoElement.removeEventListener('canplay', canPlayHandler);
                    videoElement.removeEventListener('error', errorHandler);
                    videoElement.classList.remove('active');
                    isTransitioning = false;
                    slideshowTimeoutId = setTimeout(showNextMedia, 100); // Try next quickly
                };

                videoElement.addEventListener('loadedmetadata', loadedMetadataHandler);
                videoElement.addEventListener('canplay', canPlayHandler);
                videoElement.addEventListener('error', errorHandler);
            } else {
                console.warn(`[Slideshow] Unknown media type: ${currentItem.type}`); isTransitioning = false;
                slideshowTimeoutId = setTimeout(showNextMedia, 100); // Skip to next
            }
        }, 100); // Short delay for fade-out of previous item
    }

    videoElement.addEventListener('ended', () => {
        if (!videoLoop && videoElement.classList.contains('active')) { // Only if not looping and is the active element
            console.log(`[Slideshow] Video ended: ${mediaItems[currentMediaIndex]?.filename}. Advancing.`);
            if (slideshowTimeoutId) clearTimeout(slideshowTimeoutId); slideshowTimeoutId = null;
            if (videoDurationTimeoutId) { clearTimeout(videoDurationTimeoutId); videoDurationTimeoutId = null; }
            setTimeout(showNextMedia, 50); // Short delay before showing next media
        }
    });

    // --- Fullscreen and Interaction Logic ---
    function toggleFullScreen() {
        if (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement ) {
            if (document.documentElement.requestFullscreen) { document.documentElement.requestFullscreen(); }
            else if (document.documentElement.mozRequestFullScreen) { document.documentElement.mozRequestFullScreen(); }
            else if (document.documentElement.webkitRequestFullscreen) { document.documentElement.webkitRequestFullscreen(); }
            else if (document.documentElement.msRequestFullscreen) { document.documentElement.msRequestFullscreen(); }
        } else {
            if (document.exitFullscreen) { document.exitFullscreen(); }
            else if (document.mozCancelFullScreen) { document.mozCancelFullScreen(); }
            else if (document.webkitExitFullscreen) { document.webkitExitFullscreen(); }
            else if (document.msExitFullscreen) { document.msExitFullscreen(); }
        }
    }
    function handleDoubleTap(event) {
        const currentTime = new Date().getTime();
        const tapLength = currentTime - lastTap;
        if (tapLength < doubleTapDelay && tapLength > 0) { event.preventDefault(); toggleFullScreen(); }
        lastTap = currentTime;
    }
    async function checkForConfigUpdate() {
        try {
            const response = await fetch('/api/config/check', { cache: 'no-store' });
            if (!response.ok) { console.error(`Config check failed with status: ${response.status}`); return; }
            const data = await response.json(); const serverTimestamp = data.timestamp;
            if (typeof serverTimestamp === 'number' && typeof initialTimestamp === 'number' && Math.abs(serverTimestamp - initialTimestamp) > 0.01 && initialTimestamp !== 0) {
                console.log("Configuration change detected. Reloading page...");
                if (slideshowTimeoutId) clearTimeout(slideshowTimeoutId);
                if (timeIntervalId) clearInterval(timeIntervalId);
                if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId);
                if (configCheckIntervalId) clearInterval(configCheckIntervalId);
                window.location.reload(true);
            }
        } catch (error) { console.error("Error during config check fetch:", error); }
    }
    function handleFullscreenChange() {
        const isFullscreen = !!(document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement);
        document.body.classList.toggle('fullscreen-active', isFullscreen);
        console.log(isFullscreen ? "Entered fullscreen mode." : "Exited fullscreen mode.");
    }

    // --- Initialization ---
    console.log("Starting Initialization (v3.2 - Overlay Branding Complete)...");
    updateOverlayBranding(); // Initialize overlay based on current config

    if (!mediaItems || mediaItems.length === 0) {
        console.log("No valid media items found in slideshowData during init.");
        if(statusMessageDisplay) statusMessageDisplay.style.display = 'block';
    } else {
         console.log(`Found ${mediaItems.length} media items. Starting slideshow.`);
         if(statusMessageDisplay) statusMessageDisplay.style.display = 'none';
         showNextMedia(); // Start the slideshow
    }

    // Initialize Widgets
    if (timeEnabled && timeDisplay) { updateClock(); if (timeIntervalId) clearInterval(timeIntervalId); timeIntervalId = setInterval(updateClock, 1000); }
    if (rssIsEnabled && rssTickerContainer && rssTickerContent) {
         let scrollDuration = '80s';
         switch (rssSettings.scroll_speed) { case 'slow': scrollDuration = '120s'; break; case 'fast': scrollDuration = '50s'; break; }
         rssTickerContent.style.setProperty('--rss-scroll-duration', scrollDuration); rssTickerContainer.style.display = '';
    } else if (rssTickerContainer) { rssTickerContainer.style.display = 'none'; }

    // Initialize Burn-in Prevention
    if (burnInConfig && burnInConfig.enabled && burnInConfig.elements && burnInConfig.elements.length > 0) {
        const shiftInterval = (burnInConfig.interval_seconds || 15) * 1000;
        if (shiftInterval > 0) {
            applyPixelShift(); // Initial shift
            if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId);
            pixelShiftIntervalId = setInterval(applyPixelShift, shiftInterval);
            console.log(`Burn-in prevention initialized for elements:`, burnInConfig.elements);
        } else { applyPixelShift(); /* Apply once to reset if interval is bad */ }
    } else { applyPixelShift(); /* Apply once to reset if disabled or no elements */ }

    // Event Listeners
    if (slideshowContainer) { slideshowContainer.addEventListener('touchstart', handleDoubleTap, { passive: false }); slideshowContainer.addEventListener('dblclick', (event) => { event.preventDefault(); toggleFullScreen(); }); }
    document.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) { event.preventDefault(); toggleFullScreen(); } });
    ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'msfullscreenchange'].forEach(event => document.addEventListener(event, handleFullscreenChange, false));
    handleFullscreenChange(); // Initial check for fullscreen state

    // Start Config Polling
    if (initialTimestamp !== null && initialTimestamp !== 0) { // Ensure initialTimestamp is valid
        if (configCheckIntervalId) clearInterval(configCheckIntervalId);
        configCheckIntervalId = setInterval(checkForConfigUpdate, 30000); // Poll every 30 seconds
        console.log(`Started config polling. Initial timestamp: ${initialTimestamp}`);
    } else { console.warn("Config polling disabled due to missing or zero initial timestamp."); }

}); // End DOMContentLoaded
