"""A single background browser model shared by this tab's Reco surfaces."""
from pathlib import Path
import os

import streamlit as st
from streamlit.components.v1 import declare_component

ROOT = Path(__file__).parent
# Registration exposes the bundled module under the local Streamlit CLI too.
_local = declare_component("recovery_browser", path=str(ROOT / "browser/component"))
URL = "/reco-engine/app.js" if os.getenv("VERCEL") else "/component/browser_engine.recovery_browser/app.js"
_engine = st.components.v2.component("reco_runtime", html="<span hidden></span>",
                                    js=(ROOT / "assets/reco-runtime.js").read_text(encoding="utf8"))


def warm():
    if os.getenv("VERCEL"):
        _engine(data={"url": URL}, key="warm_reco", height=0)


def generate(request, key):
    result = _engine(data={"url": URL, "request": request}, key=key, height=0,
                     on_answer_change=lambda: None)
    return result.answer
