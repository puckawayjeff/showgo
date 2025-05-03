// static/js/slideshow.js

// Wait for the DOM to be fully loaded before running scripts
document.addEventListener('DOMContentLoaded', () => {

  // --- DOM Element References ---
  const slideshowContainer = document.getElementById('slideshow-container');
  const timeWidget = document.getElementById('time-widget');
  const rssWidget = document.getElementById('rss-widget');
  const rssList = rssWidget ? rssWidget.querySelector('ul') : null;
  const watermarkElement = document.getElementById('watermark');

  // --- Check if necessary data and elements exist ---
  if (!slideshowContainer || typeof slideshowData === 'undefined') {
    console.error("Slideshow container or data not found. Exiting.");
    // Optionally display an error message on the page
    if (slideshowContainer) {
      slideshowContainer.innerHTML = '<p style="color: red; text-align: center; padding-top: 20%;">Error: Slideshow data missing.</p>';
    }
    return; // Stop execution if essential parts are missing
  }

  const { images, duration, transitionEffect, imageBaseUrl, widgets } = slideshowData;
  const { time: timeEnabled, watermark: watermarkConfig, rss: rssConfig } = widgets;

  let currentImageIndex = 0;
  let imageElements = []; // To hold the created image elements
  let rssIndex = 0;
  let rssIntervalId = null;
  let slideshowIntervalId = null;
  let timeIntervalId = null;
  let watermarkIntervalId = null;

  // --- Helper Functions ---
  function preloadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = src;
    });
  }

  function updateClock() {
    if (!timeWidget) return;
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    timeWidget.textContent = `${hours}:${minutes}:${seconds}`;
  }

  function cycleRssHeadline() {
    if (!rssList || !rssConfig.enabled || !rssConfig.headlines || rssConfig.headlines.length === 0) {
      // Stop cycling if RSS is disabled or no headlines
      if (rssIntervalId) clearInterval(rssIntervalId);
      rssIntervalId = null;
      return;
    }
    // Cycle through headlines every 15 seconds (adjust as needed)
    rssIndex = (rssIndex + 1) % rssConfig.headlines.length;
    rssList.innerHTML = `<li>${rssConfig.headlines[rssIndex].title}</li>`;
  }

  function setWatermarkPosition() {
    if (!watermarkElement || !watermarkConfig.enabled) return;

    // Reset styles first
    watermarkElement.style.top = 'auto';
    watermarkElement.style.bottom = 'auto';
    watermarkElement.style.left = 'auto';
    watermarkElement.style.right = 'auto';
    watermarkElement.style.transform = ''; // Reset transform for center

    switch (watermarkConfig.position) {
      case 'top-left':
        watermarkElement.style.top = '10px';
        watermarkElement.style.left = '10px';
        break;
      case 'top-right':
        watermarkElement.style.top = '10px';
        watermarkElement.style.right = '10px';
        break;
      case 'bottom-left':
        watermarkElement.style.bottom = '10px';
        watermarkElement.style.left = '10px';
        break;
      case 'center':
        watermarkElement.style.top = '50%';
        watermarkElement.style.left = '50%';
        // Adjust for element size to truly center
        // Get dimensions *after* text content is set
        requestAnimationFrame(() => { // Ensure text is rendered
          const rect = watermarkElement.getBoundingClientRect();
          watermarkElement.style.transform = `translate(-${rect.width / 2}px, -${rect.height / 2}px)`;
        });
        break;
      case 'bottom-right':
      default:
        watermarkElement.style.bottom = '10px';
        watermarkElement.style.right = '10px';
        break;
    }
  }

  function moveWatermark() {
    if (!watermarkElement || !watermarkConfig.enabled || !watermarkConfig.move) {
      if (watermarkIntervalId) clearInterval(watermarkIntervalId);
      watermarkIntervalId = null;
      return; // Stop if not enabled or not moving
    }

    // Simple random movement within a small range (e.g., +/- 5px)
    // Apply this relative to the base position set by setWatermarkPosition
    const offsetX = Math.floor(Math.random() * 11) - 5; // -5 to +5 px
    const offsetY = Math.floor(Math.random() * 11) - 5; // -5 to +5 px

    // Use transform for movement to avoid layout shifts if possible
    // Combine with centering transform if needed
    let baseTransform = '';
    if (watermarkConfig.position === 'center') {
      const rect = watermarkElement.getBoundingClientRect();
      if (rect.width > 0) { // Ensure element has dimensions
        baseTransform = `translate(-${rect.width / 2}px, -${rect.height / 2}px) `;
      }
    }
    watermarkElement.style.transform = `${baseTransform}translate(${offsetX}px, ${offsetY}px)`;

  }

  function showNextImage() {
    if (images.length === 0) return; // Do nothing if no images

    // Remove 'active' class from the current image (if any)
    const currentActive = slideshowContainer.querySelector('.slide-image.active');
    if (currentActive) {
      currentActive.classList.remove('active');
    }

    // Determine the next image index
    // Note: imageOrder is already applied server-side, so we just cycle sequentially here
    currentImageIndex = (currentImageIndex + 1) % images.length;

    // Add 'active' class to the new image
    if (imageElements[currentImageIndex]) {
      imageElements[currentImageIndex].classList.add('active');
    } else {
      console.error(`Image element at index ${currentImageIndex} not found.`);
    }

    // --- Preload the *next* image after the current one ---
    // This helps ensure smoother transitions
    const nextIndex = (currentImageIndex + 1) % images.length;
    if (images[nextIndex]) {
      const nextImageUrl = `${imageBaseUrl}${encodeURIComponent(images[nextIndex])}`;
      preloadImage(nextImageUrl).catch(err => console.warn(`Failed to preload image: ${images[nextIndex]}`, err));
    }
  }


  // --- Initialization ---

  // 1. Handle No Images
  if (images.length === 0) {
    slideshowContainer.innerHTML = '<p style="color: #ccc; text-align: center; padding-top: 20%;">No images uploaded.</p>';
    // Still start widgets if enabled
  } else {
    // 2. Create and append image elements (initially hidden)
    images.forEach((filename, index) => {
      const img = document.createElement('img');
      img.src = `${imageBaseUrl}${encodeURIComponent(filename)}`; // Ensure filename is URL-encoded
      img.alt = filename;
      img.classList.add('slide-image');
      // Add error handling for individual images
      img.onerror = () => {
        console.error(`Failed to load image: ${filename}`);
        img.alt = `Error loading ${filename}`;
        // Optionally replace src with a placeholder or hide the element
        // img.src = '/static/images/image-error-placeholder.png';
        img.style.display = 'none'; // Hide broken image element
      };
      slideshowContainer.appendChild(img);
      imageElements.push(img); // Store reference
    });

    // 3. Show the first image immediately
    if (imageElements[0]) {
      imageElements[0].classList.add('active');
      // Preload the second image right away
      if (images.length > 1) {
        preloadImage(`${imageBaseUrl}${encodeURIComponent(images[1])}`)
          .catch(err => console.warn(`Failed to preload image: ${images[1]}`, err));
      }
    } else if (images.length > 0) {
      console.error("First image element could not be found after creation.");
    }


    // 4. Start the slideshow interval
    slideshowIntervalId = setInterval(showNextImage, duration);
  }


  // 5. Initialize Time Widget (if enabled)
  if (timeEnabled && timeWidget) {
    updateClock(); // Initial call
    timeIntervalId = setInterval(updateClock, 1000); // Update every second
  }

  // 6. Initialize RSS Widget (if enabled)
  if (rssConfig.enabled && rssList && rssConfig.headlines && rssConfig.headlines.length > 1) {
    // Start cycling only if more than one headline
    rssIntervalId = setInterval(cycleRssHeadline, 15000); // Cycle every 15 seconds
  }

  // 7. Initialize Watermark (if enabled)
  if (watermarkConfig.enabled && watermarkElement) {
    setWatermarkPosition(); // Set initial position
    if (watermarkConfig.move) {
      // Move slightly every few seconds (e.g., 10 seconds)
      watermarkIntervalId = setInterval(moveWatermark, 10000);
    }
  }

}); // End DOMContentLoaded
