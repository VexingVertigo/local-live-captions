let ws = null;
let reconnectTimer = null;
let retryCount = 0;

function sendToAllYouTubeTabs(payload) {
  chrome.tabs.query({ url: "*://*.youtube.com/*" }, (tabs) => {
    if (!tabs) return;
    for (const tab of tabs) {
      chrome.tabs.sendMessage(tab.id, payload).catch(() => {});
    }
  });
}

function connectWS() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  sendToAllYouTubeTabs({
    type: "status",
    status: "connecting",
    message: "Connecting to daemon at ws://127.0.0.1:8765..."
  });

  try {
    ws = new WebSocket("ws://127.0.0.1:8765");
  } catch (err) {
    sendToAllYouTubeTabs({
      type: "status",
      status: "error",
      message: `WebSocket init error: ${err.message}`
    });
    return;
  }

  ws.onopen = () => {
    retryCount = 0;
    sendToAllYouTubeTabs({
      type: "status",
      status: "connected",
      message: "Connected to AI engine. Waiting for desktop audio..."
    });
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      sendToAllYouTubeTabs(data);
    } catch {
      sendToAllYouTubeTabs({ type: "transcript", text: event.data });
    }
  };

  ws.onerror = () => {
    sendToAllYouTubeTabs({
      type: "status",
      status: "error",
      message: "Cannot reach ws://127.0.0.1:8765 (Port unreachable or blocked)"
    });
  };

  ws.onclose = () => {
    retryCount++;
    sendToAllYouTubeTabs({
      type: "status",
      status: "offline",
      message: `Daemon offline. Retrying in 3s (Attempt ${retryCount})...`
    });
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connectWS, 3000);
  };
}

connectWS();

chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
  if (req.action === "get_status") {
    if (ws && ws.readyState === WebSocket.OPEN) {
      sendResponse({ status: "connected", message: "Connected to AI engine." });
    } else {
      connectWS();
      sendResponse({ status: "connecting", message: "Connecting to daemon..." });
    }
  }
  return true;
});