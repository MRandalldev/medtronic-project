import streamlit as st
import login_screen
import data
import ui
import reco

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
        st.html('<div class="reco-brand"><span class="reco-face" aria-hidden="true">◡</span>Reco</div>')
        st.subheader("Your recovery companion")
        st.caption("Hackathon workspace for fictional recovery plans.")
        if configured:
            if st.button("Sign in or create an account", type="primary"):
                st.login()
        else:
            login_screen.form()
        if st.button("Open demo patient", type="secondary"):
            st.session_state.clear()
            st.session_state["demo"] = True
            st.rerun()

oidc = configured and st.user.is_logged_in
signed = oidc or bool(st.session_state.get("local_identity"))
demo = bool(st.session_state.get("demo")) and not signed
if not signed and not demo:
    navigation = st.navigation([st.Page(welcome, title="Welcome")])
    reco.launcher(guest=True)
    navigation.run()
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
        st.Page("pages/1_Onboarding.py", title="My profile", visibility="hidden"),
        st.Page("pages/2_Upload_papers.py", title="Discharge papers", visibility="hidden"),
        st.Page("pages/3_Check_in.py", title="Daily check-in"),
        st.Page("pages/5_Assistant.py", title="Reco", visibility="hidden"),
        st.Page("pages/6_Calendar.py", title="Calendar"),
        st.Page("pages/directory.py", title="Find my care team", visibility="hidden"),
    ]
    pages.append(st.Page("pages/connections.py", title="Health connections"))
    if demo:
        pages.append(st.Page("pages/7_Care_team.py", title="Care team demo", visibility="hidden"))
    navigation = st.navigation(pages)
    with st.sidebar.expander("More options"):
        for page in pages:
            if page.title in ("My profile", "Discharge papers", "Find my care team", "Care team demo"):
                st.page_link(page)
    reco.launcher()
    if signed and (st.session_state.pop("new_signup", False) or not data.get_patient().get("name")) and not st.session_state.get("opened_profile"):
        st.session_state.opened_profile = True
        st.switch_page(pages[1])
    navigation.run()
