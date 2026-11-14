"""
ui.py — shared look-and-feel pieces. (Owner: Jaiden/Jayden, design by Alicia)

Alicia's colors and font go in .streamlit/config.toml. Reusable pieces that
appear on several pages live here, so a design change happens in one place.
"""
from base64 import b64encode
from pathlib import Path

import streamlit as st

import backend

LEVEL_STYLE = {
    "green": ("No demo rule matched", st.success),
    "yellow": ("Keep an eye on this", st.warning),
    "red": ("Act now", st.error),
}


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def alert_banner(level: str, reasons: list) -> None:
    label, box = LEVEL_STYLE.get(level, LEVEL_STYLE["green"])
    lines = [f"**{label}**"] + [f"- {r['message']}  \n  _Source: {r['source']}_" for r in reasons]
    box("\n".join(lines))
    if level == "red":
        st.error("\n".join(f"{i}. {s}" for i, s in enumerate(backend.EMERGENCY_STEPS, 1)))
        st.info("Demo alert recorded in this session. No message was sent.")


def demo_badge() -> None:
    st.caption("Fictional recovery workspace")

ASSETS = Path(__file__).parent / "assets"


@st.cache_data
def artwork(filename):
    mime = "png" if filename.endswith(".png") else "jpeg"
    return f"data:image/{mime};base64," + b64encode((ASSETS / filename).read_bytes()).decode("ascii")


appearance = st.components.v2.component("appearance_switch", html='<button type="button"></button>',
    css="button{float:right;background:var(--reco-card,transparent);color:var(--reco-ink,inherit);border:1px solid var(--reco-border,#79918b);border-radius:2rem;padding:.4rem .8rem;cursor:pointer;font:600 .85rem system-ui}",
    js=(ASSETS / "appearance.js").read_text(encoding="utf8"))


def theme():
    css = (ASSETS / "recovery.css").read_text(encoding="utf8")
    styles = (ASSETS / "appearance.css").read_text(encoding="utf8")
    st.html("<style>" + css.replace("RECO_ART", artwork("reco-face.png")) +
            styles.replace("EARTH_ART", artwork("earthrise.jpg")) + "</style>")
    appearance(key="appearance", height=38)
