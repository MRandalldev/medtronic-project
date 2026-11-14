import pandas as pd
import streamlit as st

import data
import health_connection
import ui

p = data.get_patient()
st.caption("MY RECOVERY   /   TODAY")
st.title(f"Hello, {p.get('name', '').split(' ')[0] or 'there'}")
st.caption(data.now_local().strftime("%A, %B %d, %Y"))
today = data.now_local().date().isoformat()

# 1. One next step, so a tired patient never has to work out what matters most.
ui.next_action_card(p)

# 2. Word from the care team: a seen alert, or a new message.
seen = [a for a in p.get("alerts", []) if a.get("ack") and a.get("time", "").startswith(today)]
new_messages = data.unread(p, "Care team")
if seen or new_messages:
    with st.container(border=True, key="team_word"):
        if seen:
            st.success(f"Your care team saw today's alert at {data.human_time(seen[-1]['ack']['time']).split(' at ')[1]}.")
        if new_messages:
            st.info(f"You have {new_messages} new message{'s' if new_messages != 1 else ''} from your care team.")
        st.page_link("pages/messages.py", label="Open messages →")

# 3. Today's doses.
doses = data.scheduled_doses(p)  # only clock times are scheduled doses; "as needed" medicines are counted separately
logged = p.get("med_log", {}).get(today, {})
taken = sum(bool(logged.get(f"{name} {time}")) for name, time in doses)
if doses:
    with st.container(border=True):
        st.subheader("Today's medicines")
        st.progress(taken / len(doses), text=f"{taken} of {len(doses)} scheduled doses marked taken today")
        for name, time in sorted(doses, key=lambda d: d[1]):
            label = f"{name} {time}"
            saved = bool(logged.get(label))
            if st.checkbox(f"{data.clock_12(time)} · {name}", value=saved, key=f"today_dose_{label}") != saved:
                data.log_dose(today, label, not saved)
                st.rerun()
        st.caption("Tick a dose when you take it.")
        st.page_link("pages/6_Calendar.py", label="See the full schedule →")
ui.prn_card(p, "today")

# 4. Reminders: refills and the next visit.
refills = data.refill_reminders(p)
visit = data.next_visit(p)
left, right = st.columns([1, 1], gap="medium")
with left:
    with st.container(border=True):
        st.subheader("Refills")
        if not refills:
            st.write("No refills due in the next two weeks.")
        for i, r in enumerate(refills):
            when = data.human_date(r["date"])
            if r["days"] <= 7:
                st.warning(f"**{r['name']}** · refill by {when}. Call your pharmacy now so you do not run out.")
            else:
                st.write(f"**{r['name']}** · refill by {when}")
            if st.button("I refilled it", key=f"refilled_{i}"):
                data.mark_refilled(r["name"], r["date"])
                st.rerun()
        st.caption("Refill dates come from your discharge papers. Reminders start two weeks ahead.")
with right:
    with st.container(border=True):
        st.subheader("Next visit")
        if not visit:
            st.write("No visit with a date yet.")
        else:
            index, v = visit
            st.write(f"**{data.human_date(v['date'])}** with {v['with']}" + (f" · {v['purpose']}" if v.get("purpose") else ""))
            status = v.get("status")
            if status == "confirmed":
                st.success("You confirmed this visit. Your care team can see that.")
            elif status:
                st.info("You asked to reschedule. Your care team has your message.")
            else:
                yes, no = st.columns(2)
                if yes.button("I'll be there", key="visit_confirm", width="stretch"):
                    data.set_visit_status(index, "confirmed")
                    st.rerun()
                if no.button("I need to reschedule", key="visit_move", width="stretch"):
                    data.set_visit_status(index, "reschedule requested")
                    st.rerun()
            with st.expander("Get ready for this visit"):
                questions = data.visit_questions(p)
                st.caption("Questions worth asking, built from your check-ins, doses and what Reco could not answer. Add your own.")
                for q in questions:
                    st.markdown(f"- {q}")
                if not questions:
                    st.write("Nothing flagged so far. Add anything you want to ask.")
                with st.form("add_question", clear_on_submit=True, border=False):
                    mine = st.text_input("Add a question for the visit", max_chars=200)
                    if st.form_submit_button("Add") and mine.strip():
                        p.setdefault("visit_questions", []).append(mine.strip())
                        data.save_patient(p)
                        st.rerun()

# 5. Keep family in the loop.
caregiver = p.get("caregiver", "").split("(")[0].strip()
phone = data.settings(p).get("caregiver_phone", "")
if caregiver and phone:
    from urllib.parse import quote
    with st.container(border=True):
        st.subheader(f"Update {caregiver.split()[0]}")
        update = data.daily_update(p)
        st.write(update)
        ui.call_button(f"Text this update to {caregiver.split()[0]}", f"sms:{ui._digits(phone)}?&body={quote(update)}", "share_update")

# 6. Readings and papers.
with st.container(border=True):
    st.subheader("Recovery readings")
    imported = p.get("apple_readings", [])
    synced = health_connection.samples(st.session_state.get("owner")) or []
    readings = [r for r in (synced or imported or p.get("vitals", [])) if "heart_rate" in r]
    if readings:
        frame = pd.DataFrame(readings)
        frame["time"] = pd.to_datetime(frame["time"])
        import altair as alt
        st.altair_chart(alt.Chart(frame).mark_line(color="#4f6bff", point=alt.OverlayMarkDef(color="#4f6bff", size=70)).encode(
            x=alt.X("time:T", title=None), y=alt.Y("heart_rate:Q", title="Heart rate (bpm)", scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("time:T", format="%b %d %H:%M"), "heart_rate:Q"]), height=200)
        st.caption("Apple Health · iPhone shortcut" if synced else "Apple Health · imported snapshot" if imported
                   else "Heart rate from your saved readings" + (" (some simulated)" if any(r.get("simulated") for r in readings) else ""))
    else:
        st.write("No readings recorded.")
    st.page_link("pages/progress.py", label="See all my trends and milestones →")
st.subheader("Recent documents")
for doc in p.get("documents", [])[-3:]:
    with st.expander(doc["name"]):
        st.text(doc["text"][:3000])
st.page_link("pages/2_Upload_papers.py", label="Open discharge papers →")
st.page_link("pages/5_Assistant.py", label="Ask Reco about my instructions →")
