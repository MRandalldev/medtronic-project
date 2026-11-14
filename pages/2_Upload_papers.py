from pathlib import Path

import streamlit as st

import backend
import data
import ui

DEMO_PAPERS = Path(__file__).parent.parent / "data" / "demo_discharge_papers.txt"

ui.demo_badge()
ui.page_header("Your discharge papers", "Upload or paste them. We turn them into your daily plan: medicines, warning signs and visits.")

uploaded = st.file_uploader("Upload a text file of your discharge instructions", type=["txt"])
pasted = st.text_area("Or paste the text here", height=200)
c1, c2 = st.columns(2)
build = c1.button("Build my plan", type="primary", use_container_width=True)
use_demo = c2.button("Use the demo patient's papers", use_container_width=True)

if build or use_demo:
    if use_demo:
        name, text = "Demo discharge papers (fictional)", DEMO_PAPERS.read_text(encoding="utf-8")
    else:
        name = uploaded.name if uploaded else "Pasted instructions"
        text = uploaded.read().decode("utf-8", errors="ignore") if uploaded else pasted
    if not text.strip():
        st.warning("Add your papers first.")
    else:
        with st.spinner("Reading your papers..."):
            plan = backend.extract_plan(text[:50000])
        method = plan.pop("method", "reader")
        if not (plan["medications"] or plan["follow_ups"] or plan["warning_signs"]):
            st.warning("We couldn't find medicines, warning signs or visits in that text, so your current plan "
                       "was not changed. Check that you added your discharge instructions.")
            st.stop()
        data.add_document(name, text[:50000])
        data.set_plan(plan)
        import plan_reader
        filled = data.fill_profile(plan_reader.read_profile(text))  # only empty fields; never overwrites
        how = "with AI" if method == "ai" else "with the on-device reader (no internet needed)"
        st.success(f"Your plan is ready. Read {how}: {len(plan['medications'])} medicines, "
                   f"{len(plan['warning_signs'])} warning signs, {len(plan['follow_ups'])} visits. "
                   "Check it against your papers.")
        if filled:
            labels = {"name": "name", "age": "age", "surgery": "procedure", "surgery_date": "surgery date",
                      "doctor": "surgeon", "caregiver": "caregiver", "care_phone": "care team phone"}
            st.info("Also filled in your profile: " + ", ".join(labels.get(f, f) for f in filled) + ".")
            st.page_link("pages/1_Onboarding.py", label="Review my profile", icon=":material/person:")

plan = data.get_patient().get("plan", {})
if plan.get("medications") or plan.get("follow_ups") or plan.get("warning_signs"):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("Medications")
        for m in plan.get("medications", []):
            st.write(f"**{m['name']}**: {m['dose']} ({', '.join(m['times'])})")
    with c2:
        st.subheader("Warning signs")
        for w in plan.get("warning_signs", []):
            st.write(f"- {w}")
    with c3:
        st.subheader("Follow-ups")
        for f in plan.get("follow_ups", []):
            st.write(f"**{data.human_date(f['date'], relative=False)}**: {f['with']}" + (f" ({f['purpose']})" if f["purpose"] else ""))
