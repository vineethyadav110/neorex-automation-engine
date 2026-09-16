document.addEventListener("DOMContentLoaded", async () => {
  const statusEl = document.getElementById("backend-status");
  try {
    const res = await fetch("http://127.0.0.1:8000/api/health");
    if (res.ok) {
      statusEl.textContent = "Backend: Connected (Port 8000)";
      statusEl.style.background = "#dcfce7";
      statusEl.style.color = "#166534";
    } else {
      throw new Error();
    }
  } catch (e) {
    statusEl.textContent = "Backend: Disconnected";
    statusEl.style.background = "#fee2e2";
    statusEl.style.color = "#991b1b";
  }

  document.getElementById("open-drawer-btn").addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.scripting.executeScript({
          target: { tabId: tabs[0].id },
          func: () => {
            const btn = document.getElementById("neorex-floating-btn");
            if (btn) btn.click();
          }
        });
      }
    });
  });
});
