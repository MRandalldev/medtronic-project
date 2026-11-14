import streamlit as st
import data
import provider_directory as directory

st.title("Find my care team")
st.write("Select the facility and clinician named on your discharge papers.")
term = st.text_input("Hospital name or city")
if st.button("Search", key="hospital_search") and term.strip():
    try:
        st.session_state.hits = [r for r in directory.hospitals() if term.strip().casefold() in " ".join(r[:2]).casefold()][:40]
    except Exception:
        st.session_state.hits = []
        st.warning("Hospital directory unavailable. You can enter your care team in My profile.")
if "hits" in st.session_state:
    h = st.selectbox("Hospital results", st.session_state.hits, format_func=lambda r: f"{r[0]} · {r[1]}, {r[2]}", index=None)
    if not st.session_state.hits:
        st.caption("No matching hospitals available.")
    if h and st.button("Save hospital"):
        p = data.get_patient()
        p.update(hospital=h[0], facility_id=h[3])
        data.save_patient(p)
        st.success("Hospital saved.")
p = data.get_patient()
if p.get("facility_id"):
    st.subheader(p["hospital"])
    surname = st.text_input("Filter affiliated clinicians by exact last name (optional)")
    if st.button("Search", key="affiliation_search"):
        try:
            hits = directory.affiliations(p["facility_id"], surname)
            st.session_state.affiliations = (p["facility_id"], hits)
        except Exception:
            st.session_state.pop("affiliations", None)
            st.warning("CMS affiliations are unavailable. Try the NPI search below.")
    facility, matches = st.session_state.get("affiliations", (None, []))
    if facility == p["facility_id"]:
        st.caption("Up to 50 CMS-listed clinicians. Enter a surname to narrow the list.")
        if matches:
            person = st.selectbox("Hospital clinicians", matches, index=None,
                                  format_func=lambda r: f"{r[0]} · NPI {r[1]}")
            if person and st.button("Save affiliated clinician"):
                p.update(doctor=person[0], npi=person[1])
                data.save_patient(p)
                st.success("Clinician saved.")
        else:
            st.info("No matching affiliation in this CMS dataset.")

st.subheader("Find a clinician by name and state")
with st.form("clinicians"):
    last = st.text_input("Clinician last name")
    state = st.text_input("State abbreviation", max_chars=2)
    search = st.form_submit_button("Search")
if search:
    st.session_state.providers = []
    if len(last.strip()) < 2 or len(state.strip()) != 2:
        st.warning("Enter a last name and two-letter state.")
    else:
        try:
            st.session_state.providers = directory.doctors(last.strip(), state.strip().upper())
        except Exception:
            st.warning("The registry is unavailable. Enter your clinician in My profile.")
if "providers" in st.session_state:
    provider = st.selectbox("Clinician results", st.session_state.providers, index=None, format_func=lambda r:f"{r[0]} · {r[2]} · {r[1]}")
    if not st.session_state.providers:
        st.caption("No matching clinicians available.")
    if provider and st.button("Save clinician"):
        p = data.get_patient()
        p.update(doctor=provider[0], npi=provider[1])
        data.save_patient(p)
        st.success("Clinician saved.")
st.caption("CMS reports facility affiliations. The separate NPI search identifies individual providers. Saving a provider records your selection only.")
st.markdown("[CMS hospitals](https://data.cms.gov/provider-data/dataset/xubh-q36u) · [CMS affiliations](https://data.cms.gov/provider-data/dataset/27ea-46a8) · [NPI registry](https://npiregistry.cms.hhs.gov/)")
