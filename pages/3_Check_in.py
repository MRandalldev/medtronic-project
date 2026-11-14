import streamlit as st

import backend
import data
import ui

ui.demo_badge()
p = data.get_patient()
day = data.days_since_surgery(p)
ui.page_header("Daily check-in", f"Day {day} after surgery." if day is not None else "How are you feeling today?")

questions = backend.checkin_questions(p, day)
answers = {}
for q in questions:
    answers[q["id"]] = st.radio(q["text"], q["options"], horizontal=True, index=None, key=f"q_{q['id']}")

if st.button("Submit check-in", type="primary", disabled=None in answers.values()):
    vitals = data.latest_vitals(p)
    result = backend.score_checkin(answers, vitals)
    data.add_checkin(answers, result["level"], result["reasons"])
    st.session_state["last_result"] = result
    st.session_state["mismatch"] = backend.check_mismatch(answers, vitals)

if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    ui.alert_banner(r["level"], r["reasons"])
    if st.session_state.get("mismatch"):
        st.info(st.session_state["mismatch"])
