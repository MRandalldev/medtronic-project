"""
ui.py — shared look-and-feel pieces. (Owner: Jaiden/Jayden, design by Alicia)

Alicia's colors and font go in .streamlit/config.toml. Reusable pieces that
appear on several pages live here, so a design change happens in one place.
"""
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
    st.sidebar.caption("Demo: made-up patient and simulated health data.")

def theme():
    st.html("""<style>
    .stApp {font-family:"Segoe UI",sans-serif}
    .welcome {min-height:340px;display:flex;flex-direction:column;justify-content:flex-end;
      padding:clamp(1.4rem,4vw,4rem);border-radius:1.6rem;color:#fff;
      background:radial-gradient(ellipse at 95% 5%,#72c8b6 0%,transparent 56%),
      linear-gradient(146deg,#25475c,#085c58 65%,#0d333a);}
    .welcome h1 {color:white;line-height:1.06;font-size:clamp(2.6rem,5vw,4.5rem)}
    .welcome small {letter-spacing:.16em;font-weight:650}
    .welcome p {max-width:36ch;color:#e4fbf7}
    section[data-testid="stSidebar"] {border-right:1px solid #cedbd7}
    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stVerticalBlock"][class*="st-key-"] {border-radius:20px}
    [data-testid="stVerticalBlockBorderWrapper"] {background:white}
    div[data-testid="stForm"] {border-radius:18px;background:white}
    .stButton button, .stFormSubmitButton button {border-radius:12px}
    .stTextInput input {font-size:1rem}
    @media(prefers-reduced-motion:no-preference){[data-testid="stMainBlockContainer"]{animation:appear .25s ease-out}}
    @media(prefers-reduced-motion:no-preference){.welcome{animation:appear .32s ease-out}
      @keyframes appear{from{opacity:.4;transform:translateY(5px)}to{opacity:1;transform:none}}}
    </style>""")
