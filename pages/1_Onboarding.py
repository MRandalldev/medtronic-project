import streamlit as st

import data
import ui

ui.demo_badge()
ui.page_header("About you", "A few questions so your plan fits you.")
p = data.get_patient()

with st.form("onboarding"):
    name = st.text_input("Name", p["name"])
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 110, p["age"])
    height = c2.number_input("Height (inches)", 48, 90, p["height_in"])
    surgery = st.text_input("Surgery", p["surgery"])
    c3, c4 = st.columns(2)
    surgery_date = c3.text_input("Surgery date (YYYY-MM-DD)", p["surgery_date"])
    last_appt = c4.text_input("Last appointment (YYYY-MM-DD)", p["last_appointment"])
    doctor = st.text_input("Your doctor", p["doctor"])
    caregiver = st.text_input("Family member or caregiver (optional)", p.get("caregiver", ""))
    if st.form_submit_button("Save", type="primary"):
        p.update(name=name, age=int(age), height_in=int(height), surgery=surgery,
                 surgery_date=surgery_date, last_appointment=last_appt, doctor=doctor, caregiver=caregiver)
        data.save_patient(p)
        st.success("Saved. Next: upload your discharge papers.")

st.divider()
st.subheader("Connect your health data")
st.caption("Demo: these load simulated data. The real version would connect through Apple Health and hospital records (FHIR).")
c5, c6 = st.columns(2)
c5.button("Connect Apple Health (simulated)", disabled=True, use_container_width=True)
c6.button("Connect hospital records (simulated)", disabled=True, use_container_width=True)
