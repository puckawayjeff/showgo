// static/js/slideshow.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Loaded. Initializing slideshow script...");

    // --- DOM Element References ---
    const slideshowContainer = document.getElementById('slideshow-container');
    const slideshowImageElement = document.getElementById('slideshow-image');
    const timeWidget = document.getElementById('time-widget');
    const timeDisplay = document.getElementById('time-display');
    const rssTickerContainer = document.getElementById('rss-ticker-container');
    const rssTickerContent = document.getElementById('rss-ticker-content');
    const watermarkElement = document.getElementById('watermark');
    const weatherWidget = document.getElementById('weather-widget');
    const statusMessageDisplay = document.getElementById('status-message-display');

    // --- Check if necessary data and elements exist ---
    if (!slideshowContainer || !slideshowImageElement || typeof slideshowData === 'undefined' || slideshowData === null) {
        console.error("Slideshow container, image element, or data not found/initialized. Exiting.", { container: !!slideshowContainer, imageElement: !!slideshowImageElement, data: slideshowData });
        if (statusMessageDisplay) { statusMessageDisplay.innerHTML = '<p style="color: red;">Error: Slideshow failed to initialize.</p>'; }
        else if (slideshowContainer) { slideshowContainer.innerHTML = '<p id="status-message-display" style="color: red; text-align: center; padding-top: 20%;">Error: Slideshow failed to initialize.</p>'; }
        return;
    }
    console.log("Slideshow data found:", slideshowData);

    // Destructure data from the validated slideshowData object
    const images = slideshowData.images || [];
    const duration = slideshowData.duration || 10000;
    const transitionEffect = slideshowData.transitionEffect || 'fade';
    const imageBaseUrl = slideshowData.imageBaseUrl || '';
    const imageScaling = slideshowData.imageScaling || 'cover';
    const widgets = slideshowData.widgets || {};
    const burnInPrevention = slideshowData.burnInPrevention || {};
    const initialTimestamp = slideshowData.initialTimestamp || 0;

    const timeEnabled = widgets.time ?? true;
    const watermarkConfig = widgets.watermark || {};
    const rssConfig = widgets.rss || {};

    let currentImageIndex = -1;
    let slideshowIntervalId = null;
    let timeIntervalId = null;
    let pixelShiftIntervalId = null;
    let configCheckIntervalId = null;
    let isPreloading = false;

    const doubleTapDelay = 400;
    let lastTap = 0;

    const shiftableElementMap = { 'watermark': watermarkElement, 'time': timeDisplay, 'weather': weatherWidget, 'rss': rssTickerContainer, 'status': statusMessageDisplay };

    // --- Helper Functions ---
    function preloadImage(src) { /* (no change) */
        if (isPreloading) return Promise.resolve();
        isPreloading = true; console.log("Preloading:", src);
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => { console.log("Preloaded successfully:", src); isPreloading = false; resolve(img); };
            img.onerror = (err) => { console.error("Failed to preload:", src, err); isPreloading = false; reject(err); };
            img.src = src;
        });
    }
    function updateClock() { /* (no change) */
        if (!timeDisplay) return;
        const now = new Date(); const hours = String(now.getHours()).padStart(2, '0'); const minutes = String(now.getMinutes()).padStart(2, '0'); const seconds = String(now.getSeconds()).padStart(2, '0');
        timeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
    }
    function setWatermarkPosition() { /* (no change) */
        if (!watermarkElement || !watermarkConfig.enabled) return;
        watermarkElement.style.transform = ''; watermarkElement.className = `widget ${watermarkConfig.position || 'bottom-right'}`;
    }

    // --- MODIFIED applyPixelShift ---
    function applyPixelShift() {
        // Reset logic remains the same
        if (!burnInPrevention || !burnInPrevention.enabled || !burnInPrevention.elements || burnInPrevention.elements.length === 0) {
            if (pixelShiftIntervalId) { clearInterval(pixelShiftIntervalId); pixelShiftIntervalId = null; }
            Object.values(shiftableElementMap).forEach(element => {
                if (element) element.style.transform = '';
            });
            return;
        }

        // Calculate random offsets
        const strength = burnInPrevention.strength_pixels || 3;
        const offsetX = Math.floor(Math.random() * (2 * strength + 1)) - strength;
        const offsetY = Math.floor(Math.random() * (2 * strength + 1)) - strength;

        // Apply shift to selected elements
        burnInPrevention.elements.forEach(elementId => {
            const element = shiftableElementMap[elementId];
            if (element) {
                // *** Check if the element is the RSS ticker ***
                if (elementId === 'rss') {
                    // Only apply vertical shift (translateY) to RSS ticker
                    element.style.transform = `translate(0px, ${offsetY}px)`;
                     // console.log(`Applying vertical shift to RSS: Y=${offsetY}px`); // Optional debug
                } else {
                    // Apply both X and Y shift to other elements
                    element.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
                }
            }
        });
    }
    // --- END MODIFIED applyPixelShift ---


    // --- Ken Burns Effect Function ---
    function applyKenBurnsEffect(element, animationDuration) { /* (no change) */
        if (!element) return;
        element.classList.remove('kenburns-active'); element.style.transition = '';
        const scaleFactor = 1.15; const startsZoomed = Math.random() < 0.5; const startScale = startsZoomed ? scaleFactor : 1; const endScale = startsZoomed ? 1 : scaleFactor;
        const maxTranslateX = ((Math.max(startScale, endScale) - 1) / 2) * 50; const maxTranslateY = ((Math.max(startScale, endScale) - 1) / 2) * 50;
        const startX = (Math.random() * maxTranslateX * 2) - maxTranslateX; const startY = (Math.random() * maxTranslateY * 2) - maxTranslateY; const endX = (Math.random() * maxTranslateX * 2) - maxTranslateX; const endY = (Math.random() * maxTranslateY * 2) - maxTranslateY;
        const originX = Math.random() * 50 + 25; const originY = Math.random() * 50 + 25;
        element.style.transformOrigin = `${originX}% ${originY}%`; element.style.transform = `scale(${startScale}) translate(${startX}%, ${startY}%)`;
        void element.offsetWidth;
        element.style.setProperty('--kb-duration', `${animationDuration / 1000}s`); element.classList.add('kenburns-active'); element.style.transform = `scale(${endScale}) translate(${endX}%, ${endY}%)`;
        console.log(`Ken Burns Applied: Start Scale=${startScale.toFixed(2)}, End Scale=${endScale.toFixed(2)}, Duration=${animationDuration}ms`);
    }
    function resetKenBurnsEffect(element) { /* (no change) */
         if (!element) return;
         element.classList.remove('kenburns-active'); element.style.transition = 'none'; element.style.transform = 'scale(1) translate(0, 0)'; element.style.transformOrigin = 'center center';
         void element.offsetWidth; element.style.transition = ''; console.log("Ken Burns effect reset");
    }
    // --- END Ken Burns ---

    // --- showNextImage function ---
    function showNextImage() { /* (no change) */
        if (!images || images.length === 0) { console.log("showNextImage called, but no images available."); if(slideshowIntervalId) clearInterval(slideshowIntervalId); slideshowIntervalId = null; slideshowImageElement.style.opacity = 0; if(statusMessageDisplay) statusMessageDisplay.innerHTML = '<p>No valid images found for slideshow.</p>'; return; }
        currentImageIndex = (currentImageIndex + 1) % images.length; const nextImageFilename = images[currentImageIndex]; const nextImageUrl = `${imageBaseUrl}${encodeURIComponent(nextImageFilename)}`;
        console.log(`Showing image ${currentImageIndex + 1}/${images.length}: ${nextImageFilename}`);
        slideshowImageElement.style.opacity = 0;
        setTimeout(() => {
            resetKenBurnsEffect(slideshowImageElement);
            slideshowImageElement.src = nextImageUrl; slideshowImageElement.alt = nextImageFilename; slideshowImageElement.style.display = '';
            slideshowImageElement.onerror = () => { console.error(`Failed to load image: ${nextImageFilename}`); slideshowImageElement.alt = `Error loading ${nextImageFilename}`; };
             const tempImg = new Image();
             tempImg.onload = () => {
                 slideshowImageElement.src = nextImageUrl; slideshowImageElement.style.opacity = 1;
                 if (transitionEffect === 'kenburns') { setTimeout(() => applyKenBurnsEffect(slideshowImageElement, duration), 50); }
                 const preloadIndex = (currentImageIndex + 1) % images.length;
                 if (images.length > 1 && images[preloadIndex]) { const preloadUrl = `${imageBaseUrl}${encodeURIComponent(images[preloadIndex])}`; preloadImage(preloadUrl).catch(err => console.warn(`Failed to preload image: ${images[preloadIndex]}`, err)); }
             };
             tempImg.onerror = slideshowImageElement.onerror; tempImg.src = nextImageUrl;
        }, 1000);
    }
    // --- END showNextImage ---

    function toggleFullScreen() { /* (no change) */
        if (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement ) { if (document.documentElement.requestFullscreen) { document.documentElement.requestFullscreen(); } else if (document.documentElement.mozRequestFullScreen) { document.documentElement.mozRequestFullScreen(); } else if (document.documentElement.webkitRequestFullscreen) { document.documentElement.webkitRequestFullscreen(); } else if (document.documentElement.msRequestFullscreen) { document.documentElement.msRequestFullscreen(); } console.log("Requested fullscreen"); } else { if (document.exitFullscreen) { document.exitFullscreen(); } else if (document.mozCancelFullScreen) { document.mozCancelFullScreen(); } else if (document.webkitExitFullscreen) { document.webkitExitFullscreen(); } else if (document.msExitFullscreen) { document.msExitFullscreen(); } console.log("Exited fullscreen"); }
    }
    function handleDoubleTap(event) { /* (no change) */
        const currentTime = new Date().getTime(); const tapLength = currentTime - lastTap; if (tapLength < doubleTapDelay && tapLength > 0) { event.preventDefault(); toggleFullScreen(); } lastTap = currentTime;
    }
    async function checkForConfigUpdate() { /* (no change) */
        console.log("Polling for config update..."); try { const response = await fetch('/api/config/check', { cache: 'no-store' }); if (!response.ok) { console.error(`Config check failed with status: ${response.status}`); return; } const data = await response.json(); const serverTimestamp = data.timestamp; console.log(`Server timestamp: ${serverTimestamp}, Initial timestamp: ${initialTimestamp}`); if (typeof serverTimestamp === 'number' && typeof initialTimestamp === 'number' && Math.abs(serverTimestamp - initialTimestamp) > 0.01 && initialTimestamp !== 0) { console.log("Configuration change detected. Reloading page..."); if (slideshowIntervalId) clearInterval(slideshowIntervalId); if (timeIntervalId) clearInterval(timeIntervalId); if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId); if (configCheckIntervalId) clearInterval(configCheckIntervalId); window.location.reload(true); } else { console.log("No configuration change detected."); } } catch (error) { console.error("Error during config check fetch:", error); }
    }
    function handleFullscreenChange() { /* (no change) */
        const isFullscreen = !!(document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement); if (isFullscreen) { document.body.classList.add('fullscreen-active'); console.log("Entered fullscreen - hiding cursor."); } else { document.body.classList.remove('fullscreen-active'); console.log("Exited fullscreen - showing cursor."); }
    }

    // --- Initialization ---
    console.log("Starting Initialization...");
    if (!images || images.length === 0) { console.log("No images found in slideshowData."); if(statusMessageDisplay) statusMessageDisplay.style.display = 'block'; if(slideshowIntervalId) clearInterval(slideshowIntervalId); slideshowIntervalId = null; }
    else {
         console.log(`Found ${images.length} images. Starting slideshow.`); if(statusMessageDisplay) statusMessageDisplay.style.display = 'none';
         showNextImage(); // Show first image
         if (images.length > 1) { slideshowIntervalId = setInterval(showNextImage, duration); console.log(`Slideshow interval started with duration: ${duration}ms`); }
         else { console.log("Only one image found, slideshow interval not started."); }
    }
    if (timeEnabled && timeDisplay) { updateClock(); timeIntervalId = setInterval(updateClock, 1000); console.log("Time widget initialized."); }
    else { console.log("Time widget disabled or element not found."); }
    if (rssConfig.enabled && rssTickerContainer) { console.log("RSS Ticker is enabled (content rendered by server)."); }
    else if (rssTickerContainer) { rssTickerContainer.style.display = 'none'; console.log("RSS Ticker disabled or container not found."); }
    if (watermarkConfig.enabled && watermarkElement) { setWatermarkPosition(); console.log("Watermark initialized."); }
    else { console.log("Watermark disabled or element not found."); }
    if (burnInPrevention && burnInPrevention.enabled && burnInPrevention.elements && burnInPrevention.elements.length > 0) { const shiftInterval = (burnInPrevention.interval_seconds || 15) * 1000; if (shiftInterval > 0) { applyPixelShift(); pixelShiftIntervalId = setInterval(applyPixelShift, shiftInterval); console.log(`Burn-in prevention initialized with interval: ${shiftInterval}ms`); } else { console.warn("Burn-in prevention interval is zero or invalid. Disabling."); applyPixelShift(); } }
    else { console.log("Burn-in prevention disabled or no elements specified."); applyPixelShift(); }
    slideshowContainer.addEventListener('touchstart', handleDoubleTap, { passive: false }); document.body.addEventListener('dblclick', toggleFullScreen); document.addEventListener('keydown', (event) => { if (event.key === 'Enter' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'SELECT') { event.preventDefault(); toggleFullScreen(); } }); document.addEventListener('fullscreenchange', handleFullscreenChange); document.addEventListener('mozfullscreenchange', handleFullscreenChange); document.addEventListener('webkitfullscreenchange', handleFullscreenChange); document.addEventListener('msfullscreenchange', handleFullscreenChange); handleFullscreenChange(); console.log("Event listeners added.");
    if (initialTimestamp !== null) { configCheckIntervalId = setInterval(checkForConfigUpdate, 30000); console.log(`Started config polling. Initial timestamp: ${initialTimestamp}`); }
    else { console.warn("Config polling disabled due to missing initial timestamp."); }

}); // End DOMContentLoaded
