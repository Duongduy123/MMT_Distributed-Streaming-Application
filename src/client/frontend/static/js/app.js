// Client UI script — vanilla JavaScript, no framework, no WebSockets.
// Status: SCAFFOLD. The local API (/api/*) does not exist yet, so this script makes NO network
// requests and simulates NO messages, users or transfers. Only local UI behaviour (tab switching)
// is wired.
//
// TODO(Phase 10): call the client process's local API (same origin, 127.0.0.1) for login,
//   sending global/direct chat, file offer/accept and the user list.
// TODO(Phase 10, D2): receive events (presence, messages, delivery receipts, file progress)
//   via polling, long-polling or Server-Sent Events from the same local listener.
"use strict";

(function initTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => {
        const active = t === tab;
        t.classList.toggle("active", active);
        t.setAttribute("aria-selected", String(active));
        document.getElementById("tab-" + t.dataset.tab).hidden = !active;
      });
    });
  });
})();

(function preventPlaceholderSubmits() {
  // Controls are disabled; this guards against accidental submits if one is re-enabled early.
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => event.preventDefault());
  });
})();
