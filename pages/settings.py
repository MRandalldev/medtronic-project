import streamlit as st

import data
import ui

p = data.get_patient()
prefs = data.settings(p)
st.title("Settings")

with st.container(border=True):
    st.subheader("Emergency help")
    st.caption("These power the one-tap call and text buttons that appear when a check-in or Reco finds a warning sign.")
    with st.form("emergency_settings"):
        countdown = st.toggle("Start a 10-second countdown to call 911 when I report a 911-level symptom",
                              value=prefs["countdown"],
                              help="You can cancel it. Your phone always asks you to confirm before it places a call; "
                                   "no website can call 911 on its own.")
        left, right = st.columns(2)
        care = left.text_input("Care team phone", data.care_phone(p), placeholder="(555) 010-0199",
                               help="Usually printed on your discharge papers. We fill it in when we read them.")
        caregiver = right.text_input("Caregiver's phone (for one-tap texts)", prefs["caregiver_phone"])
        if st.form_submit_button("Save", type="primary"):
            digits = lambda n: sum(ch.isdigit() for ch in n)
            if (care and digits(care) < 10) or (caregiver and digits(caregiver) < 10):
                st.warning("Phone numbers need at least 10 digits.")
            else:
                p["care_phone"] = care.strip()
                p["settings"] = {**prefs, "countdown": countdown, "caregiver_phone": caregiver.strip()}
                data.save_patient(p)
                st.success("Saved.")
    if ui.demo_safe():
        st.caption("Demo mode: call and text buttons explain what would happen instead of dialing.")

with st.container(border=True):
    st.subheader("Reminders")
    from datetime import time as _time
    try:
        current = _time.fromisoformat(prefs["checkin_time"])
    except ValueError:
        current = _time(9, 0)
    chosen = st.time_input("Daily check-in reminder time", current, step=900,
                           help="Used when you download your schedule from the Calendar page. Your phone's calendar shows the alert.")
    if chosen != current:
        p["settings"] = {**prefs, "checkin_time": chosen.strftime("%H:%M")}
        data.save_patient(p)
        st.success(f"Check-in reminder set for {data.clock_12(chosen.strftime('%H:%M'))}. Download your schedule again from the Calendar to update your phone.")
    st.caption("A website cannot ring your phone by itself. Reminders reach you through your phone's calendar: "
               "download the schedule once from the Calendar page.")

with st.container(border=True):
    st.subheader("Your recovery plan")
    st.page_link("pages/1_Onboarding.py", label="My profile", icon=":material/person:")
    st.page_link("pages/2_Upload_papers.py", label="Discharge papers", icon=":material/description:")
    st.page_link("pages/directory.py", label="Find my care team", icon=":material/local_hospital:")
    st.page_link("pages/connections.py", label="Health connections (iPhone)", icon=":material/favorite:")

with st.container(border=True):
    st.subheader("Appearance")
    st.write("Use the Dark mode / Light mode button at the top right of any page. Your choice is remembered on this device.")

if st.session_state.get("demo"):
    with st.container(border=True):
        st.subheader("Demo tools")
        st.page_link("pages/7_Care_team.py", label="Care team view", icon=":material/groups:")
        st.page_link("pages/caregiver.py", label="Caregiver view", icon=":material/family_restroom:")
