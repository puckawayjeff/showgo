// static/js/slideshow.js

document.addEventListener('DOMContentLoaded', () => {

  // --- DOM Element References ---
  const slideshowContainer = document.getElementById('slideshow-container');
  const timeWidget = document.getElementById('time-widget');
  const rssTickerContainer = document.getElementById('rss-ticker-container');
  const rssTickerContent = document.getElementById('rss-ticker-content');
  const watermarkElement = document.getElementById('watermark');
  const weatherWidget = document.getElementById('weather-widget');
  const statusMessageDisplay = document.getElementById('status-message-display');

  // --- Check if necessary data and elements exist ---
  if (!slideshowContainer || typeof slideshowData === 'undefined') {
      console.error("Slideshow container or data not found. Exiting.");
      if (slideshowContainer) {
          slideshowContainer.innerHTML = '<p id="status-message-display" style="color: red; text-align: center; padding-top: 20%;">Error: Slideshow data missing.</p>';
      }
      return;
  }

  // Destructure data from embedded object
  const { images, duration, transitionEffect, imageBaseUrl, imageScaling, widgets, burnInPrevention, initialTimestamp } = slideshowData;
  const { time: timeEnabled, watermark: watermarkConfig, rss: rssConfig } = widgets;

  let currentImageIndex = 0;
  let imageElements = [];
  let slideshowIntervalId = null;
  let timeIntervalId = null;
  let pixelShiftIntervalId = null;
  let configCheckIntervalId = null;

  const doubleTapDelay = 400;
  let lastTap = 0;

  const shiftableElementMap = {
      'watermark': watermarkElement, 'time': timeWidget,
      'weather': weatherWidget, 'rss': rssTickerContainer,
      'status': statusMessageDisplay
  };

  // --- Helper Functions ---
  function preloadImage(src) { /* (Keep same) */
      return new Promise((resolve, reject) => {
          const img = new Image();
          img.onload = () => resolve(img);
          img.onerror = reject;
          img.src = src;
      });
  }
  function updateClock() { /* (Keep same) */
      if (!timeWidget) return;
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');
      timeWidget.textContent = `${hours}:${minutes}:${seconds}`;
  }
  function setWatermarkPosition() { /* (Keep same) */
      if (!watermarkElement || !watermarkConfig.enabled) return;
      watermarkElement.style.top = 'auto'; watermarkElement.style.bottom = 'auto';
      watermarkElement.style.left = 'auto'; watermarkElement.style.right = 'auto';
      watermarkElement.style.transform = '';
      switch (watermarkConfig.position) {
          case 'top-left': watermarkElement.style.top = '10px'; watermarkElement.style.left = '10px'; break;
          case 'top-right': watermarkElement.style.top = '10px'; watermarkElement.style.right = '10px'; break;
          case 'bottom-left': watermarkElement.style.bottom = '10px'; watermarkElement.style.left = '10px'; break;
          case 'center':
               watermarkElement.style.top = '50%'; watermarkElement.style.left = '50%';
               requestAnimationFrame(() => {
                   const rect = watermarkElement.getBoundingClientRect();
                   if (rect.width > 0 && rect.height > 0) {
                      watermarkElement.style.transform = `translate(-${rect.width / 2}px, -${rect.height / 2}px)`;
                   }
               }); break;
          case 'bottom-right': default: watermarkElement.style.bottom = '10px'; watermarkElement.style.right = '10px'; break;
      }
  }
  function applyPixelShift() { /* (Keep same) */
      if (!burnInPrevention || !burnInPrevention.enabled || burnInPrevention.elements.length === 0) {
          if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId);
          pixelShiftIntervalId = null;
          Object.values(shiftableElementMap).forEach(element => {
               if (element) element.style.transform = '';
          });
          if (watermarkElement && watermarkConfig.enabled && watermarkConfig.position === 'center') {
               setWatermarkPosition();
          }
          return;
      }
      const strength = burnInPrevention.strength_pixels || 3;
      const offsetX = Math.floor(Math.random() * (2 * strength + 1)) - strength;
      const offsetY = Math.floor(Math.random() * (2 * strength + 1)) - strength;
      burnInPrevention.elements.forEach(elementId => {
          const element = shiftableElementMap[elementId];
          if (element) {
              let baseTransform = '';
              if (elementId === 'watermark' && watermarkConfig.position === 'center') {
                  const rect = element.getBoundingClientRect();
                  if (rect.width > 0) { baseTransform = `translate(-${rect.width / 2}px, -${rect.height / 2}px) `; }
              }
               const effectiveOffsetY = (elementId === 'rss') ? 0 : offsetY;
               element.style.transform = `${baseTransform}translate(${offsetX}px, ${effectiveOffsetY}px)`;
          }
      });
  }
  function showNextImage() { /* (Keep same) */
      if (images.length === 0) return;
      const currentActive = slideshowContainer.querySelector('.slide-image.active');
      if (currentActive) { currentActive.classList.remove('active'); }
      currentImageIndex = (currentImageIndex + 1) % images.length;
      if (imageElements[currentImageIndex]) {
           imageElements[currentImageIndex].classList.add('active');
      } else { console.error(`Image element at index ${currentImageIndex} not found.`); }
      const nextIndex = (currentImageIndex + 1) % images.length;
      if (images[nextIndex]) {
           const nextImageUrl = `${imageBaseUrl}${encodeURIComponent(images[nextIndex])}`;
           preloadImage(nextImageUrl).catch(err => console.warn(`Failed to preload image: ${images[nextIndex]}`, err));
      }
  }
  function toggleFullScreen() { /* (Keep same) */
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
  function handleDoubleTap(event) { /* (Keep same) */
      const currentTime = new Date().getTime();
      const tapLength = currentTime - lastTap;
      if (tapLength < doubleTapDelay && tapLength > 0) {
          event.preventDefault();
          toggleFullScreen();
      }
      lastTap = currentTime;
  }
  async function checkForConfigUpdate() { /* (Keep same) */
      try {
          const response = await fetch('/api/config/check', { cache: 'no-store' });
          if (!response.ok) { console.error(`Config check failed with status: ${response.status}`); return; }
          const data = await response.json();
          const serverTimestamp = data.timestamp;
          if (serverTimestamp && initialTimestamp && Math.abs(serverTimestamp - initialTimestamp) > 0.01) {
               console.log("Configuration change detected. Reloading page...");
               if (slideshowIntervalId) clearInterval(slideshowIntervalId);
               if (timeIntervalId) clearInterval(timeIntervalId);
               if (pixelShiftIntervalId) clearInterval(pixelShiftIntervalId);
               if (configCheckIntervalId) clearInterval(configCheckIntervalId);
               window.location.reload(true);
          }
      } catch (error) { console.error("Error during config check fetch:", error); }
  }

  // --- NEW: Fullscreen Change Handler ---
  function handleFullscreenChange() {
      const isFullscreen = !!(document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement);
      if (isFullscreen) {
          document.body.classList.add('fullscreen-active');
          console.log("Entered fullscreen - hiding cursor.");
      } else {
          document.body.classList.remove('fullscreen-active');
          console.log("Exited fullscreen - showing cursor.");
      }
  }
  // ------------------------------------


  // --- Initialization ---
  // 1. Handle No Images
  if (images.length === 0) {
      if(statusMessageDisplay) statusMessageDisplay.innerHTML = '<p>No images uploaded.</p>';
      else slideshowContainer.innerHTML = '<p id="status-message-display" style="color: #ccc; text-align: center; padding-top: 20%;">No images uploaded.</p>';
  } else {
      // 2. Create and append image elements
      images.forEach((filename, index) => {
          const img = document.createElement('img');
          img.src = `${imageBaseUrl}${encodeURIComponent(filename)}`;
          img.alt = filename;
          img.classList.add('slide-image');
          img.style.objectFit = (imageScaling === 'contain') ? 'contain' : 'cover';
          img.onerror = () => { console.error(`Failed to load image: ${filename}`); img.alt = `Error loading ${filename}`; img.style.display = 'none'; };
          slideshowContainer.appendChild(img);
          imageElements.push(img);
      });
      // 3. Show the first image
       if (imageElements[0]) {
            imageElements[0].classList.add('active');
            if (images.length > 1) { preloadImage(`${imageBaseUrl}${encodeURIComponent(images[1])}`).catch(err => console.warn(`Failed to preload image: ${images[1]}`, err)); }
       } else if (images.length > 0) { console.error("First image element could not be found."); }
      // 4. Start the slideshow interval
      slideshowIntervalId = setInterval(showNextImage, duration);
  }

  // 5. Initialize Time Widget
  if (timeEnabled && timeWidget) { updateClock(); timeIntervalId = setInterval(updateClock, 1000); }

  // 6. Initialize RSS Ticker
  if (rssConfig.enabled && rssTickerContent && rssConfig.headlines && rssConfig.headlines.length > 0) {
      const tickerText = rssConfig.headlines.map(h => h.title).join(' <span class="text-gray-400 mx-2">&bull;</span> ');
      rssTickerContent.innerHTML = `<span>${tickerText}</span><span>${tickerText}</span>`;
  } else if (rssTickerContent) {
      rssTickerContent.innerHTML = '';
  }

  // 7. Initialize Watermark Position
  if (watermarkConfig.enabled && watermarkElement) { setWatermarkPosition(); }
  // 8. Initialize Burn-In Prevention
  if (burnInPrevention && burnInPrevention.enabled) {
      const shiftInterval = (burnInPrevention.interval_seconds || 15) * 1000;
      pixelShiftIntervalId = setInterval(applyPixelShift, shiftInterval);
      applyPixelShift();
  } else {
       applyPixelShift();
  }

  // --- UPDATED: Add Event Listeners ---
  // Double Tap (Touch)
  slideshowContainer.addEventListener('touchstart', handleDoubleTap);
  // Double Click (Mouse) - Attach to body or container
  document.body.addEventListener('dblclick', toggleFullScreen);
  // Enter Key (Keyboard) - Attach to document
  document.addEventListener('keydown', (event) => {
      // Check if Enter key was pressed and maybe if no input field has focus
      if (event.key === 'Enter' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'SELECT') {
           event.preventDefault(); // Prevent default Enter behavior (like submitting forms if any existed)
           toggleFullScreen();
      }
  });
  // Listen for actual fullscreen changes (including Esc key)
  document.addEventListener('fullscreenchange', handleFullscreenChange);
  document.addEventListener('mozfullscreenchange', handleFullscreenChange);
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
  document.addEventListener('msfullscreenchange', handleFullscreenChange);
  // Initial check in case page loads in fullscreen
  handleFullscreenChange();
  // ------------------------------------

  // 10. Start Config Polling
  configCheckIntervalId = setInterval(checkForConfigUpdate, 30000);
  console.log(`Started config polling. Initial timestamp: ${initialTimestamp}`);


}); // End DOMContentLoaded
