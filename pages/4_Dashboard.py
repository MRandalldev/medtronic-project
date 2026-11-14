from datetime import date

import pandas as pd
import streamlit as st
import data

p = data.get_patient()
st.caption("MY RECOVERY   /   TODAY")
st.title(f"Hello, {p.get('name', '').split(' ')[0] or 'there'}")
st.caption(date.today().strftime("%A, %B %d, %Y"))
today = date.today().isoformat()
doses = [(med["name"], time) for med in p.get("plan", {}).get("medications", []) for time in med["times"]]
logged = p.get("med_log", {}).get(today, {})
taken = sum(bool(logged.get(f"{name} {time}")) for name, time in doses)
if doses:
    with st.container(border=True):
        st.subheader("Have you taken your medication?")
        st.progress(taken / len(doses), text=f"{taken} of {len(doses)} scheduled doses marked taken today")
        st.page_link("pages/6_Calendar.py", label="Review my doses →")
left, right = st.columns([1.45, 1], gap="medium")
with left:
    with st.container(border=True):
        st.subheader("Daily check-in")
        st.write("Record how you feel and compare it with your last check-in.")
        st.page_link("pages/3_Check_in.py", label="Start check-in →")
    with st.container(border=True):
        st.subheader("Recovery readings")
        imported = p.get("apple_readings", [])
        readings = imported or p.get("vitals", [])
        if readings:
            df = pd.DataFrame(readings).set_index("time")
            field = st.radio("Measurement", ["Heart rate (bpm)"] if imported else ["Heart rate (bpm)", "Oxygen (%)"], horizontal=True)
            st.line_chart(df["heart_rate" if field.startswith("Heart") else "spo2"], color="#148778")
            st.caption("Apple Health · imported snapshot" if imported else "Simulated wearable readings")
        else:
            st.write("No readings recorded.")
with right:
    with st.container(border=True):
        st.subheader("Medications today")
        meds = p.get("plan", {}).get("medications", [])
        for m in meds:
            st.text(f"{', '.join(m['times'])}   {m['name']}")
        if not meds:
            st.write("Your medication schedule will appear here.")
        st.page_link("pages/6_Calendar.py", label="Open schedule →")
    with st.container(border=True):
        st.subheader("Upcoming visits")
        for visit in p.get("plan", {}).get("follow_ups", []):
            st.text(f"{visit['date']}   {visit['with']}")
        if not p.get("plan", {}).get("follow_ups"):
            st.write("No visit recorded.")
    st.page_link("pages/5_Assistant.py", label="Ask about my instructions →")
st.subheader("Recent documents")
for doc in p.get("documents", [])[-3:]:
    with st.expander(doc["name"]):
        st.text(doc["text"][:3000])
st.page_link("pages/2_Upload_papers.py", label="Open discharge papers →")
