"""
pages/watch.py — simulated smartwatch reading for the demo. (Owner: Jaiden)

No real watch is connected. The button adds one made-up reading to the
patient's vitals, the same shape a real watch sync would add, so the
check-in's mismatch detection has something to react to.
"""
from datetime import datetime

import streamlit as st

import data

st.title("Smartwatch")
st.caption("Simulated for this demo. No watch is connected.")

p = data.get_patient()
vitals = p.setdefault("vitals", [])
last = dict(vitals[-1]) if vitals else {}

hr = st.slider("Resting heart rate to send (bpm)", 50, 140, 112)
if st.button("Simulate watch reading", type="primary"):
    reading = {k: last[k] for k in ("spo2", "temp_f", "weight_lb") if k in last}
    reading["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    reading["heart_rate"] = hr
    reading["simulated"] = True
    vitals.append(reading)
    data.save_patient(p)
    st.success(f"Watch reading received: resting heart rate {hr} bpm. Now do today's check-in.")

if vitals:
    latest = vitals[-1]
    label = "simulated" if latest.get("simulated") else "saved"
    st.metric("Latest heart rate", f"{latest.get('heart_rate', '—')} bpm", help=f"{label} reading at {latest['time']}")

sims = [v for v in vitals if v.get("simulated")]
if sims and st.button("Remove simulated readings"):
    p["vitals"] = [v for v in vitals if not v.get("simulated")]
    data.save_patient(p)
    st.rerun()
