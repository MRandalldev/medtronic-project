import streamlit as st

st.title("Settings")
with st.container(border=True):
    st.subheader("Your recovery plan")
    st.page_link("pages/1_Onboarding.py", label="My profile", icon=":material/person:")
    st.page_link("pages/2_Upload_papers.py", label="Discharge papers", icon=":material/description:")
    st.page_link("pages/directory.py", label="Find my care team", icon=":material/search:")
if st.session_state.get("demo"):
    with st.container(border=True):
        st.subheader("Demo tools")
        st.page_link("pages/7_Care_team.py", label="Care team demo", icon=":material/groups:")
