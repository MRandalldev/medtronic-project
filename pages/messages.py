"""Messages between the patient and the care team."""
import streamlit as st

import data
import ui

p = data.get_patient()
ui.page_header("Messages", "Write to your care team. For anything urgent, call them or 911.")
if st.session_state.get("demo"):
    st.caption("Demo: open Care team view in the sidebar to read this as the nurse and reply.")
else:
    st.caption("This prototype is not connected to a real clinic yet. Messages are saved to your record so you can bring them to a visit.")
acks = [a for a in p.get("alerts", []) if a.get("ack")]
if acks:
    last = acks[-1]
    st.success(f"Your care team saw your alert from {data.human_time(last['time'])} ({ui._topic(last['reasons'][0]['message']) if last.get('reasons') else 'warning sign'}).")
ui.thread(p, "Patient")
data.mark_read("Care team")  # after showing them, so "new" is visible once
