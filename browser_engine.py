import os
from pathlib import Path


from streamlit.components.v1 import declare_component

# The browser may fetch assets from a different function instance than its session.
# This URL always resolves, even before that instance has executed the page script.
if os.getenv("VERCEL"):
    select_passage = declare_component("recovery_browser", url="/reco-engine/index.html")
else:
    select_passage = declare_component(
        "recovery_browser", path=str(Path(__file__).parent / "browser" / "component"))
