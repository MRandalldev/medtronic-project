import streamlit as st

import backend
import data
import ui

PULSE_SOURCE = "https://medlineplus.gov/ency/patientinstructions/000102.htm"

ui.demo_badge()
p = data.get_patient()
day = data.days_since_surgery(p)
ui.page_header("Daily check-in", f"Day {day} after surgery. About a minute." if day is not None else "How are you feeling today?")

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
                    data.add_alert("yellow", [{"message": "Said they feel worse than reported after their readings changed: "
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
    ui.checkin_recap(p)

questions = backend.checkin_questions(p, day)
yes_no = [q for q in questions if q["options"] == ["No", "Yes"]]
trends = [q for q in questions if q["options"] != ["No", "Yes"]]

form_area = st.expander("Check in again", expanded=False) if result else st.container()
with form_area:
    answers = {}
    with st.container(border=True):
        st.subheader("1 · Any of these today?")
        st.caption("Tick everything that applies. Leave the rest blank.")
        cols = st.columns(2)
        for i, q in enumerate(yes_no):
            answers[q["id"]] = "Yes" if cols[i % 2].checkbox(q["text"], key=f"q_{q['id']}") else "No"
    with st.container(border=True):
        st.subheader("2 · How is your recovery going?")
        for q in trends:
            answers[q["id"]] = st.radio(q["text"], q["options"], horizontal=True, index=None, key=f"q_{q['id']}")
        pain = st.pills("Pain right now (0 = none, 10 = worst you can imagine)", list(range(11)), key="n_pain")
        walk = st.number_input("Minutes you walked today", 0, 600, 0, step=5, key="n_walk")
    with st.container(border=True):
        st.subheader("3 · Your numbers (optional)")
        st.caption("Fill in what you measured today. Discharge papers usually ask for pulse and weight each morning "
                   "and temperature each evening. Leave a box empty if you did not measure it.")
        a, b, c = st.columns(3)
        pulse = a.number_input("Resting pulse (beats per minute)", 30, 220, None, step=1, key="n_pulse")
        temp = b.number_input("Temperature (°F)", 93.0, 108.0, None, step=0.1, format="%.1f", key="n_temp")
        weight = c.number_input("Weight (lb)", 60.0, 600.0, None, step=0.1, format="%.1f", key="n_weight")
        d, e, _ = st.columns(3)
        bp_sys = d.number_input("Blood pressure: top number", 60, 260, None, step=1, key="n_bp_sys")
        bp_dia = e.number_input("Blood pressure: bottom number", 30, 160, None, step=1, key="n_bp_dia")
    missing = None in answers.values() or pain is None
    half_bp = (bp_sys is None) != (bp_dia is None)
    if missing:
        st.caption("Answer the two questions and tap your pain level in part 2 to submit.")
    if half_bp:
        st.caption("Enter both blood pressure numbers, or leave both empty.")
    if st.button("Submit check-in", type="primary", disabled=missing or half_bp):
        numbers = {"pain": pain, "walk_min": walk, "heart_rate": pulse, "temp_f": temp, "weight_lb": weight,
                   "bp_sys": bp_sys, "bp_dia": bp_dia}
        numbers = {k: v for k, v in numbers.items() if v is not None}
        data.record_numbers(numbers)  # typed numbers become a reading, so the same sourced rules score them
        vitals = data.latest_vitals(p)
        scored = backend.score_checkin(answers, vitals)
        data.add_checkin(answers, scored["level"], scored["reasons"], numbers)
        st.session_state.update(last_result=scored, last_result_date=today,
                                mismatch=backend.check_mismatch(answers, vitals), mismatch_answer=None)
        st.rerun()  # refresh the sidebar too, so "Check-in due" turns into "Checked in today" right away
