import streamlit as st

import backend
import data
import ui

ui.demo_badge()
ui.page_header("Care team view", "For the surgeon or nurse. Demo sign-in.")

if not st.session_state.get("care_signed_in"):
    st.text_input("Clinician email", value="nurse@example-hospital.org")
    if st.button("Sign in as care team", type="primary"):
        st.session_state["care_signed_in"] = True
        st.rerun()
    st.stop()

p = data.get_patient()
s = backend.care_team_summary(p)

st.subheader(f"{p['name']}: day {data.days_since_surgery(p)}")
st.write(s["summary"])
st.write(f"**Next follow-up:** {s['next_follow_up']}")

st.subheader("Flags")
if s["flags"]:
    for f in s["flags"]:
        st.error(f) if f.startswith("RED") else st.warning(f)
else:
    st.success("No flags.")

st.subheader("Messages")
for m in p.get("messages", []):
    st.write(f"**{m['from']}** ({m['time']}): {m['text']}")
reply = st.text_input("Message the patient")
if st.button("Send") and reply:
    data.add_message("Care team", reply)
    st.rerun()
