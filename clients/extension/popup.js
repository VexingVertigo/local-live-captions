const defaultSettings = {
  speakerColors: false,
  textColor: "#ffffff",
  showBackground: true,
  bgOpacity: 85
};

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const speakerColorsToggle = document.getElementById("speakerColorsToggle");
const textColorPicker = document.getElementById("textColorPicker");
const showBgToggle = document.getElementById("showBgToggle");
const opacityRange = document.getElementById("opacityRange");
const opacityVal = document.getElementById("opacityVal");

// Check daemon connection
chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
  if (res && res.connected) {
    statusDot.classList.add("connected");
    statusText.textContent = "Connected";
  } else {
    statusDot.classList.remove("connected");
    statusText.textContent = "Offline";
  }
});

// Load preferences from storage
function loadSettings() {
  if (chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(defaultSettings, (items) => {
      applyToUI(items);
    });
  } else {
    // Fallback if storage API permission is not in manifest
    const saved = localStorage.getItem("ai_caption_settings");
    applyToUI(saved ? JSON.parse(saved) : defaultSettings);
  }
}

function applyToUI(s) {
  speakerColorsToggle.checked = !!s.speakerColors;
  textColorPicker.value = s.textColor || "#ffffff";
  showBgToggle.checked = s.showBackground !== false;
  opacityRange.value = s.bgOpacity !== undefined ? s.bgOpacity : 85;
  opacityVal.textContent = `${opacityRange.value}%`;
}

// Save & broadcast settings to tabs
function saveAndBroadcast() {
  const settings = {
    speakerColors: speakerColorsToggle.checked,
    textColor: textColorPicker.value,
    showBackground: showBgToggle.checked,
    bgOpacity: parseInt(opacityRange.value, 10)
  };

  opacityVal.textContent = `${settings.bgOpacity}%`;

  if (chrome.storage && chrome.storage.local) {
    chrome.storage.local.set(settings);
  }
  localStorage.setItem("ai_caption_settings", JSON.stringify(settings));

  // Send update to all open video tabs
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

// Event Listeners
speakerColorsToggle.addEventListener("change", saveAndBroadcast);
textColorPicker.addEventListener("input", saveAndBroadcast);
showBgToggle.addEventListener("change", saveAndBroadcast);
opacityRange.addEventListener("input", saveAndBroadcast);

loadSettings();