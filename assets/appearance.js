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
  button.onclick = () => {
    const next = page.dataset.recoTheme === "light" ? "dark" : "light";
    try { localStorage.setItem("reco-appearance",next); } catch {}
    apply(next);
  };
}
