let targetVideo = null;
let captionBox = null;
let line1El = null;
let line2El = null;
let span1El = null;
let span2El = null;
let resizeObserver = null;
let clearTimer = null;
let overlayEnabled = true;

// User configurable settings
let settings = {
  speakerColors: false,
  textColor: "#ffffff",
  showBackground: true,
  bgOpacity: 85
};

// Standard multi-speaker color scheme (Yellow, Cyan, Green, Pink)
const SPEAKER_COLORS = ["#facc15", "#38bdf8", "#4ade80", "#f472b6"];

let line1Words = [];
let line2Words = [];
let line1Speaker = 0;
let line2Speaker = 0;
const MAX_LINE_CHARS = 52;

function loadSavedSettings() {
  if (chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(settings, (items) => {
      if (items) {
        settings = Object.assign(settings, items);
        renderLines();
      }
    });
  } else {
    try {
      const saved = localStorage.getItem("ai_caption_settings");
      if (saved) {
        settings = Object.assign(settings, JSON.parse(saved));
        renderLines();
      }
    } catch (e) {}
  }
}

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

  line1El = document.createElement("div");
  line1El.style.cssText = "margin-bottom: 5px; display: none; text-align: center; max-width: 100%;";
  span1El = document.createElement("span");
  span1El.style.cssText = `
    padding: 5px 12px !important;
    border-radius: 4px !important;
    display: inline-block !important;
    box-decoration-break: clone !important;
    -webkit-box-decoration-break: clone !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.95), 0 0 3px rgba(0,0,0,0.9) !important;
  `;
  line1El.appendChild(span1El);

  line2El = document.createElement("div");
  line2El.style.cssText = "display: none; text-align: center; max-width: 100%;";
  span2El = document.createElement("span");
  span2El.style.cssText = `
    padding: 5px 12px !important;
    border-radius: 4px !important;
    display: inline-block !important;
    box-decoration-break: clone !important;
    -webkit-box-decoration-break: clone !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.95), 0 0 3px rgba(0,0,0,0.9) !important;
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
  if (!captionBox || !overlayEnabled) return;

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

  // Refresh targetVideo if detached from DOM during YouTube client-side routing
  if (!targetVideo || !document.contains(targetVideo)) {
    targetVideo = findActiveVideo();
  }

  if (!targetVideo) {
    captionBox.style.display = "none";
    return;
  }

  const rect = targetVideo.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0 || rect.bottom < 0 || rect.top > window.innerHeight) {
    captionBox.style.display = "none";
    return;
  }

  captionBox.style.width = `${Math.min(rect.width * 0.92, 850)}px`;

  const bottomOffset = Math.max(34, rect.height * 0.12);
  captionBox.style.left = `${rect.left + rect.width / 2}px`;
  captionBox.style.top = `${rect.bottom - bottomOffset}px`;
  captionBox.style.transform = "translate(-50%, -100%)";
}

function renderLines() {
  if (!span1El || !span2El || !overlayEnabled) return;

  const alpha = (settings.bgOpacity / 100).toFixed(2);
  const bgStyle = settings.showBackground
    ? `rgba(8, 8, 8, ${alpha})`
    : "transparent";

  span1El.style.setProperty("background", bgStyle, "important");
  span2El.style.setProperty("background", bgStyle, "important");

  let color1 = settings.textColor;
  let color2 = settings.textColor;

  if (settings.speakerColors) {
    color1 = SPEAKER_COLORS[line1Speaker % SPEAKER_COLORS.length];
    color2 = SPEAKER_COLORS[line2Speaker % SPEAKER_COLORS.length];
  }

  span1El.style.color = color1;
  span2El.style.color = color2;

  if (line1Words.length > 0) {
    const isMulti = settings.speakerColors && (line1Words.length > 0 && line2Words.length > 0 && line1Speaker !== line2Speaker);
    span1El.textContent = (isMulti ? "- " : "") + line1Words.join(" ");
    line1El.style.display = "block";
  } else {
    line1El.style.display = "none";
  }

  if (line2Words.length > 0) {
    const isMulti = settings.speakerColors && (line1Words.length > 0 && line2Words.length > 0 && line1Speaker !== line2Speaker);
    span2El.textContent = (isMulti ? "- " : "") + line2Words.join(" ");
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

function appendTranscription(newText, incomingSpeaker = 0) {
  if (!overlayEnabled) return;

  const incoming = newText.trim().split(/\s+/).filter(Boolean);
  if (!incoming.length) return;

  clearTimeout(clearTimer);

  for (const word of incoming) {
    if (settings.speakerColors && line2Words.length > 0 && incomingSpeaker !== line2Speaker) {
      line1Words = [...line2Words];
      line1Speaker = line2Speaker;
      line2Words = [word];
      line2Speaker = incomingSpeaker;
      continue;
    }

    if (line2Words.length === 0) {
      if (line1Words.length === 0) line1Speaker = incomingSpeaker;

      const candidate = line1Words.concat([word]).join(" ");
      const isEnd = /[.!?]$/.test(line1Words[line1Words.length - 1] || "");

      if (candidate.length <= MAX_LINE_CHARS && !isEnd && (!settings.speakerColors || incomingSpeaker === line1Speaker)) {
        line1Words.push(word);
      } else {
        line2Words.push(word);
        line2Speaker = incomingSpeaker;
      }
    } else {
      const candidate = line2Words.concat([word]).join(" ");
      const isEnd = /[.!?]$/.test(line2Words[line2Words.length - 1] || "");

      if (candidate.length <= MAX_LINE_CHARS && !isEnd) {
        line2Words.push(word);
      } else {
        line1Words = [...line2Words];
        line1Speaker = line2Speaker;
        line2Words = [word];
        line2Speaker = incomingSpeaker;
      }
    }
  }

  renderLines();

  clearTimer = setTimeout(() => {
    if (!captionBox) return;
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

  if (data.action === "update_settings" && data.settings) {
    settings = Object.assign(settings, data.settings);
    renderLines();
    return;
  }

  if (data.text !== undefined) {
    if (!targetVideo || !document.contains(targetVideo)) {
      attachVideoTracker(findActiveVideo());
    }
    appendTranscription(data.text, data.speaker !== undefined ? data.speaker : 0);
  }
});

// Alt + C toggles overlay on and off
window.addEventListener("keydown", (e) => {
  if (e.altKey && (e.key === "c" || e.key === "C")) {
    overlayEnabled = !overlayEnabled;
    if (!overlayEnabled) {
      if (captionBox) captionBox.style.display = "none";
    } else {
      initCaptionOverlay();
      const active = findActiveVideo();
      if (active) attachVideoTracker(active);
      renderLines();
    }
  }
});

try {
  chrome.runtime.sendMessage({ action: "ensure_connected" }).catch(() => {});
} catch (e) {}

loadSavedSettings();