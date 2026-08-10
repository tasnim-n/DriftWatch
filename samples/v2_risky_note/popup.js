document.getElementById("saveBtn").addEventListener("click", () => {
  const note = document.getElementById("noteInput").value;
  chrome.storage.local.set({ userNote: note }, () => {
    console.log("Note saved locally.");
  });
});
