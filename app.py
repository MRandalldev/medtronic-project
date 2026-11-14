import streamlit as st

import data
import ui

st.set_page_config(page_title="Recovery Companion", page_icon="❤️", layout="wide")
ui.demo_badge()

ui.page_header("Recovery Companion", "Your recovery plan, daily check-ins and care team in one place.")

if not st.session_state.get("signed_in"):
    st.subheader("Sign in")
    st.text_input("Email", value="demo.patient@example.com")
    st.text_input("Password", value="demo", type="password")
    col1, col2 = st.columns(2)
    if col1.button("Sign in", type="primary", use_container_width=True):
        st.session_state["signed_in"] = True
        data.get_patient()
        st.rerun()
    if col2.button("Judge mode: start with the demo patient", use_container_width=True):
        data.reset_to_sample()
        st.session_state["signed_in"] = True
        st.rerun()
else:
    p = data.get_patient()
    st.success(f"Signed in as {p['name']}. Day {data.days_since_surgery(p)} after surgery.")
    st.write("Use the sidebar: **Onboarding → Upload papers → Check-in → Dashboard**.")
    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()
