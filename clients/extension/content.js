let ws = null;
let captionBox = null;
let isEnabled = false;
let reconnectTimer = null;

function createCaptionBox(player) {
  if (document.getElementById("ai-cc-box")) return;

  captionBox = document.createElement("div");
  captionBox.id = "ai-cc-box";
  captionBox.style.cssText = `
    position: absolute;
    bottom: 70px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(10, 10, 10, 0.85);
    color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 20px;
    font-weight: 600;
    line-height: 1.4;
    padding: 6px 16px;
    border-radius: 6px;
    z-index: 60;
    pointer-events: none;
    max-width: 82%;
    text-align: center;
    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.6);
    display: none;
    transition: opacity 0.15s ease;
  `;
  player.appendChild(captionBox);
}

function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  ws = new WebSocket("ws://127.0.0.1:8765");

  ws.onopen = () => {
    console.log("[AI CC] Connected to local desktop daemon.");
    if (captionBox && isEnabled) {
      captionBox.style.display = "block";
      captionBox.innerText = "Listening for audio...";
    }
  };

  ws.onmessage = (event) => {
    if (!isEnabled || !captionBox) return;
    try {
      const data = JSON.parse(event.data);
      if (data.type === "transcript" && data.text) {
        captionBox.innerText = data.text;
      }
    } catch {
      captionBox.innerText = event.data;
    }
  };

  ws.onclose = () => {
    if (captionBox && isEnabled) {
      captionBox.innerText = "[Local AI Daemon Offline - Launch server.py]";
    }
    if (isEnabled) {
      clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connectWebSocket, 3000);
    }
  };

  ws.onerror = () => {
    if (ws) ws.close();
  };
}

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
      captionBox.style.display = "block";
      captionBox.innerText = "Connecting to GPU engine...";
      connectWebSocket();
    } else {
      btn.style.color = "#ffffff";
      btn.querySelector("span").style.borderColor = "#bbb";
      captionBox.style.display = "none";
      if (ws) {
        ws.close();
        ws = null;
      }
    }
  };

  // Place immediately before the Settings gear icon
  rightControls.insertBefore(btn, rightControls.firstChild);
}

// Observe YouTube player DOM changes (SPA page swaps)
const observer = new MutationObserver(() => injectToggleButton());
observer.observe(document.body, { childList: true, subtree: true });
injectToggleButton();