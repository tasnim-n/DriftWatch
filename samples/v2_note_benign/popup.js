// V1.0.1 benign refactored note saving script
document.getElementById("saveBtn").addEventListener("click", () => {
  // Read textarea value
  const text = document.getElementById("noteInput").value;
  // Save locally in chrome storage
  chrome.storage.local.set({ myNote: text }, () => {
    console.log("Note saved successfully.");
  });
});
