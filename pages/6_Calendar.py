from datetime import date

import streamlit as st

import data
import ui

ui.demo_badge()
ui.page_header("Medications and appointments")
p = data.get_patient()
today = date.today().isoformat()
plan = p.get("plan", {})

st.subheader(f"Today's doses ({today})")
log = p.get("med_log", {}).get(today, {})
for m in plan.get("medications", []):
    for t in m["times"]:
        key = f"{m['name']} {t}"
        taken = st.checkbox(f"{t}: {m['name']}, {m['dose']}", value=log.get(key, False), key=f"dose_{key}")
        if taken != log.get(key, False):
            data.log_dose(today, key, taken)

st.subheader("Refills")
for m in plan.get("medications", []):
    st.write(f"**{m['name']}**: refill by {m.get('refill_date', 'unknown')}")

st.subheader("Upcoming appointments")
for f in plan.get("follow_ups", []):
    st.write(f"**{f['date']}**: {f['with']} ({f['purpose']})")

st.caption("Demo: reminders appear here. The real version would send phone notifications.")
