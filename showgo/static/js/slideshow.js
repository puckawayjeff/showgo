// static/js/slideshow.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Loaded. Initializing slideshow script (v2 - Video Support)...");

    // *** ADDED: Log the raw slideshowData object as soon as the script runs ***
    console.log("Initial slideshowData object:", slideshowData);

    // --- DOM Element References ---
    const slideshowContainer = document.getElementById('slideshow-container');
    const imageElement = document.getElementById('slideshow-image'); // Image display
    const videoElement = document.getElementById('slideshow-video'); // Video display (NEW)
    const timeWidget = document.getElementById('time-widget');
    const timeDisplay = document.getElementById('time-display');
    const rssTickerContainer = document.getElementById('rss-ticker-container');
    const rssTickerContent = document.getElementById('rss-ticker-content');
    const watermarkElement = document.getElementById('watermark');
    const weatherWidget = document.getElementById('weather-widget');
    const statusMessageDisplay = document.getElementById('status-message-display');

    // --- Check if necessary data and elements exist ---
    // Check slideshowData FIRST, before trying to access its properties
    if (typeof slideshowData === 'undefined' || slideshowData === null || !slideshowContainer || !imageElement || !videoElement) {
        console.error("Slideshow container, media elements, or data object not found/initialized.", {
            container: !!slideshowContainer,
            imageElement: !!imageElement,
            videoElement: !!videoElement,
            dataObjectExists: (slideshowData !== null && typeof slideshowData !== 'undefined') // Explicitly check data object
        });
        if (statusMessageDisplay) { statusMessageDisplay.innerHTML = '<p style="color: red;">Error: Slideshow failed to initialize. Missing elements or data.</p>'; }
        else if (slideshowContainer) { slideshowContainer.innerHTML = '<p id="status-message-display" style="color: red; text-align: center; padding-top: 20%;">Error: Slideshow failed to initialize.</p>'; }
        return; // Stop execution
    }
    // Now we know slideshowData exists, log its properties
    console.log("Slideshow data confirmed. mediaItems:", slideshowData.mediaItems);
    console.log("Slideshow data confirmed. config:", slideshowData.config);


    // --- Destructure Config and Data ---
    // Access properties safely now that we know slideshowData exists
    const mediaItems = slideshowData.mediaItems || []; // List of {filename, type}
    const config = slideshowData.config || {};
    const slideshowConfig = config.slideshow || {};
    const widgetConfig = config.widgets || {};
    const watermarkConfig = config.watermark || {};
    const burnInConfig = config.burn_in_prevention || {};
    const initialTimestamp = slideshowData.initialTimestamp || 0;
    const mediaBaseUrl = slideshowData.mediaBaseUrl || ''; // Base URL for uploads

    // Specific config values with defaults
    const imageDuration = (slideshowConfig.duration_seconds || 10) * 1000;
    const transitionEffect = slideshowConfig.transition_effect || 'fade'; // Primarily for images
    const imageScaling = slideshowConfig.image_scaling || 'cover';
    const videoScaling = slideshowConfig.video_scaling || 'contain';
    const videoAutoplay = slideshowConfig.video_autoplay ?? true;
    const videoLoop = slideshowConfig.video_loop ?? false;
    const videoMuted = slideshowConfig.video_muted ?? true;
    const videoShowControls = slideshowConfig.video_show_controls ?? false;

    const timeEnabled = widgetConfig.time?.enabled ?? true;
    const rssConfig = widgetConfig.rss || {};

    // --- State Variables ---
    let currentMediaIndex = -1;
    let slideshowTimeoutId = null; // Timeout used for images or looping videos
    let timeIntervalId = null;
    let pixelShiftIntervalId = null;
    let configCheckIntervalId = null;
    let isTransitioning = false; // Flag to prevent rapid transitions

    const doubleTapDelay = 400;
    let lastTap = 0;

    // Map element IDs to elements for pixel shift
    const shiftableElementMap = {
        'watermark': watermarkElement,
        'time': timeDisplay,
        'weather': weatherWidget,
        'rss': rssTickerContainer,
        'status': statusMessageDisplay
    };

    // --- Helper Functions --- (Keep existing helpers: preloadMedia, updateClock, setWatermarkPosition, applyPixelShift, applyKenBurnsEffect, resetKenBurnsEffect) ...
    function preloadMedia(index) {
        if (index < 0 || index >= mediaItems.length) return Promise.resolve();
        const item = mediaItems[index];
        const url = `${mediaBaseUrl}${encodeURIComponent(item.filename)}`;
        if (item.type === 'image') {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = resolve;
                img.onerror = reject;
                img.src = url;
            });
        } else {
            return Promise.resolve();
        }
    }
    function updateClock() { if (!timeDisplay) return; try { const now = new Date(); const hours = String(now.getHours()).padStart(2, '0'); const minutes = String(now.getMinutes()).padStart(2, '0'); const seconds = String(now.getSeconds()).padStart(2, '0'); timeDisplay.textContent = `${hours}:${minutes}:${seconds}`; } catch (e) { console.error("Error updating clock:", e); if(timeIntervalId) clearInterval(timeIntervalId); timeIntervalId = null; timeDisplay.textContent = "??:??:??"; } }
    function setWatermarkPosition() { if (!watermarkElement || !watermarkConfig.enabled) return; watermarkElement.style.transform = ''; watermarkElement.className = `widget ${watermarkConfig.position || 'bottom-right'}`; }
    function applyPixelShift() { if (!burnInConfig || !burnInConfig.enabled || !burnInConfig.elements || burnInConfig.elements.length === 0) { if (pixelShiftIntervalId) { clearInterval(pixelShiftIntervalId); pixelShiftIntervalId = null; } Object.values(shiftableElementMap).forEach(element => { if (element) element.style.transform = ''; }); return; } const strength = burnInConfig.strength_pixels || 3; const offsetX = Math.floor(Math.random() * (2 * strength + 1)) - strength; const offsetY = Math.floor(Math.random() * (2 * strength + 1)) - strength; burnInConfig.elements.forEach(elementId => { const element = shiftableElementMap[elementId]; if (element) { if (elementId === 'rss') { element.style.transform = `translate(0px, ${offsetY}px)`; } else { element.style.transform = `translate(${offsetX}px, ${offsetY}px)`; } } }); }
    function applyKenBurnsEffect(element, animationDuration) { if (!element) return; element.classList.remove('kenburns-active'); element.style.transition = ''; const scaleFactor = 1.15; const startsZoomed = Math.random() < 0.5; const startScale = startsZoomed ? scaleFactor : 1; const endScale = startsZoomed ? 1 : scaleFactor; const maxTranslateX = ((Math.max(startScale, endScale) - 1) / 2) * 50; const maxTranslateY = ((Math.max(startScale, endScale) - 1) / 2) * 50; const startX = (Math.random() * maxTranslateX * 2) - maxTranslateX; const startY = (Math.random() * maxTranslateY * 2) - maxTranslateY; const endX = (Math.random() * maxTranslateX * 2) - maxTranslateX; const endY = (Math.random() * maxTranslateY * 2) - maxTranslateY; const originX = Math.random() * 50 + 25; const originY = Math.random() * 50 + 25; element.style.transformOrigin = `${originX}% ${originY}%`; element.style.transform = `scale(${startScale}) translate(${startX}%, ${startY}%)`; void element.offsetWidth; element.style.setProperty('--kb-duration', `${animationDuration / 1000}s`); element.classList.add('kenburns-active'); element.style.transform = `scale(${endScale}) translate(${endX}%, ${endY}%)`; }
    function resetKenBurnsEffect(element) { if (!element) return; element.classList.remove('kenburns-active'); element.style.transition = 'none'; element.style.transform = 'scale(1) translate(0, 0)'; element.style.transformOrigin = 'center center'; void element.offsetWidth; element.style.transition = ''; }


    // --- Core Slideshow Logic ---
    function showNextMedia() {
        // Use the already destructured mediaItems
        if (isTransitioning || !mediaItems || mediaItems.length === 0) {
            // console.log("showNextMedia: Transitioning or no media items."); // Keep this less verbose
            if (!mediaItems || mediaItems.length === 0) {
                 if(slideshowTimeoutId) clearTimeout(slideshowTimeoutId); slideshowTimeoutId = null;
                 imageElement.classList.remove('active'); videoElement.classList.remove('active');
                 if(statusMessageDisplay) statusMessageDisplay.style.display = 'block';
            }
            return;
        }
        isTransitioning = true;
        if(statusMessageDisplay) statusMessageDisplay.style.display = 'none';

        if (slideshowTimeoutId) clearTimeout(slideshowTimeoutId);
        slideshowTimeoutId = null;

        currentMediaIndex = (currentMediaIndex + 1) % mediaItems.length;
        const currentItem = mediaItems[currentMediaIndex];
        const mediaUrl = `${mediaBaseUrl}${encodeURIComponent(currentItem.filename)}`;

        console.log(`[Slideshow] Showing media ${currentMediaIndex + 1}/${mediaItems.length}: ${currentItem.filename} (Type: ${currentItem.type})`);

        const activeElement = imageElement.classList.contains('active') ? imageElement : (videoElement.classList.contains('active') ? videoElement : null);
        if (activeElement) {
            activeElement.classList.remove('active');
            if (activeElement === imageElement) resetKenBurnsEffect(imageElement);
            if (activeElement === videoElement) videoElement.pause();
        }

        setTimeout(() => {
            if (currentItem.type === 'image') {
                videoElement.style.display = 'none';
                imageElement.style.display = 'block';
                imageElement.style.objectFit = imageScaling;
                imageElement.alt = currentItem.filename;
                const tempImg = new Image();
                tempImg.onload = () => {
                    imageElement.src = mediaUrl;
                    if (transitionEffect === 'kenburns') {
                        setTimeout(() => applyKenBurnsEffect(imageElement, imageDuration), 50);
                    }
                    imageElement.classList.add('active');
                    isTransitioning = false;
                    slideshowTimeoutId = setTimeout(showNextMedia, imageDuration);
                    preloadMedia((currentMediaIndex + 1) % mediaItems.length).catch(err => console.warn(`[Preload] Failed for next item`, err));
                };
                tempImg.onerror = () => {
                    console.error(`[Slideshow] Failed to load image: ${currentItem.filename}`);
                    imageElement.alt = `Error loading ${currentItem.filename}`;
                    imageElement.src = "";
                    imageElement.classList.remove('active');
                    isTransitioning = false;
                    slideshowTimeoutId = setTimeout(showNextMedia, 100);
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

                const canPlayHandler = () => {
                    videoElement.removeEventListener('canplay', canPlayHandler);
                    videoElement.removeEventListener('error', errorHandler);
                    videoElement.classList.add('active');
                    isTransitioning = false;
                    console.log(`[Slideshow] Video ready: ${currentItem.filename}`);
                    if (videoAutoplay) {
                         videoElement.play().catch(e => console.warn(`Autoplay prevented for ${currentItem.filename}:`, e));
                    }
                    if (videoLoop) {
                        console.log(`[Slideshow] Video looping, setting timeout: ${imageDuration}ms`);
                        slideshowTimeoutId = setTimeout(showNextMedia, imageDuration);
                    }
                    preloadMedia((currentMediaIndex + 1) % mediaItems.length).catch(err => console.warn(`[Preload] Failed for next item`, err));
                };

                const errorHandler = (e) => {
                    videoElement.removeEventListener('canplay', canPlayHandler);
                    videoElement.removeEventListener('error', errorHandler);
                    console.error(`[Slideshow] Failed to load video: ${currentItem.filename}`, e);
                    videoElement.classList.remove('active');
                    isTransitioning = false;
                    slideshowTimeoutId = setTimeout(showNextMedia, 100);
                };

                videoElement.addEventListener('canplay', canPlayHandler);
                videoElement.addEventListener('error', errorHandler);

            } else {
                console.warn(`[Slideshow] Unknown media type: ${currentItem.type}`);
                isTransitioning = false;
                slideshowTimeoutId = setTimeout(showNextMedia, 100);
            }
        }, 100);
    }

    // --- Event Listener for Non-Looping Videos Ending ---
    videoElement.addEventListener('ended', () => {
        if (!videoLoop && videoElement.classList.contains('active')) {
            console.log(`[Slideshow] Video ended: ${mediaItems[currentMediaIndex]?.filename}. Advancing.`);
            if (slideshowTimeoutId) clearTimeout(slideshowTimeoutId);
            slideshowTimeoutId = null;
            // Add a small delay before showing next to prevent abrupt cut
            setTimeout(showNextMedia, 50);
        } else if (videoLoop) {
             // console.log(`[Slideshow] Looping video ended, restarting/continuing loop.`); // Less verbose
        }
    });


    // --- Fullscreen and Interaction Logic --- (Keep existing functions: toggleFullScreen, handleDoubleTap, checkForConfigUpdate, handleFullscreenChange) ...
    function toggleFullScreen() { console.log("toggleFullScreen function called"); if (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement ) { if (document.documentElement.requestFullscreen) { document.documentElement.requestFullscreen(); } else if (document.documentElement.mozRequestFullScreen) { document.documentElement.mozRequestFullScreen(); } else if (document.documentElement.webkitRequestFullscreen) { document.documentElement.webkitRequestFullscreen(); } else if (document.documentElement.msRequestFullscreen) { document.documentElement.msRequestFullscreen(); } console.log("Requested fullscreen"); } else { if (document.exitFullscreen) { document.exitFullscreen(); } else if (document.mozCancelFullScreen) { document.mozCancelFullScreen(); } else if (document.webkitExitFullscreen) { document.webkitExitFullscreen(); } else if (document.msExitFullscreen) { document.msExitFullscreen(); } console.log("Exited fullscreen"); } }
    function handleDoubleTap(event) { console.log("Double tap detected"); const currentTime = new Date().getTime(); const tapLength = currentTime - lastTap; if (tapLength < doubleTapDelay && tapLength > 0) { console.log("Double tap confirmed, toggling fullscreen."); event.preventDefault(); toggleFullScreen(); } else { console.log("Single tap registered."); } lastTap = currentTime; }
    async function checkForConfigUpdate() { try { const response = await fetch('/api/config/check', { cache: 'no-store' }); if (!response.ok) { console.error(`Config check failed with status: ${response.status}`); return; } const data = await response.json(); const serverTimestamp = data.timestamp; if (typeof serverTimestamp === 'number' && typeof initialTimestamp === 'number' && Math.abs(serverTimestamp - initialTimestamp) > 0.01 && initialTimestamp !== 0) { console.log("Configuration change detected. Reloading page..."); if (slideshowTimeoutId) clearTimeout(slideshowTimeoutId); if (timeIntervalId) clearInterval(timeIntervalId); if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId); if (configCheckIntervalId) clearInterval(configCheckIntervalId); window.location.reload(true); } } catch (error) { console.error("Error during config check fetch:", error); } }
    function handleFullscreenChange() { const isFullscreen = !!(document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement); if (isFullscreen) { document.body.classList.add('fullscreen-active'); console.log("Entered fullscreen - hiding cursor."); } else { document.body.classList.remove('fullscreen-active'); console.log("Exited fullscreen - showing cursor."); } }


    // --- Initialization ---
    console.log("Starting Initialization Checks (v2)...");

    // *** Updated Check: Use the destructured mediaItems ***
    if (!mediaItems || mediaItems.length === 0) {
        // *** Updated Log Message ***
        console.log("No valid media items found in slideshowData during init.");
        if(statusMessageDisplay) statusMessageDisplay.style.display = 'block';
    } else {
         console.log(`Found ${mediaItems.length} media items. Starting slideshow.`);
         if(statusMessageDisplay) statusMessageDisplay.style.display = 'none';
         showNextMedia(); // Start the slideshow
    }

    // Initialize Widgets (No changes needed)
    if (timeEnabled && timeDisplay) { updateClock(); if (timeIntervalId) clearInterval(timeIntervalId); timeIntervalId = setInterval(updateClock, 1000); console.log("Time widget initialized."); }
    else { console.log("Time widget disabled or element not found."); if (timeDisplay) timeDisplay.textContent = ""; }
    if (rssConfig.enabled && rssTickerContainer && rssTickerContent) { let scrollDuration = '80s'; switch (rssConfig.scroll_speed) { case 'slow': scrollDuration = '120s'; break; case 'fast': scrollDuration = '50s'; break; default: scrollDuration = '80s'; break; } rssTickerContent.style.setProperty('--rss-scroll-duration', scrollDuration); console.log(`RSS scroll speed set to ${rssConfig.scroll_speed} (${scrollDuration})`); rssTickerContainer.style.display = ''; }
    else if (rssTickerContainer) { rssTickerContainer.style.display = 'none'; console.log("RSS Ticker disabled or container/content not found."); }
    if (watermarkConfig.enabled && watermarkElement) { setWatermarkPosition(); console.log("Watermark initialized."); }
    else { console.log("Watermark disabled or element not found."); }
    if (burnInConfig && burnInConfig.enabled && burnInConfig.elements && burnInConfig.elements.length > 0) { const shiftInterval = (burnInConfig.interval_seconds || 15) * 1000; if (shiftInterval > 0) { applyPixelShift(); if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId); pixelShiftIntervalId = setInterval(applyPixelShift, shiftInterval); console.log(`Burn-in prevention initialized with interval: ${shiftInterval}ms`); } else { console.warn("Burn-in prevention interval is zero or invalid. Disabling."); applyPixelShift(); } }
    else { console.log("Burn-in prevention disabled or no elements specified."); applyPixelShift(); }

    // --- Event Listeners (No changes needed) ---
    if (slideshowContainer) { slideshowContainer.addEventListener('touchstart', handleDoubleTap, { passive: false }); console.log("Touch listener added to slideshowContainer."); slideshowContainer.addEventListener('dblclick', (event) => { console.log("Double click detected on container"); event.preventDefault(); toggleFullScreen(); }); console.log("Double click listener added to slideshowContainer."); }
    else { console.error("Slideshow container not found for touch/dblclick listeners."); }
    document.addEventListener('keydown', (event) => { if (event.key === 'Enter' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'SELECT') { console.log("Enter key pressed, toggling fullscreen."); event.preventDefault(); toggleFullScreen(); } }); console.log("Keydown listener added to document.");
    document.addEventListener('fullscreenchange', handleFullscreenChange); document.addEventListener('mozfullscreenchange', handleFullscreenChange); document.addEventListener('webkitfullscreenchange', handleFullscreenChange); document.addEventListener('msfullscreenchange', handleFullscreenChange); handleFullscreenChange(); console.log("Fullscreen change listeners added.");

    // Start Config Polling (No changes needed)
    if (initialTimestamp !== null) { if (configCheckIntervalId) clearInterval(configCheckIntervalId); configCheckIntervalId = setInterval(checkForConfigUpdate, 30000); console.log(`Started config polling. Initial timestamp: ${initialTimestamp}`); }
    else { console.warn("Config polling disabled due to missing initial timestamp."); }

}); // End DOMContentLoaded
