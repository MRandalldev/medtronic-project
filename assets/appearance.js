export default function ({parentElement}) {
  const button = parentElement.querySelector("button");
  const page = document.documentElement;
  let stored;
  try { stored = localStorage.getItem("reco-appearance"); } catch {}
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  function apply(mode) {
    page.dataset.recoTheme = mode;
    button.textContent = mode === "light" ? "☾  Dark mode" : "☀  Light mode";
    button.setAttribute("aria-label", "Switch to " + (mode === "light" ? "dark" : "light") + " mode");
  }
  apply(stored || (media.matches ? "dark" : "light"));
  // reco-close-sidebar: on a phone, choosing a page closes the sidebar so the page is visible.
  if (!window.__recoSidebarCloser) {
    window.__recoSidebarCloser = true;
    document.addEventListener("click", event => {
      if (window.innerWidth > 768) return;
      if (!event.target.closest('section[data-testid=stSidebar] [data-testid=stPageLink-NavLink]')) return;
      setTimeout(() => document.querySelector('section[data-testid=stSidebar] [data-testid=stSidebarCollapseButton] button, section[data-testid=stSidebar] button[kind=headerNoPadding]')?.click(), 150);
    }, true);
  }
  // reco-active-link: mark the sidebar link for the page that is open, so it can be highlighted.
  if (!window.__recoActiveLink) {
    window.__recoActiveLink = true;
    const mark = () => {
      const here = decodeURIComponent(location.pathname.replace(/\/+$/, "").split("/").pop() || "today").toLowerCase();
      document.querySelectorAll('section[data-testid=stSidebar] [data-testid=stPageLink-NavLink]').forEach(link => {
        const target = decodeURIComponent((link.getAttribute("href") || "").split("/").pop()).toLowerCase();
        if (target === here || (here === "" && target === "today")) link.setAttribute("data-active", ""); else link.removeAttribute("data-active");
      });
      // Streamlit gives bordered containers no attribute of their own; tag each one once so the theme can style it as a card.
      document.querySelectorAll('[data-testid=stVerticalBlock]:not([data-reco-seen])').forEach(block => {
        block.setAttribute("data-reco-seen", "");
        if (parseFloat(getComputedStyle(block).borderTopWidth) > 0) block.setAttribute("data-reco-card", "");
      });
    };
    let queued = false;
    new MutationObserver(() => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; mark(); }); } }).observe(document.body, {childList:true, subtree:true});
    mark();
  }
  button.onclick = () => {
    const next = page.dataset.recoTheme === "light" ? "dark" : "light";
    try { localStorage.setItem("reco-appearance",next); } catch {}
    apply(next);
  };
}
