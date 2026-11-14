from datetime import date

import streamlit as st
import data

p = data.get_patient()
st.title("Your recovery profile")
st.caption("Use fictional details for this hackathon. You can update them at any time.")


def saved_date(key):
    try:
        return date.fromisoformat(p.get(key, ""))
    except (TypeError, ValueError):
        return None


with st.form("onboarding"):
    name = st.text_input("Preferred name", p["name"])
    left, right = st.columns(2)
    age = left.number_input("Age (optional)", min_value=0, max_value=120, value=p["age"])
    height = right.number_input("Height in inches (optional)", min_value=1, max_value=110, value=p["height_in"])
    surgery = st.text_input("Procedure", p["surgery"])
    left, right = st.columns(2)
    surgery_date = left.date_input("Surgery date", value=saved_date("surgery_date"))
    last_appt = right.date_input("Last appointment", value=saved_date("last_appointment"))
    hospital = st.text_input("Hospital", p.get("hospital", ""))
    doctor = st.text_input("Doctor or care team", p["doctor"])
    caregiver = st.text_input("Caregiver (optional)", p.get("caregiver", ""))
    medications = st.text_area("Medicines you report taking (one per line)", p.get("reported_meds", ""))
    note = st.text_input("Something you want the assistant to remember (optional)", p.get("preference", ""))
    if st.form_submit_button("Save profile", type="primary"):
        if not name.strip():
            st.warning("Enter a preferred name.")
        else:
            if hospital.strip() != p.get("hospital", ""):
                p.pop("facility_id", None)
            if doctor.strip() != p.get("doctor", ""):
                p.pop("npi", None)
            p.update(name=name.strip(), age=age, height_in=height, surgery=surgery.strip(),
                     surgery_date=surgery_date.isoformat() if surgery_date else "",
                     last_appointment=last_appt.isoformat() if last_appt else "",
                     hospital=hospital.strip(), doctor=doctor.strip(), caregiver=caregiver.strip(),
                     reported_meds=medications.strip(), preference=note.strip())
            data.save_patient(p)
            st.success("Profile saved.")
st.page_link("pages/2_Upload_papers.py", label="Add discharge instructions →")
st.page_link("pages/directory.py", label="Find my hospital or clinician →")
