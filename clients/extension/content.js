let targetVideo = null;
let captionBox = null;
let line1El = null;
let line2El = null;
let span1El = null;
let span2El = null;
let resizeObserver = null;
let clearTimer = null;

// Symmetrical two-line roll-up state
let line1Words = [];
let line2Words = [];
const MAX_LINE_CHARS = 58; // Allows lines to extend across to the right side

function initCaptionOverlay() {
  if (captionBox) return;

  captionBox = document.createElement("div");
  captionBox.id = "ai-live-caption-box";
  captionBox.setAttribute("style", `
    position: fixed !important;
    z-index: 2147483647 !important;
    pointer-events: none !important;
    background: transparent !important;
    display: none;
    flex-direction: column !important;
    align-items: center !important;
    box-sizing: border-box !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    line-height: 1.4 !important;
    transition: opacity 0.2s ease;
  `);

  // Line 1 Container & Span
  line1El = document.createElement("div");
  line1El.style.cssText = "margin-bottom: 5px; display: none; text-align: center; max-width: 100%;";
  span1El = document.createElement("span");
  span1El.style.cssText = `
    background: rgba(8, 8, 8, 0.86) !important;
    color: #ffffff !important;
    padding: 5px 12px !important;
    border-radius: 4px !important;
    display: inline-block !important;
    box-decoration-break: clone !important;
    -webkit-box-decoration-break: clone !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.95) !important;
  `;
  line1El.appendChild(span1El);

  // Line 2 Container & Span
  line2El = document.createElement("div");
  line2El.style.cssText = "display: none; text-align: center; max-width: 100%;";
  span2El = document.createElement("span");
  span2El.style.cssText = `
    background: rgba(8, 8, 8, 0.86) !important;
    color: #ffffff !important;
    padding: 5px 12px !important;
    border-radius: 4px !important;
    display: inline-block !important;
    box-decoration-break: clone !important;
    -webkit-box-decoration-break: clone !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.95) !important;
  `;
  line2El.appendChild(span2El);

  captionBox.appendChild(line1El);
  captionBox.appendChild(line2El);
  document.body.appendChild(captionBox);

  window.addEventListener("scroll", updateOverlayPosition, { passive: true, capture: true });
  window.addEventListener("resize", updateOverlayPosition, { passive: true });
}

function findActiveVideo() {
  const videos = Array.from(document.querySelectorAll("video"));
  if (!videos.length) return null;
  const playing = videos.find((v) => !v.paused && !v.ended && v.readyState > 2);
  if (playing) return playing;

  return videos.sort((a, b) => {
    const ra = a.getBoundingClientRect();
    const rb = b.getBoundingClientRect();
    return (rb.width * rb.height) - (ra.width * ra.height);
  })[0];
}

function updateOverlayPosition() {
  if (!captionBox) return;

  const fsElement = document.fullscreenElement || document.webkitFullscreenElement;
  if (fsElement) {
    if (captionBox.parentElement !== fsElement && fsElement.appendChild) {
      fsElement.appendChild(captionBox);
    }
    captionBox.style.position = "absolute";
    captionBox.style.left = "50%";
    captionBox.style.top = "auto";
    captionBox.style.bottom = "8%";
    captionBox.style.transform = "translateX(-50%)";
    captionBox.style.width = "85%";
    captionBox.style.fontSize = "22px";
    return;
  }

  if (captionBox.parentElement !== document.body) {
    document.body.appendChild(captionBox);
    captionBox.style.position = "fixed";
    captionBox.style.bottom = "auto";
    captionBox.style.fontSize = "18px";
  }

  if (!targetVideo) targetVideo = findActiveVideo();
  if (!targetVideo) {
    captionBox.style.display = "none";
    return;
  }

  const rect = targetVideo.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0 || rect.bottom < 0 || rect.top > window.innerHeight) {
    captionBox.style.display = "none";
    return;
  }

  // Extend evenly across the player
  captionBox.style.width = `${Math.min(rect.width * 0.92, 850)}px`;

  const bottomOffset = Math.max(34, rect.height * 0.12);
  captionBox.style.left = `${rect.left + rect.width / 2}px`;
  captionBox.style.top = `${rect.bottom - bottomOffset}px`;
  captionBox.style.transform = "translate(-50%, -100%)";
}

function renderLines() {
  if (line1Words.length > 0) {
    span1El.textContent = line1Words.join(" ");
    line1El.style.display = "block";
  } else {
    line1El.style.display = "none";
  }

  if (line2Words.length > 0) {
    span2El.textContent = line2Words.join(" ");
    line2El.style.display = "block";
  } else {
    line2El.style.display = "none";
  }

  if (line1Words.length > 0 || line2Words.length > 0) {
    captionBox.style.display = "flex";
    captionBox.style.opacity = "1";
    updateOverlayPosition();
  }
}

function appendTranscription(newText) {
  const incoming = newText.trim().split(/\s+/).filter(Boolean);
  if (!incoming.length) return;

  clearTimeout(clearTimer);

  for (const word of incoming) {
    const lastActive = line2Words.length ? line2Words[line2Words.length - 1] : line1Words[line1Words.length - 1];
    if (lastActive && lastActive.toLowerCase() === word.toLowerCase()) {
      continue;
    }

    if (line2Words.length === 0) {
      const candidate = line1Words.concat([word]).join(" ");
      const isEnd = /[.!?]$/.test(line1Words[line1Words.length - 1] || "");

      if (candidate.length <= MAX_LINE_CHARS && !isEnd) {
        line1Words.push(word);
      } else {
        line2Words.push(word);
      }
    } else {
      const candidate = line2Words.concat([word]).join(" ");
      const isEnd = /[.!?]$/.test(line2Words[line2Words.length - 1] || "");

      if (candidate.length <= MAX_LINE_CHARS && !isEnd) {
        line2Words.push(word);
      } else {
        line1Words = [...line2Words];
        line2Words = [word];
      }
    }
  }

  renderLines();

  clearTimer = setTimeout(() => {
    captionBox.style.opacity = "0";
    setTimeout(() => {
      captionBox.style.display = "none";
      line1Words = [];
      line2Words = [];
      line1El.style.display = "none";
      line2El.style.display = "none";
    }, 200);
  }, 3200);
}

function attachVideoTracker(video) {
  if (!video) return;
  targetVideo = video;
  if (resizeObserver) resizeObserver.disconnect();
  resizeObserver = new ResizeObserver(updateOverlayPosition);
  resizeObserver.observe(video);
  updateOverlayPosition();
}

chrome.runtime.onMessage.addListener((data) => {
  initCaptionOverlay();
  if (data.text !== undefined) {
    if (!targetVideo) attachVideoTracker(findActiveVideo());
    appendTranscription(data.text);
  }
});

window.addEventListener("keydown", (e) => {
  if (e.altKey && (e.key === "c" || e.key === "C")) {
    initCaptionOverlay();
    const active = findActiveVideo();
    if (active) attachVideoTracker(active);
  }
});