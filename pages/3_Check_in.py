import streamlit as st

import backend
import data
import ui

PULSE_SOURCE = "https://medlineplus.gov/ency/patientinstructions/000102.htm"

ui.demo_badge()
p = data.get_patient()
day = data.days_since_surgery(p)
ui.page_header("Daily check-in", f"Day {day} after surgery. About 30 seconds." if day is not None else "How are you feeling today?")

today = data.now_local().date().isoformat()
result = st.session_state.get("last_result") if st.session_state.get("last_result_date") == today else None

# The result goes first, so a frightened patient sees the next step without scrolling.
if result:
    ui.alert_banner(result["level"], result["reasons"])
    question = st.session_state.get("mismatch")
    if question:
        with st.container(border=True, key="mismatch_box"):
            st.markdown("**One more question**")
            st.write(question)
            answered = st.session_state.get("mismatch_answer")
            if answered is None:
                yes, no = st.columns(2)
                if yes.button("Yes, I feel worse than I said", width="stretch", key="mismatch_yes"):
                    data.add_alert("yellow", [{"message": "Said they feel worse than reported after their heart rate changed: "
                                                          "call your care team today.", "source": PULSE_SOURCE}])
                    st.session_state["mismatch_answer"] = "yes"
                    st.rerun()
                if no.button("No, I really feel fine", width="stretch", key="mismatch_no"):
                    st.session_state["mismatch_answer"] = "no"
                    st.rerun()
            elif answered == "yes":
                st.success("Thanks for being honest. Your care team now sees that you feel worse, along with your reading.")
            else:
                st.info("Thanks. Your care team still sees the reading, so they can decide whether to check in.")

questions = backend.checkin_questions(p, day)
yes_no = [q for q in questions if q["options"] == ["No", "Yes"]]
trends = [q for q in questions if q["options"] != ["No", "Yes"]]

form_area = st.expander("Check in again", expanded=False) if result else st.container()
with form_area:
    answers = {}
    with st.container(border=True):
        st.subheader("Any of these today?")
        st.caption("Tick everything that applies. Leave the rest blank.")
        cols = st.columns(2)
        for i, q in enumerate(yes_no):
            answers[q["id"]] = "Yes" if cols[i % 2].checkbox(q["text"], key=f"q_{q['id']}") else "No"
    for q in trends:
        answers[q["id"]] = st.radio(q["text"], q["options"], horizontal=True, index=None, key=f"q_{q['id']}")
    missing = None in answers.values()
    if missing:
        st.caption("Answer the leg swelling question to submit.")
    if st.button("Submit check-in", type="primary", disabled=missing):
        vitals = data.latest_vitals(p)
        scored = backend.score_checkin(answers, vitals)
        data.add_checkin(answers, scored["level"], scored["reasons"])
        st.session_state.update(last_result=scored, last_result_date=today,
                                mismatch=backend.check_mismatch(answers, vitals), mismatch_answer=None)
        st.rerun()  # refresh the sidebar too, so "Check-in due" turns into "Checked in today" right away
