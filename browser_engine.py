from pathlib import Path

from streamlit.components.v1 import declare_component

select_passage = declare_component(
    "recovery_browser",
    path=str(Path(__file__).parent / "browser" / "component"),
)
