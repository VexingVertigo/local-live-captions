let socket = null;
let isConnected = false;
let reconnectTimer = null;
let keepAliveTimer = null;

function broadcastStatus(status, message) {
  chrome.runtime.sendMessage({
    type: "status_update",
    connected: isConnected,
    status: status,
    message: message
  }).catch(() => {
    // Popup is closed, ignore error
  });
}

function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  chrome.storage.local.get({ serverHost: "127.0.0.1:8765" }, (items) => {
    const host = items.serverHost || "127.0.0.1:8765";
    const wsUrl = `ws://${host}`;

    console.log(`[LiveCaptions] Connecting to: ${wsUrl}`);

    if (socket) {
      try { socket.close(); } catch (e) {}
    }

    try {
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        console.log(`[LiveCaptions] Connected to ${wsUrl}`);
        isConnected = true;
        clearTimeout(reconnectTimer);
        startKeepAlive();
        broadcastStatus("connected", "AI Engine ready.");
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "transcript") {
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
              if (tabs && tabs[0]?.id) {
                chrome.tabs.sendMessage(tabs[0].id, data).catch(() => {});
              }
            });
          }
        } catch (err) {
          console.error("[LiveCaptions] Message parsing error:", err);
        }
      };

      socket.onclose = (e) => {
        console.warn(`[LiveCaptions] Socket closed (code ${e.code}). Reconnecting in 3s...`);
        isConnected = false;
        stopKeepAlive();
        broadcastStatus("disconnected", "Daemon offline.");
        scheduleReconnect();
      };

      socket.onerror = (err) => {
        console.error("[LiveCaptions] Socket error:", err);
        isConnected = false;
        stopKeepAlive();
        try { socket.close(); } catch (e) {}
      };
    } catch (err) {
      console.error("[LiveCaptions] Initialization error:", err);
      isConnected = false;
      stopKeepAlive();
      scheduleReconnect();
    }
  });
}

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

// Runtime messaging
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "get_status") {
    if (!isConnected) {
      connectWebSocket();
    }
    sendResponse({
      connected: isConnected,
      message: isConnected ? "AI Engine ready." : "Connecting to daemon..."
    });
    return true;
  }

  if (request.action === "reconnect" || request.action === "ensure_connected") {
    if (socket) {
      try { socket.close(); } catch (e) {}
      socket = null;
    }
    connectWebSocket();
    sendResponse({ status: "connecting" });
    return true;
  }
});

// Start immediately on load
connectWebSocket();