let socket = null;
let isConnected = false;
let reconnectTimer = null;

function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  try {
    socket = new WebSocket("ws://127.0.0.1:8765");

    socket.onopen = () => {
      isConnected = true;
      clearTimeout(reconnectTimer);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Relay transcripts to content script in the active tab
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs && tabs[0] && tabs[0].id) {
            chrome.tabs.sendMessage(tabs[0].id, data).catch(() => {});
          }
        });
      } catch (err) {}
    };

    socket.onclose = () => {
      isConnected = false;
      scheduleReconnect();
    };

    socket.onerror = () => {
      isConnected = false;
      try { socket.close(); } catch (e) {}
    };
  } catch (err) {
    isConnected = false;
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connectWebSocket, 3000);
}

// Listen for popup status checks and content script triggers
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "get_status") {
    sendResponse({
      connected: isConnected,
      message: isConnected ? "AI Engine ready on RTX 5080." : "Daemon offline. Double-click run_daemon.vbs."
    });
    return true;
  }

  if (request.action === "reconnect") {
    connectWebSocket();
    sendResponse({ status: "attempting_reconnect" });
    return true;
  }
});

// Start connection loop
connectWebSocket();