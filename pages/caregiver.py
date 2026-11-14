"""Caregiver view: what a family member needs to help, without the patient's whole record."""
import streamlit as st

import data
import ui

p = data.get_patient()
first = (p.get("name") or "Your family member").split(" ")[0]
caregiver = p.get("caregiver", "").split("(")[0].strip()
ui.page_header("Caregiver view", f"What {caregiver.split()[0] if caregiver else 'a family member'} would see. Demo of the shared family view.")

with st.container(border=True):
    st.subheader("Today's update")
    st.write(data.daily_update(p))
    today = data.now_local().date().isoformat()
    open_alerts = [a for a in p.get("alerts", []) if a.get("time", "").startswith(today)]
    if open_alerts:
        worst = "red" if any(a["level"] == "red" for a in open_alerts) else "yellow"
        reasons = "; ".join(ui._short(r["message"]) for a in open_alerts for r in a.get("reasons", []))
        if worst == "red":
            st.error(f"{first} reported an emergency warning sign today: {reasons}. Make sure 911 was called.")
        else:
            st.warning(f"{first} should call the care team today about: {reasons}. You can help by making the call together.")

with st.container(border=True):
    st.subheader("Medicines today")
    logged = p.get("med_log", {}).get(today, {})
    doses = sorted(data.scheduled_doses(p), key=lambda d: d[1])
    for name, clock in doses:
        st.markdown(f"{'✅ taken' if logged.get(f'{name} {clock}') else '⬜ not marked'} · **{data.clock_12(clock)}** · {name}")
    if not doses:
        st.write("No scheduled medicines yet.")
    late = data.overdue_doses(p)
    if late:
        st.warning(f"{len(late)} dose{'s are' if len(late) != 1 else ' is'} more than an hour late. A gentle reminder may help.")

with st.container(border=True):
    st.subheader("How you can help")
    visit = data.next_visit(p)
    if visit:
        st.markdown(f"- **Drive to the next visit:** {data.human_date(visit[1]['date'])} with {visit[1]['with']}.")
    for r in data.refill_reminders(p):
        st.markdown(f"- **Pick up a refill:** {r['name']} by {data.human_date(r['date'])}.")
    for m in data.milestones(p):
        if not m["done"] and "Until then" in m["label"]:
            st.markdown(f"- **Until {data.human_date(m['date'], relative=False)}:** {m['label'].split('Until then: ')[1].split('. Ask')[0]}. Help with lifting and chores.")
    with st.expander("Warning signs to know"):
        for sign in p.get("plan", {}).get("warning_signs", []):
            st.markdown(f"- {sign}")
        if not p.get("plan", {}).get("warning_signs"):
            st.write("Warning signs appear here once discharge papers are added.")
    care = data.care_phone(p)
    if care:
        ui.call_button(f"Call the care team · {care}", "tel:" + ui._digits(care), "caregiver_care")
st.caption("This view shows today's summary only: no documents, no message history.")
