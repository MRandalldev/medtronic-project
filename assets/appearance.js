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
  button.onclick = () => {
    const next = page.dataset.recoTheme === "light" ? "dark" : "light";
    try { localStorage.setItem("reco-appearance",next); } catch {}
    apply(next);
  };
}
