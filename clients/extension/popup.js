const defaultSettings = {
  serverHost: "127.0.0.1:8765",
  speakerColors: false,
  textColor: "#ffffff",
  showBackground: true,
  bgOpacity: 85
};

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const serverHostInput = document.getElementById("serverHostInput");
const speakerColorsToggle = document.getElementById("speakerColorsToggle");
const textColorPicker = document.getElementById("textColorPicker");
const showBgToggle = document.getElementById("showBgToggle");
const opacityRange = document.getElementById("opacityRange");
const opacityVal = document.getElementById("opacityVal");

function updateStatusUI(connected, message) {
  if (connected) {
    statusDot.classList.add("connected");
    statusText.textContent = "Connected";
  } else {
    statusDot.classList.remove("connected");
    statusText.textContent = message || "Offline";
  }
}

// Initial status request to background script
chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
  if (res) {
    updateStatusUI(res.connected, res.connected ? "Connected" : "Offline");
  }
});

// Real-time status updates broadcast from background.js
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "status_update") {
    updateStatusUI(message.connected, message.status === "connected" ? "Connected" : "Offline");
  }
});

function loadSettings() {
  chrome.storage.local.get(defaultSettings, (items) => {
    applyToUI(items);
  });
}

function applyToUI(s) {
  serverHostInput.value = s.serverHost || "127.0.0.1:8765";
  speakerColorsToggle.checked = !!s.speakerColors;
  textColorPicker.value = s.textColor || "#ffffff";
  showBgToggle.checked = s.showBackground !== false;
  opacityRange.value = s.bgOpacity !== undefined ? s.bgOpacity : 85;
  opacityVal.textContent = `${opacityRange.value}%`;
}

function saveAndBroadcast() {
  const currentHost = serverHostInput.value.trim() || "127.0.0.1:8765";
  const settings = {
    serverHost: currentHost,
    speakerColors: speakerColorsToggle.checked,
    textColor: textColorPicker.value,
    showBackground: showBgToggle.checked,
    bgOpacity: parseInt(opacityRange.value, 10)
  };

  opacityVal.textContent = `${settings.bgOpacity}%`;

  chrome.storage.local.set(settings, () => {
    chrome.runtime.sendMessage({ action: "reconnect" });
  });

  chrome.tabs.query({}, (tabs) => {
    for (const tab of tabs) {
      if (tab.id) {
        chrome.tabs.sendMessage(tab.id, {
          action: "update_settings",
          settings: settings
        }).catch(() => {});
      }
    }
  });
}

serverHostInput.addEventListener("change", saveAndBroadcast);
speakerColorsToggle.addEventListener("change", saveAndBroadcast);
textColorPicker.addEventListener("input", saveAndBroadcast);
showBgToggle.addEventListener("change", saveAndBroadcast);
opacityRange.addEventListener("input", saveAndBroadcast);

loadSettings();