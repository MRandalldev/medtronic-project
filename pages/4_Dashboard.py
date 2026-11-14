import pandas as pd
import streamlit as st

import data
import ui

ui.demo_badge()
p = data.get_patient()
ui.page_header(f"Hi, {p['name'].split()[0]}", f"Day {data.days_since_surgery(p)} of your recovery")

checkins = p.get("checkins", [])
last = checkins[-1] if checkins else None
c1, c2, c3 = st.columns(3)
c1.metric("Today's status", last["level"].upper() if last else "No check-in yet")
c2.metric("Check-ins done", len(checkins))
follow = p.get("plan", {}).get("follow_ups", [])
c3.metric("Next follow-up", follow[0]["date"] if follow else "None")

if last and last["level"] != "green":
    ui.alert_banner(last["level"], last["reasons"])

st.subheader("Vital signs (simulated)")
vitals = p.get("vitals", [])
if vitals:
    df = pd.DataFrame(vitals).set_index("time")
    st.line_chart(df[["heart_rate", "spo2"]])

st.subheader("Recent documents")
docs = p.get("documents", [])
if docs:
    for d in docs[-3:]:
        with st.expander(d["name"]):
            st.write(d["text"][:1000])
else:
    st.caption("No documents yet. Upload your discharge papers.")
