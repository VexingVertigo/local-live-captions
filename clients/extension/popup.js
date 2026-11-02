const dot = document.getElementById("status-dot");
const text = document.getElementById("status-text");
const detail = document.getElementById("status-detail");

function updateStatus() {
  chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
    if (chrome.runtime.lastError || !res || res.status === "offline") {
      dot.className = "dot offline";
      text.innerText = "Offline";
      detail.innerText = "Daemon not detected. Double-click run_daemon.vbs to launch.";
    } else {
      dot.className = "dot online";
      text.innerText = "Connected";
      detail.innerText = "Ready. Press Alt + C on any video to stream subtitles.";
    }
  });
}

updateStatus();
setInterval(updateStatus, 1500);