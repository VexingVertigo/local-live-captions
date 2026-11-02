const dot = document.getElementById("status-dot");
const text = document.getElementById("status-text");
const detail = document.getElementById("status-detail");

function renderState(isOnline, message) {
  if (isOnline) {
    dot.className = "dot online";
    text.innerText = "Connected";
    text.style.color = "#22c55e";
    detail.innerText = message || "Ready. Press Alt + C on any video to stream captions.";
  } else {
    dot.className = "dot offline";
    text.innerText = "Offline";
    text.style.color = "#ef4444";
    detail.innerText = message || "Daemon not detected. Double-click run_daemon.vbs to launch.";
  }
}

function checkStatus() {
  chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
    if (chrome.runtime.lastError || !res) {
      renderState(false);
      return;
    }
    renderState(res.connected, res.message);
  });
}

checkStatus();
setInterval(checkStatus, 1500);