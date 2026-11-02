let socket = null;
let isConnected = false;
let reconnectTimer = null;
let keepAliveTimer = null;

function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  try {
    socket = new WebSocket("ws://127.0.0.1:8765");

    socket.onopen = () => {
      isConnected = true;
      clearTimeout(reconnectTimer);
      startKeepAlive();
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "transcript") {
          // Broadcast transcript and speaker tag to all active browser tabs
          chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs && tabs[0] && tabs[0].id) {
              chrome.tabs.sendMessage(tabs[0].id, data).catch(() => {});
            }
          });
        }
      } catch (err) {}
    };

    socket.onclose = () => {
      isConnected = false;
      stopKeepAlive();
      scheduleReconnect();
    };

    socket.onerror = () => {
      isConnected = false;
      stopKeepAlive();
      try { socket.close(); } catch (e) {}
    };
  } catch (err) {
    isConnected = false;
    stopKeepAlive();
    scheduleReconnect();
  }
}

// Resets Chromium service worker's 30s idle timer
function startKeepAlive() {
  stopKeepAlive();
  keepAliveTimer = setInterval(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "ping" }));
    } else {
      stopKeepAlive();
    }
  }, 20000);
}

function stopKeepAlive() {
  if (keepAliveTimer) {
    clearInterval(keepAliveTimer);
    keepAliveTimer = null;
  }
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connectWebSocket, 3000);
}

// Top-level message listener (wakes service worker on Chrome when triggered)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "get_status") {
    if (!isConnected) connectWebSocket();
    sendResponse({
      connected: isConnected,
      message: isConnected ? "AI Engine ready." : "Daemon offline. Run daemon."
    });
    return true;
  }

  if (request.action === "reconnect" || request.action === "ensure_connected") {
    connectWebSocket();
    sendResponse({ status: "connecting" });
    return true;
  }
});

// Initial startup
connectWebSocket();