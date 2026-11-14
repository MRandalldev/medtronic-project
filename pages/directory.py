import streamlit as st
import data
import provider_directory as directory
import hospital_index

st.title("Find my care team")
st.write("Choose the hospital named on your discharge papers. Then you can find your clinician.")
p = data.get_patient()
index = hospital_index.load()
US_STATES = ("AK AL AR AZ CA CO CT DC DE FL GA HI IA ID IL IN KS KY LA MA MD ME MI MN MO MS MT NC ND NE NH NJ NM NV NY "
             "OH OK OR PA RI SC SD TN TX UT VA VT WA WI WV WY").split()
DEMO_HOSPITAL = ("Greensboro Heart & Vascular Center (fictional)", "Greensboro", "NC", "DEMO-0001")


def save_hospital(h):
    p.update(hospital=h[0], hospital_city=h[1], hospital_state=h[2], facility_id=h[3])
    data.save_patient(p)
    st.success(f"Saved {h[0]}.")


if index is None:
    st.warning("The hospital list isn't available right now. You can type your hospital in My profile.")
    st.page_link("pages/1_Onboarding.py", label="Open My profile", icon=":material/person:")
else:
    states = index.states()
    default = p.get("hospital_state") or ("NC" if st.session_state.get("demo") else None)
    left, right = st.columns([1, 3])
    state = left.selectbox("State", states, index=states.index(default) if default in states else None,
                           placeholder="Choose", key="hospital_state_pick")
    if state:
        options = list(index.by_state.get(state, []))
        if st.session_state.get("demo") and state == "NC":
            options = [DEMO_HOSPITAL] + options
        choice = right.selectbox(f"Hospital ({len(options)} in {state})", options, index=None,
                                 format_func=lambda r: f"{r[0]} · {r[1]}", placeholder="Start typing the hospital name",
                                 key="hospital_pick")
        if choice and st.button("Save hospital", type="primary"):
            save_hospital(choice)
    with st.expander("Don't know the state? Search every hospital"):
        query = st.text_input("Hospital name or city", placeholder="e.g. moses cone greensboro", key="hospital_query")
        if query.strip():
            hits = index.search(query)
            if hits:
                pick = st.selectbox(f"{len(hits)} best matches", hits, index=0, key="hospital_hits",
                                    format_func=lambda r: f"{r[0]} · {r[1]}, {r[2]}")
                if st.button("Save this hospital", key="save_hit"):
                    save_hospital(pick)
            else:
                st.caption("No matches. Try fewer words, or just the city.")
    st.caption("From the CMS Hospital General Information dataset.")
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
    saved_state = data.get_patient().get("hospital_state")
    state = st.selectbox("State", US_STATES, index=US_STATES.index(saved_state) if saved_state in US_STATES else None,
                         placeholder="Choose") or ""
    search = st.form_submit_button("Search")
if search:
    st.session_state.providers = []
    if len(last.strip()) < 2 or len(state.strip()) != 2:
        st.warning("Enter a last name and choose a state.")
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
