from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

import streamlit as st
import data
from health_import import import_health

st.title("Health connections")
st.subheader("Apple Health")
st.write("Import a snapshot of heart-rate readings from an Apple Health export. Use a fictional export for this demo.")
st.caption("On iPhone, open Health → your profile → Export All Health Data. Choose the ZIP or export.xml. Up to 100 recent readings are saved.")
upload = st.file_uploader("Apple Health export", type=["xml", "zip"], max_upload_size=32)
p = data.get_patient()
if st.button("Import readings", disabled=not upload):
    try:
        rows = import_health(upload)
        if rows:
            p["apple_readings"] = rows
            data.save_patient(p)
            st.success(f"Saved {len(rows)} readings to your profile.")
        else:
            st.info("This export contains no supported heart-rate readings.")
    except (ValueError, ParseError, BadZipFile, RuntimeError, OSError) as exc:
        st.error(f"Could not read this export. {exc}")
if p.get("apple_readings"):
    st.write(f"Last imported reading · {p['apple_readings'][-1]['time']}")
    if st.button("Remove imported readings"):
        p.pop("apple_readings")
        data.save_patient(p)
        st.rerun()
st.caption("Live syncing requires an authorized HealthKit app on your Apple device.")
