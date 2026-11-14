from datetime import date

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
alerts = p.get("alerts", [])
waiting = sum(not a.get("ack") for a in alerts)
if not alerts:
    st.success("No flags.")
else:
    st.caption(f"{waiting} waiting for you, {len(alerts) - waiting} acknowledged. Newest first.")
for index in range(len(alerts) - 1, -1, -1):
    alert = alerts[index]
    reasons = "; ".join(r["message"] for r in alert.get("reasons", []))
    with st.container(border=True, key=f"flag_{index}"):
        text = f"**{alert['level'].upper()}** · {data.human_time(alert.get('time', ''))} · {reasons}"
        # if/else, not a one-line conditional: Streamlit "magic" prints the value of a bare expression.
        if alert["level"] == "red":
            st.error(text)
        else:
            st.warning(text)
        if alert.get("ack"):
            st.caption(f"Acknowledged by {alert['ack']['by']} · {data.human_time(alert['ack']['time'])}. The patient can see this.")
        elif st.button("Acknowledge and tell the patient", key=f"ack_{index}"):
            data.acknowledge_alert(index)
            topic = ui._topic(alert["reasons"][0]["message"]) if alert.get("reasons") else "your alert"
            data.add_message("Care team", f"We saw your alert about {topic}. "
                             + ("If you have not called 911 yet and still have this symptom, call now. " if alert["level"] == "red" else "")
                             + "A nurse will call you today.")
            st.rerun()

st.subheader("Visits")
for index, visit in enumerate(p.get("plan", {}).get("follow_ups", [])):
    with st.container(border=True, key=f"visit_{index}"):
        status = visit.get("status")
        st.write(f"**{visit['with']}** · {data.human_date(visit.get('date', ''))}" + (f" · {visit['purpose']}" if visit.get("purpose") else ""))
        if status == "confirmed":
            st.success("Patient confirmed.")
        elif status:
            st.warning("Patient asked to reschedule.")
        elif visit.get("date"):
            st.caption("Waiting for the patient to confirm.")
        if status == "reschedule requested" or not visit.get("date"):
            try:
                start = date.fromisoformat(visit.get("date", ""))
            except ValueError:
                start = data.now_local().date()
            new_day = st.date_input("Set a date", value=max(start, data.now_local().date()), min_value=data.now_local().date(), key=f"visit_day_{index}")
            if st.button("Save date and tell the patient", key=f"visit_save_{index}"):
                data.schedule_visit(index, new_day.isoformat())
                st.rerun()
questions = data.visit_questions(p)
if questions:
    with st.expander(f"What the patient wants to raise at the next visit ({len(questions)})"):
        for q in questions:
            st.markdown(f"- {q}")

st.subheader("Messages")
ui.thread(p, "Care team")
data.mark_read("Patient")
