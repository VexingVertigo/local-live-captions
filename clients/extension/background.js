chrome.runtime.onInstalled.addListener(() => {
  console.log("[Local Live Captions] Background worker loaded.");
  // Initialize default options
  chrome.storage.local.get(["captionsEnabled", "captionFontSize"], (res) => {
    if (res.captionsEnabled === undefined) {
      chrome.storage.local.set({ captionsEnabled: true });
    }
    if (res.captionFontSize === undefined) {
      chrome.storage.local.set({ captionFontSize: 20 });
    }
  });
});