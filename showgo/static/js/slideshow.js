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

    // Destructure data
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
    function preloadImage(src) {
        if (isPreloading) return Promise.resolve();
        isPreloading = true;
        // console.log("[Preload] Starting:", src); // Less verbose
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => { /*console.log("[Preload] Success:", src);*/ isPreloading = false; resolve(img); };
            img.onerror = (err) => { console.error("[Preload] Failed:", src, err); isPreloading = false; reject(err); };
            img.src = src;
        });
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
            if(timeIntervalId) clearInterval(timeIntervalId);
            timeIntervalId = null;
            timeDisplay.textContent = "??:??:??";
        }
    }

    function setWatermarkPosition() {
        if (!watermarkElement || !watermarkConfig.enabled) return;
        watermarkElement.style.transform = '';
        watermarkElement.className = `widget ${watermarkConfig.position || 'bottom-right'}`;
    }

    function applyPixelShift() {
        if (!burnInPrevention || !burnInPrevention.enabled || !burnInPrevention.elements || burnInPrevention.elements.length === 0) {
            if (pixelShiftIntervalId) { clearInterval(pixelShiftIntervalId); pixelShiftIntervalId = null; }
            Object.values(shiftableElementMap).forEach(element => { if (element) element.style.transform = ''; });
            return;
        }
        const strength = burnInPrevention.strength_pixels || 3;
        const offsetX = Math.floor(Math.random() * (2 * strength + 1)) - strength;
        const offsetY = Math.floor(Math.random() * (2 * strength + 1)) - strength;
        burnInPrevention.elements.forEach(elementId => {
            const element = shiftableElementMap[elementId];
            if (element) {
                if (elementId === 'rss') { element.style.transform = `translate(0px, ${offsetY}px)`; }
                else { element.style.transform = `translate(${offsetX}px, ${offsetY}px)`; }
            }
        });
    }

    function applyKenBurnsEffect(element, animationDuration) {
        if (!element) return;
        element.classList.remove('kenburns-active');
        element.style.transition = '';
        const scaleFactor = 1.15; const startsZoomed = Math.random() < 0.5; const startScale = startsZoomed ? scaleFactor : 1; const endScale = startsZoomed ? 1 : scaleFactor;
        const maxTranslateX = ((Math.max(startScale, endScale) - 1) / 2) * 50; const maxTranslateY = ((Math.max(startScale, endScale) - 1) / 2) * 50;
        const startX = (Math.random() * maxTranslateX * 2) - maxTranslateX; const startY = (Math.random() * maxTranslateY * 2) - maxTranslateY; const endX = (Math.random() * maxTranslateX * 2) - maxTranslateX; const endY = (Math.random() * maxTranslateY * 2) - maxTranslateY;
        const originX = Math.random() * 50 + 25; const originY = Math.random() * 50 + 25;
        element.style.transformOrigin = `${originX}% ${originY}%`; element.style.transform = `scale(${startScale}) translate(${startX}%, ${startY}%)`;
        void element.offsetWidth;
        element.style.setProperty('--kb-duration', `${animationDuration / 1000}s`); element.classList.add('kenburns-active'); element.style.transform = `scale(${endScale}) translate(${endX}%, ${endY}%)`;
        // console.log(`Ken Burns Applied: Start Scale=${startScale.toFixed(2)}, End Scale=${endScale.toFixed(2)}, Duration=${animationDuration}ms`);
    }

    function resetKenBurnsEffect(element) {
         if (!element) return;
         element.classList.remove('kenburns-active');
         element.style.transition = 'none';
         element.style.transform = 'scale(1) translate(0, 0)';
         element.style.transformOrigin = 'center center';
         void element.offsetWidth;
         element.style.transition = '';
         // console.log("Ken Burns effect reset");
    }

    function showNextImage() {
        if (!images || images.length === 0) {
             console.log("showNextImage: No images.");
             if(slideshowIntervalId) clearInterval(slideshowIntervalId); slideshowIntervalId = null;
             slideshowImageElement.style.opacity = 0;
             if(statusMessageDisplay) statusMessageDisplay.style.display = 'block';
             return;
        }
        if(statusMessageDisplay) statusMessageDisplay.style.display = 'none';

        currentImageIndex = (currentImageIndex + 1) % images.length;
        const nextImageFilename = images[currentImageIndex];
        const nextImageUrl = `${imageBaseUrl}${encodeURIComponent(nextImageFilename)}`;

        // console.log(`[Slideshow] Showing image ${currentImageIndex + 1}/${images.length}: ${nextImageFilename}`);

        const tempImg = new Image();
        tempImg.onload = () => {
            // console.log(`[Slideshow] Image loaded: ${nextImageFilename}`);
            resetKenBurnsEffect(slideshowImageElement);
            slideshowImageElement.src = nextImageUrl;
            slideshowImageElement.alt = nextImageFilename;
            slideshowImageElement.style.display = '';
            if (transitionEffect === 'kenburns') {
                setTimeout(() => applyKenBurnsEffect(slideshowImageElement, duration), 50);
            }
            slideshowImageElement.style.opacity = 1;
            // console.log(`[Slideshow] Fading in: ${nextImageFilename}`);
            const preloadIndex = (currentImageIndex + 1) % images.length;
            if (images.length > 1 && images[preloadIndex]) {
                 const preloadUrl = `${imageBaseUrl}${encodeURIComponent(images[preloadIndex])}`;
                 preloadImage(preloadUrl).catch(err => console.warn(`[Preload] Failed for next image: ${images[preloadIndex]}`, err));
            }
        };
        tempImg.onerror = () => {
            console.error(`[Slideshow] Failed to load image: ${nextImageFilename}`);
            slideshowImageElement.alt = `Error loading ${nextImageFilename}`;
            slideshowImageElement.src = "";
            slideshowImageElement.style.opacity = 0;
        };

        // console.log(`[Slideshow] Setting tempImg src: ${nextImageUrl}`);
        tempImg.src = nextImageUrl;

        slideshowImageElement.style.opacity = 0;
        // console.log("[Slideshow] Fading out previous image.");

    }

    function toggleFullScreen() {
        console.log("toggleFullScreen function called"); // DEBUG
        if (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement ) {
            if (document.documentElement.requestFullscreen) { document.documentElement.requestFullscreen(); }
            else if (document.documentElement.mozRequestFullScreen) { document.documentElement.mozRequestFullScreen(); }
            else if (document.documentElement.webkitRequestFullscreen) { document.documentElement.webkitRequestFullscreen(); }
            else if (document.documentElement.msRequestFullscreen) { document.documentElement.msRequestFullscreen(); }
             console.log("Requested fullscreen");
        } else {
            if (document.exitFullscreen) { document.exitFullscreen(); }
            else if (document.mozCancelFullScreen) { document.mozCancelFullScreen(); }
            else if (document.webkitExitFullscreen) { document.webkitExitFullscreen(); }
            else if (document.msExitFullscreen) { document.msExitFullscreen(); }
             console.log("Exited fullscreen");
        }
    }
    function handleDoubleTap(event) {
        console.log("Double tap detected"); // DEBUG
        const currentTime = new Date().getTime();
        const tapLength = currentTime - lastTap;
        if (tapLength < doubleTapDelay && tapLength > 0) {
            console.log("Double tap confirmed, toggling fullscreen."); // DEBUG
            event.preventDefault(); // Prevent zoom on double tap
            toggleFullScreen();
        } else {
             console.log("Single tap registered."); // DEBUG
        }
        lastTap = currentTime;
    }
    async function checkForConfigUpdate() {
        // console.log("Polling for config update..."); // Less verbose
        try {
            const response = await fetch('/api/config/check', { cache: 'no-store' });
            if (!response.ok) { console.error(`Config check failed with status: ${response.status}`); return; }
            const data = await response.json();
            const serverTimestamp = data.timestamp;
            // console.log(`Server timestamp: ${serverTimestamp}, Initial timestamp: ${initialTimestamp}`);
            if (typeof serverTimestamp === 'number' && typeof initialTimestamp === 'number' && Math.abs(serverTimestamp - initialTimestamp) > 0.01 && initialTimestamp !== 0) {
                 console.log("Configuration change detected. Reloading page...");
                 if (slideshowIntervalId) clearInterval(slideshowIntervalId);
                 if (timeIntervalId) clearInterval(timeIntervalId);
                 if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId);
                 if (configCheckIntervalId) clearInterval(configCheckIntervalId);
                 window.location.reload(true);
            } else {
                 // console.log("No configuration change detected.");
            }
        } catch (error) { console.error("Error during config check fetch:", error); }
    }
    function handleFullscreenChange() {
        const isFullscreen = !!(document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement);
        if (isFullscreen) { document.body.classList.add('fullscreen-active'); console.log("Entered fullscreen - hiding cursor."); }
        else { document.body.classList.remove('fullscreen-active'); console.log("Exited fullscreen - showing cursor."); }
    }

    // --- Initialization ---
    console.log("Starting Initialization...");

    if (!images || images.length === 0) {
        console.log("No images found in slideshowData during init.");
        if(statusMessageDisplay) statusMessageDisplay.style.display = 'block';
    } else {
         console.log(`Found ${images.length} images. Starting slideshow.`);
         if(statusMessageDisplay) statusMessageDisplay.style.display = 'none';
         showNextImage(); // Show first image
         if (images.length > 1) {
             if (slideshowIntervalId) clearInterval(slideshowIntervalId);
             slideshowIntervalId = setInterval(showNextImage, duration);
             console.log(`Slideshow interval started with duration: ${duration}ms`);
         } else {
             console.log("Only one image found, slideshow interval not started.");
         }
    }

    if (timeEnabled && timeDisplay) {
        updateClock();
        if (timeIntervalId) clearInterval(timeIntervalId);
        timeIntervalId = setInterval(updateClock, 1000);
        console.log("Time widget initialized.");
    } else {
         console.log("Time widget disabled or element not found.");
         if (timeDisplay) timeDisplay.textContent = "";
    }

    if (rssConfig.enabled && rssTickerContainer && rssTickerContent) {
         console.log("RSS Ticker is enabled.");
         let scrollDuration = '80s';
         switch (rssConfig.scroll_speed) {
             case 'slow': scrollDuration = '120s'; break;
             case 'fast': scrollDuration = '50s'; break;
             default: scrollDuration = '80s'; break;
         }
         rssTickerContent.style.setProperty('--rss-scroll-duration', scrollDuration);
         console.log(`RSS scroll speed set to ${rssConfig.scroll_speed} (${scrollDuration})`);
         rssTickerContainer.style.display = '';
    } else if (rssTickerContainer) {
         rssTickerContainer.style.display = 'none';
         console.log("RSS Ticker disabled or container/content not found.");
    }

    if (watermarkConfig.enabled && watermarkElement) {
        setWatermarkPosition(); console.log("Watermark initialized.");
    } else { console.log("Watermark disabled or element not found."); }

    if (burnInPrevention && burnInPrevention.enabled && burnInPrevention.elements && burnInPrevention.elements.length > 0) {
        const shiftInterval = (burnInPrevention.interval_seconds || 15) * 1000;
        if (shiftInterval > 0) {
            applyPixelShift();
            if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId);
            pixelShiftIntervalId = setInterval(applyPixelShift, shiftInterval);
            console.log(`Burn-in prevention initialized with interval: ${shiftInterval}ms`);
        } else { console.warn("Burn-in prevention interval is zero or invalid. Disabling."); applyPixelShift(); }
    } else { console.log("Burn-in prevention disabled or no elements specified."); applyPixelShift(); }

    // --- REVISED Event Listeners ---
    if (slideshowContainer) {
        // Touch listener on the container
        slideshowContainer.addEventListener('touchstart', handleDoubleTap, { passive: false });
        console.log("Touch listener added to slideshowContainer.");

        // Double-click listener ALSO on the container
        slideshowContainer.addEventListener('dblclick', (event) => {
             console.log("Double click detected on container"); // DEBUG
             event.preventDefault(); // Prevent default double-click behavior (like text selection)
             toggleFullScreen();
        });
         console.log("Double click listener added to slideshowContainer.");
    } else {
        console.error("Slideshow container not found for touch/dblclick listeners.");
    }

    // Keydown listener on the document
    document.addEventListener('keydown', (event) => {
        console.log(`Keydown detected: ${event.key}`); // DEBUG
        if (event.key === 'Enter' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'SELECT') {
             console.log("Enter key pressed, toggling fullscreen."); // DEBUG
             event.preventDefault();
             toggleFullScreen();
        }
    });
    console.log("Keydown listener added to document.");

    // Fullscreen change listeners (no change here)
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('msfullscreenchange', handleFullscreenChange);
    handleFullscreenChange(); // Initial check
    console.log("Fullscreen change listeners added.");
    // --- END Event Listeners ---

    // Start Config Polling
    if (initialTimestamp !== null) {
        if (configCheckIntervalId) clearInterval(configCheckIntervalId);
        configCheckIntervalId = setInterval(checkForConfigUpdate, 30000);
        console.log(`Started config polling. Initial timestamp: ${initialTimestamp}`);
    } else { console.warn("Config polling disabled due to missing initial timestamp."); }

}); // End DOMContentLoaded
