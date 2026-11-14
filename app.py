import streamlit as st
import login_screen
import data
import ui

st.set_page_config(page_title="Recovery Companion", page_icon="♡", layout="wide")
ui.theme()
try:
    configured = bool(st.secrets.get("auth", {}).get("client_id"))
except FileNotFoundError:
    configured = False

def welcome():
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown('<section class="welcome"><small>RECOVERY COMPANION</small><h1>Your recovery,<br>one day at a time.</h1><p>Keep your discharge instructions, daily check-ins and upcoming appointments together.</p></section>', unsafe_allow_html=True)
    with right:
        st.header("Welcome back")
        st.caption("Hackathon workspace for fictional recovery plans.")
        if configured:
            if st.button("Sign in or create an account", type="primary"):
                st.login()
        else:
            login_screen.form()
        if st.button("Open demo patient", type="secondary"):
            st.session_state["demo"] = True
            st.rerun()

oidc = configured and st.user.is_logged_in
signed = oidc or bool(st.session_state.get("local_identity"))
demo = bool(st.session_state.get("demo")) and not signed
if not signed and not demo:
    st.navigation([st.Page(welcome, title="Welcome")]).run()
else:
    if oidc:
        data.bind_account(st.user["iss"], st.user["sub"])
    elif signed:
        data.bind_account("local-email", st.session_state.local_identity)
    st.sidebar.title("Recovery Companion")
    st.sidebar.caption("Synthetic patient workspace")
    if st.sidebar.button("Sign out" if signed else "Leave demo"):
        st.session_state.clear()
        if oidc:
            st.logout()
        st.rerun()
    pages = [
        st.Page("pages/4_Dashboard.py", title="Today", icon=":material/home:", default=True),
        st.Page("pages/1_Onboarding.py", title="My profile"),
        st.Page("pages/2_Upload_papers.py", title="Discharge papers"),
        st.Page("pages/3_Check_in.py", title="Daily check-in"),
        st.Page("pages/5_Assistant.py", title="Recovery assistant"),
        st.Page("pages/6_Calendar.py", title="Medications & visits"),
        st.Page("pages/directory.py", title="Find my care team"),
    ]
    if demo:
        pages.append(st.Page("pages/7_Care_team.py", title="Care team demo"))
    navigation = st.navigation(pages)
    if signed and not data.get_patient().get("name") and not st.session_state.get("opened_profile"):
        st.session_state.opened_profile = True
        st.switch_page(pages[1])
    navigation.run()
