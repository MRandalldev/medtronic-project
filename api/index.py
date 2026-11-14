"""ASGI entry point for the workspace and the Apple Health shortcut."""
from pathlib import Path

from starlette.routing import Route
import streamlit as st

from health_connection import receive

app = st.App(Path(__file__).resolve().parents[1] / "app.py",
             routes=[Route("/health/readings", receive, methods=["POST"])])
