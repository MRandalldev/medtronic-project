"""
pages/watch.py — Devices: a simulated smartwatch for the demo. (Owner: Jaiden)

No real watch is connected. Readings are made up but have the same shape a real
watch sync would add to the patient's vitals, so the check-in's mismatch
detection and the care team view react to them. Every simulated reading is
labelled "simulated" and can be removed.
"""
import random
from datetime import timedelta

import pandas as pd
import streamlit as st

import data

SCENARIOS = {
    "Heart rate climbing tonight": [82, 86, 91, 97, 104, 112],
    "Steady recovery": [78, 80, 79, 81, 78, 80],
}
# Step count for the day at each reading: resting on the couch while the pulse climbs, short walks on a steady day.
STEPS = {
    "Heart rate climbing tonight": [1840, 1840, 1846, 1850, 1850, 1852],
    "Steady recovery": [900, 1450, 2100, 2600, 3150, 3600],
}

st.title("Devices")
st.caption("Watch and blood pressure cuff readings are simulated for this demo: heart rate, steps and blood pressure. No device is connected.")

p = data.get_patient()
vitals = p.setdefault("vitals", [])


def base_reading():
    """Copy the latest real oxygen, temperature and weight so only the heart rate changes."""
    last = next((v for v in reversed(vitals) if not v.get("simulated")), vitals[-1] if vitals else {})
    return {k: last[k] for k in ("spo2", "temp_f", "weight_lb") if k in last}


def add_reading(hr, when, steps=None):
    vitals.append({**base_reading(), "time": when.strftime("%Y-%m-%d %H:%M"), "heart_rate": int(hr), "simulated": True,
                   **({"steps": int(steps)} if steps is not None else {})})


with st.container(border=True):
    st.subheader("Smartwatch")
    sims = [v for v in vitals if v.get("simulated")]
    st.markdown(f"**Status:** {'Connected (simulated)' if sims else 'Ready (simulated)'}"
                + (f" · last reading {sims[-1]['time'][-5:]}" if sims else ""))
    left, right = st.columns([2, 1])
    scenario = left.selectbox("Play a scenario", list(SCENARIOS), help="Adds a series of readings over the last three hours.")
    if right.button("Play scenario", type="primary", width="stretch"):
        p["vitals"] = vitals = [v for v in vitals if not v.get("simulated")]
        now = data.now_local()
        for i, hr in enumerate(SCENARIOS[scenario]):
            add_reading(hr, now - timedelta(minutes=30 * (len(SCENARIOS[scenario]) - 1 - i)), STEPS[scenario][i])
        data.save_patient(p)
        st.toast(f"Played “{scenario}”: {len(SCENARIOS[scenario])} readings. Now do today's check-in.")
        st.rerun()  # so the status line and chart show the new readings

    with st.expander("Send a single reading"):
        hr = st.slider("Resting heart rate to send (bpm)", 50, 140, 112)
        if st.button("Simulate watch reading"):
            add_reading(hr, data.now_local())
            data.save_patient(p)
            st.success(f"Watch reading received: resting heart rate {hr} bpm. Now do today's check-in.")

    with st.expander("Send a blood pressure reading (simulated cuff)"):
        top, bottom = st.columns(2)
        sys_value = top.number_input("Top number", 60, 260, 128, key="cuff_sys")
        dia_value = bottom.number_input("Bottom number", 30, 160, 78, key="cuff_dia")
        if st.button("Simulate cuff reading"):
            vitals.append({"time": data.now_local().strftime("%Y-%m-%d %H:%M"), "bp_sys": int(sys_value), "bp_dia": int(dia_value), "simulated": True})
            data.save_patient(p)
            st.success(f"Cuff reading received: {int(sys_value)}/{int(dia_value)}. It is checked at your next check-in and shown on your dashboard.")

    auto = st.toggle("Auto-sync a new reading every 20 seconds while this page is open", key="watch_auto")

    @st.fragment(run_every="20s" if auto else None)
    def live_feed():
        patient = data.get_patient()
        readings = patient.get("vitals", [])
        if auto and readings:
            last = readings[-1]
            drift = random.choice([-2, -1, 0, 1, 2]) + (2 if last.get("heart_rate", 80) < 100 and scenario.startswith("Heart") else 0)
            readings.append({**base_reading(), "time": data.now_local().strftime("%Y-%m-%d %H:%M"),
                             "heart_rate": max(50, min(140, last.get("heart_rate", 80) + drift)), "simulated": True})
            data.save_patient(patient)
        timed = [v for v in readings if "heart_rate" in v]
        if timed:  # chart the last 24 hours around the newest reading, on a real time axis
            newest = pd.to_datetime(timed[-1]["time"])
            timed = [v for v in timed if pd.to_datetime(v["time"]) >= newest - pd.Timedelta(hours=24)]
        recent = timed[-12:]
        if recent:
            latest = recent[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("Latest heart rate", f"{latest['heart_rate']} bpm",
                      delta=(latest["heart_rate"] - recent[-2]["heart_rate"]) if len(recent) > 1 else None,
                      delta_color="inverse", help=f"{'simulated' if latest.get('simulated') else 'saved'} reading at {latest['time']}")
            merged = data.latest_vitals(patient)
            m2.metric("Steps today", f"{merged['steps']:,}" if "steps" in merged else "–")
            m3.metric("Blood pressure", f"{merged['bp_sys']}/{merged['bp_dia']}" if "bp_sys" in merged and "bp_dia" in merged else "–")
            frame = pd.DataFrame(recent)
            frame["time"] = pd.to_datetime(frame["time"])
            import altair as alt  # zoomed y-axis: starting at 0 would flatten the climb the demo needs to show
            chart = alt.Chart(frame).mark_line(color="#4f6bff", point=alt.OverlayMarkDef(color="#4f6bff", size=70)).encode(
                x=alt.X("time:T", title=None), y=alt.Y("heart_rate:Q", title="bpm", scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip("time:T", format="%b %d %H:%M"), "heart_rate:Q"])
            st.altair_chart(chart, height=220)

    live_feed()

    if any(v.get("simulated") for v in data.get_patient().get("vitals", [])) and st.button("Remove simulated readings"):
        p["vitals"] = [v for v in data.get_patient()["vitals"] if not v.get("simulated")]
        data.save_patient(p)
        st.rerun()

with st.container(border=True):
    st.subheader("Apple Health")
    st.write("Bring in heart-rate readings from an iPhone: import a Health export, or set up a shortcut that sends new readings.")
    st.page_link("pages/connections.py", label="Connect Apple Health", icon=":material/favorite:")
    st.caption("Fully automatic syncing needs a native iPhone app with HealthKit permission. That's the next step after this prototype.")
