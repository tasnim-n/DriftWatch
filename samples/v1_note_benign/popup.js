// V1.0.0 safe note saving script
document.getElementById("saveBtn").addEventListener("click", () => {
  const text = document.getElementById("noteInput").value;
  chrome.storage.local.set({ myNote: text });
});
