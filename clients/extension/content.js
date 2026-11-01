let captionWrapper = null;
let textSpan = null;
let isEnabled = false;
let clearTimer = null;
let pauseTimer = null;

let line1Text = "";
let line2Text = "";
let isNewSentence = true;

const MAX_LINE_CHARS = 40;

function createCaptionBox(player) {
  if (document.getElementById("ai-cc-wrapper")) return;

  captionWrapper = document.createElement("div");
  captionWrapper.id = "ai-cc-wrapper";
  captionWrapper.style.cssText = `
    position: absolute;
    bottom: 75px;
    left: 50%;
    transform: translateX(-50%);
    width: fit-content;
    max-width: 82%;
    text-align: center;
    z-index: 60;
    pointer-events: none;
    display: none;
    transition: opacity 0.2s ease;
  `;

  textSpan = document.createElement("span");
  textSpan.id = "ai-cc-text";
  textSpan.style.cssText = `
    font-family: "YouTube Noto", Roboto, "Segoe UI", Arial, sans-serif;
    font-size: 21px;
    font-weight: 600;
    line-height: 1.5;
    color: #ffffff;
    background: rgba(8, 8, 10, 0.85);
    padding: 6px 14px;
    border-radius: 4px;
    box-decoration-break: clone;
    -webkit-box-decoration-break: clone;
    box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.6);
    text-shadow: 0 1px 3px rgba(0,0,0,0.9);
    white-space: pre-wrap;
    display: inline-block;
  `;

  captionWrapper.appendChild(textSpan);
  player.appendChild(captionWrapper);
}

function formatWord(word) {
  if (isNewSentence) {
    isNewSentence = false;
    return word.charAt(0).toUpperCase() + word.slice(1);
  }
  return word;
}

function appendSpeech(incomingString) {
  if (!captionWrapper || !isEnabled) return;

  const words = incomingString.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return;

  captionWrapper.style.display = "block";
  textSpan.style.color = "#ffffff";

  for (let rawWord of words) {
    const word = formatWord(rawWord);

    if ((line2Text + " " + word).trim().length > MAX_LINE_CHARS) {
      line1Text = line2Text;
      line2Text = word;
    } else {
      line2Text = line2Text ? `${line2Text} ${word}` : word;
    }
  }

  // Display 2 lines if Line 1 has text, otherwise a single compact line
  if (line1Text) {
    textSpan.innerText = `${line1Text}\n${line2Text}`;
  } else {
    textSpan.innerText = line2Text;
  }

  // Commit sentence break after a natural pause
  clearTimeout(pauseTimer);
  pauseTimer = setTimeout(() => {
    isNewSentence = true;
    if (line2Text) {
      line1Text = line2Text;
      line2Text = "";
    }
  }, 1800);

  // Clear captions after 5 seconds of silence
  clearTimeout(clearTimer);
  clearTimer = setTimeout(() => {
    line1Text = "";
    line2Text = "";
    isNewSentence = true;
    if (captionWrapper) captionWrapper.style.display = "none";
  }, 5000);
}

function showSystemStatus(message, isError = false) {
  if (!captionWrapper || !isEnabled) return;
  clearTimeout(clearTimer);
  clearTimeout(pauseTimer);
  line1Text = "";
  line2Text = "";
  isNewSentence = true;

  captionWrapper.style.display = "block";
  textSpan.style.color = isError ? "#ff6b6b" : "#ffca28";
  textSpan.innerText = message;
}

chrome.runtime.onMessage.addListener((msg) => {
  if (!isEnabled) return;

  if (msg.type === "transcript" && msg.text) {
    appendSpeech(msg.text);
  } else if (msg.type === "status") {
    if (msg.status === "offline") {
      showSystemStatus(`[Error] ${msg.message}`, true);
    } else if (msg.status === "connecting" || msg.status === "connected") {
      showSystemStatus(msg.message, false);
    }
  }
});

function injectToggleButton() {
  const rightControls = document.querySelector(".ytp-right-controls");
  const player = document.querySelector("#movie_player");

  if (!rightControls || !player || document.getElementById("ai-cc-toggle-btn")) {
    return;
  }

  createCaptionBox(player);

  const btn = document.createElement("button");
  btn.id = "ai-cc-toggle-btn";
  btn.className = "ytp-button";
  btn.title = "Toggle Local AI Captions";
  btn.innerHTML = `<span style="font-weight:700; font-size:12px; border:1.5px solid #bbb; border-radius:3px; padding:2px 5px;">AI CC</span>`;

  btn.onclick = () => {
    isEnabled = !isEnabled;
    if (isEnabled) {
      btn.style.color = "#3ea6ff";
      btn.querySelector("span").style.borderColor = "#3ea6ff";
      showSystemStatus("Connecting to AI engine...", false);
      chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
        if (res && res.status === "connected") {
          showSystemStatus(res.message, false);
        }
      });
    } else {
      btn.style.color = "#ffffff";
      btn.querySelector("span").style.borderColor = "#bbb";
      clearTimeout(clearTimer);
      clearTimeout(pauseTimer);
      line1Text = "";
      line2Text = "";
      isNewSentence = true;
      captionWrapper.style.display = "none";
    }
  };

  rightControls.insertBefore(btn, rightControls.firstChild);
}

const observer = new MutationObserver(() => injectToggleButton());
observer.observe(document.body, { childList: true, subtree: true });
injectToggleButton();