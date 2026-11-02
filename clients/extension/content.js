let captionWrapper = null;
let textSpan = null;
let isEnabled = false;
let clearTimer = null;
let pauseTimer = null;

let line1Text = "";
let line2Text = "";
let isNewSentence = true;

const MAX_LINE_CHARS = 42;

function getActiveVideo() {
  const videos = Array.from(document.querySelectorAll("video"));
  return videos.find(v => !v.paused && v.currentTime > 0) || videos[0] || null;
}

function ensureCaptionElements() {
  if (captionWrapper && document.body.contains(captionWrapper)) return;

  captionWrapper = document.createElement("div");
  captionWrapper.id = "universal-ai-cc-root";
  captionWrapper.style.cssText = `
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    width: fit-content;
    max-width: 85vw;
    text-align: center;
    z-index: 2147483647;
    pointer-events: none;
    display: none;
    transition: opacity 0.15s ease;
  `;

  textSpan = document.createElement("span");
  textSpan.style.cssText = `
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 20px;
    font-weight: 600;
    line-height: 1.5;
    color: #ffffff;
    background: rgba(10, 10, 14, 0.88);
    padding: 6px 14px;
    border-radius: 4px;
    box-decoration-break: clone;
    -webkit-box-decoration-break: clone;
    box-shadow: 0 4px 14px rgba(0,0,0,0.6);
    text-shadow: 0 1px 2px rgba(0,0,0,0.9);
    white-space: pre-wrap;
    display: inline-block;
  `;

  captionWrapper.appendChild(textSpan);
  document.body.appendChild(captionWrapper);
}

function appendSpeech(text) {
  ensureCaptionElements();
  if (!captionWrapper || !isEnabled) return;

  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return;

  captionWrapper.style.display = "block";
  textSpan.style.color = "#ffffff";

  for (let rawWord of words) {
    let word = rawWord;
    if (isNewSentence) {
      isNewSentence = false;
      word = word.charAt(0).toUpperCase() + word.slice(1);
    }

    if ((line2Text + " " + word).trim().length > MAX_LINE_CHARS) {
      line1Text = line2Text;
      line2Text = word;
    } else {
      line2Text = line2Text ? `${line2Text} ${word}` : word;
    }
  }

  textSpan.innerText = line1Text ? `${line1Text}\n${line2Text}` : line2Text;

  clearTimeout(pauseTimer);
  pauseTimer = setTimeout(() => {
    isNewSentence = true;
    if (line2Text) {
      line1Text = line2Text;
      line2Text = "";
    }
  }, 1800);

  clearTimeout(clearTimer);
  clearTimer = setTimeout(() => {
    line1Text = "";
    line2Text = "";
    isNewSentence = true;
    if (captionWrapper) captionWrapper.style.display = "none";
  }, 5000);
}

function toggleCaptions() {
  isEnabled = !isEnabled;
  ensureCaptionElements();

  if (isEnabled) {
    captionWrapper.style.display = "block";
    textSpan.style.color = "#ffca28";
    textSpan.innerText = "Local AI Captions: Listening...";
    chrome.runtime.sendMessage({ action: "get_status" });
  } else {
    clearTimeout(clearTimer);
    clearTimeout(pauseTimer);
    line1Text = "";
    line2Text = "";
    isNewSentence = true;
    captionWrapper.style.display = "none";
  }
}

// Global Hotkey: Alt + C toggles live captions on any website
window.addEventListener("keydown", (e) => {
  if (e.altKey && (e.key === "c" || e.key === "C")) {
    toggleCaptions();
  }
});

// Click extension icon from browser toolbar to toggle
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.action === "toggle_from_icon") {
    toggleCaptions();
  } else if (isEnabled && msg.type === "transcript" && msg.text) {
    appendSpeech(msg.text);
  }
});