import streamlit as st

import backend
import data
import ui

ui.demo_badge()
ui.page_header("Your discharge papers", "Save a fictional discharge document to search in your recovery assistant.")

uploaded = st.file_uploader("Upload a text file of your discharge instructions", type=["txt"])
pasted = st.text_area("Or paste the text here", height=200)

if st.button("Save synthetic instructions", type="primary"):
    text = uploaded.read().decode("utf-8", errors="ignore") if uploaded else pasted
    if not text.strip():
        st.warning("Add your papers first.")
    else:
        data.add_document(uploaded.name if uploaded else "Pasted instructions", text[:50000])
        st.success("Document saved for source lookup. The medication schedule requires separate review.")

plan = data.get_patient().get("plan", {})
if plan:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("Medications")
        for m in plan.get("medications", []):
            st.write(f"**{m['name']}**, {m['dose']} at {', '.join(m['times'])}")
    with c2:
        st.subheader("Warning signs")
        for w in plan.get("warning_signs", []):
            st.write(f"- {w}")
    with c3:
        st.subheader("Follow-ups")
        for f in plan.get("follow_ups", []):
            st.write(f"**{f['date']}**: {f['with']} ({f['purpose']})")
