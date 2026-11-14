"""Recovery dashboard: milestones, medication adherence and health trends, all computed from the patient's record."""
from html import escape

import pandas as pd
import streamlit as st

import data
import ui

p = data.get_patient()
ui.page_header("Recovery dashboard", "Your milestones, medicines and trends in one place.")

day = data.days_since_surgery(p)
doses = data.adherence(p)
pains = [c["numbers"]["pain"] for c in p.get("checkins", []) if c.get("numbers", {}).get("pain") is not None]
a, b, c, d = st.columns(4)
a.metric("Recovery day", day if day is not None else "–")
b.metric("Check-in streak", f"{ui.check_in_streak(p)} day{'s' if ui.check_in_streak(p) != 1 else ''}")
c.metric("Doses taken (7 days)", f"{round(100 * doses['taken'] / doses['due'])}%" if doses["due"] else "–",
         help=f"{doses['taken']} of {doses['due']} scheduled doses marked taken since {data.human_date(doses['since'], relative=False)}."
         if doses["due"] else "Mark a dose as taken in the Calendar to start tracking.")
d.metric("Latest pain", f"{pains[-1]}/10" if pains else "–", delta=(pains[-1] - pains[-2]) or None if len(pains) > 1 else None, delta_color="inverse")

with st.container(border=True):
    st.subheader("Milestones")
    stones = data.milestones(p)
    upcoming = next((m for m in stones if not m["done"] and m["date"]), None)
    rows = []
    for m in stones:
        state = "done" if m["done"] else "next" if m is upcoming else ""
        when = data.human_date(m["date"], relative=not m["done"]) if m["date"] else "Not yet"
        rows.append(f'<div class="milestone {state}"><div class="dot">{"✓" if m["done"] else ""}</div>'
                    f'<div><div class="when">{escape(when)}</div><div class="what">{escape(m["label"])}</div></div></div>')
    st.html("".join(rows) if rows else "<p>Add your surgery date and discharge papers to see your milestones.</p>")
    st.caption("Built from your profile, your visits and the time limits written in your discharge papers.")

with st.container(border=True):
    st.subheader("Medicines")
    if doses["due"]:
        st.progress(doses["taken"] / doses["due"], text=f"{doses['taken']} of {doses['due']} scheduled doses marked taken")
        if doses["missed"]:
            st.write("Not marked as taken:")
            for when, name, clock in doses["missed"][-6:]:
                st.markdown(f"- {data.human_date(when, relative=False)} · {data.clock_12(clock)} · {name}")
            st.caption("Your care team sees missed doses too. If you took one and forgot to mark it, fix it in the Calendar.")
        else:
            st.success("Every scheduled dose so far is marked taken.")
    else:
        st.write("No doses marked yet. Tick a dose in the Calendar and your 7-day record starts here.")
    st.page_link("pages/6_Calendar.py", label="Open my doses →")

with st.container(border=True):
    st.subheader("Health trends")
    series = {}
    for check in p.get("checkins", []):
        n = check.get("numbers", {})
        for key, label in (("pain", "Pain (0–10)"), ("walk_min", "Minutes walked")):
            if n.get(key) is not None:
                series.setdefault(label, []).append((check["date"], n[key]))
    labels = {"heart_rate": "Heart rate (bpm)", "spo2": "Oxygen (%)", "temp_f": "Temperature (°F)", "weight_lb": "Weight (lb)",
              "bp_sys": "Blood pressure: top number", "bp_dia": "Blood pressure: bottom number", "steps": "Steps (watch)"}
    for row in p.get("vitals", []):
        for key, label in labels.items():
            if row.get(key) is not None:
                series.setdefault(label, []).append((row["time"], row[key]))
    if series:
        choice = st.selectbox("Measurement", list(series))
        frame = pd.DataFrame(series[choice], columns=["time", "value"])
        frame["time"] = pd.to_datetime(frame["time"])
        import altair as alt
        scale = alt.Scale(domain=[0, 10]) if choice.startswith("Pain") else alt.Scale(zero=choice.startswith(("Minutes", "Steps")))
        st.altair_chart(alt.Chart(frame).mark_line(color="#148778", point=alt.OverlayMarkDef(color="#148778", size=70)).encode(
            x=alt.X("time:T", title=None), y=alt.Y("value:Q", title=choice, scale=scale),
            tooltip=[alt.Tooltip("time:T", format="%b %d %H:%M"), alt.Tooltip("value:Q", title=choice)]), height=240)
        st.caption(f"{len(frame)} reading{'s' if len(frame) != 1 else ''}. Pain and walking come from your check-ins; "
                   "the rest from your check-in numbers and device readings.")
    else:
        st.write("Your trends appear after your first check-in or device reading.")

with st.container(border=True):
    st.subheader("Check-in history")
    history = [{"Date": data.human_date(ch["date"], relative=False),
                "Result": {"green": "All clear", "yellow": "Call care team", "red": "Emergency sign"}.get(ch.get("level"), ""),
                "Overall": ch.get("answers", {}).get("overall", ""),
                "Pain": ch.get("numbers", {}).get("pain"), "Walked (min)": ch.get("numbers", {}).get("walk_min")}
               for ch in reversed(p.get("checkins", [])[-10:])]
    if history:
        st.dataframe(pd.DataFrame(history), hide_index=True, width="stretch")
    else:
        st.write("No check-ins yet.")
        st.page_link("pages/3_Check_in.py", label="Do today's check-in →")
