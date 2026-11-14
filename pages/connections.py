from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

import streamlit as st
import data
import health_connection
from urllib.parse import urlsplit
from health_import import import_health

st.title("Health connections")
st.subheader("Apple Health")
st.write("Connect an iPhone shortcut to share heart rate. You choose when it runs and can disconnect it here.")
owner = st.session_state.get("owner")
linked = health_connection.samples(owner)
if owner:
    if linked is None:
        consent = st.checkbox("Allow this shortcut to send heart rate and sample time to my recovery account.")
        if st.button("Connect Apple Health", disabled=not consent):
            st.session_state.health_key = health_connection.connect(owner)
            st.rerun()
    else:
        st.success(f"Shortcut access enabled · {len(linked)} readings received")
        if linked:
            st.caption("Latest sample · " + linked[-1]["time"])
        if st.button("Refresh readings"):
            st.rerun()
        if st.button("Disconnect and delete synced readings"):
            health_connection.disconnect(owner)
            st.session_state.pop("health_key", None)
            st.rerun()
else:
    st.info("Sign in to connect an iPhone to your own account. You can try a fictional export below.")

with st.expander("Set up the iPhone shortcut", expanded=bool(st.session_state.get("health_key"))):
    st.write("1. In Shortcuts on iPhone, create a shortcut. Add Find Health Samples. Choose Heart Rate, sort by Start Date (latest first), and limit to one sample.")
    st.write("2. Use Get Details of Health Samples to get its Start Date and Value. Format the date as ISO 8601 with a time zone. Use the numeric heart rate in beats per minute.")
    st.write("3. Add Get Contents of URL. Use the address below, select POST, and add an Authorization header with the value Bearer followed by a space and your connection key.")
    origin = urlsplit(st.context.url)
    st.code(f"{origin.scheme}://{origin.netloc}/health/readings", language=None)
    if origin.scheme != "https":
        st.caption("On iPhone, use the HTTPS address of the deployed workspace.")
    if st.session_state.get("health_key"):
        st.caption("Private connection key · copy this into your shortcut.")
        st.code(st.session_state.health_key, language=None)
        if st.button("Hide connection key"):
            del st.session_state.health_key
            st.rerun()
    elif owner and linked is not None and st.button("Replace connection key"):
        st.session_state.health_key = health_connection.connect(owner)
        st.rerun()
    st.write("4. Choose a JSON request body. Add a Number named heart_rate from Value and a Text field named time from the formatted date. Run the shortcut and allow Shortcuts to read Heart Rate and send to this site when iOS asks. Tap Refresh readings here.")
    st.caption("The key grants permission to submit heart rate only. Disconnecting it removes the synced readings. Health access for Shortcuts can also be managed on iPhone.")
    st.markdown("[Apple’s guide to finding Health samples](https://support.apple.com/guide/shortcuts/apd3c845e881/ios) · [Send a request in Shortcuts](https://support.apple.com/guide/shortcuts/apd58d46713f/ios)")

st.subheader("Import a snapshot")
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
