"""ASGI entry point for the workspace and the Apple Health shortcut."""
from pathlib import Path

from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import streamlit as st

from health_connection import receive

ROOT = Path(__file__).resolve().parents[1]
app = st.App(ROOT / "app.py", routes=[
    Route("/health/readings", receive, methods=["POST"]),
    Mount("/reco-engine", app=StaticFiles(directory=ROOT / "browser/component", html=True)),
])
