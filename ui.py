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

def theme():
    assets = Path(__file__).parent / "assets"
    css = (assets / "recovery.css").read_text(encoding="utf-8")
    artwork = b64encode((assets / "reco-reference.jpg").read_bytes()).decode("ascii")
    st.html("<style>" + css.replace("RECO_ART", "data:image/jpeg;base64," + artwork) + "</style>")
