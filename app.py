import os

import streamlit as st
import login_screen
import data
import ui
import reco

st.set_page_config(page_title="Recovery Companion", page_icon="♡", layout="wide")
ui.theme()
reco.browser_engine.warm()
try:
    configured = bool(st.secrets.get("auth", {}).get("client_id"))
except FileNotFoundError:
    configured = False

def enter_demo():
    st.session_state.clear()
    st.session_state.demo = True
    st.session_state.enter_workspace = True


def welcome():
    email_settings = ("DATABASE_URL", "RECOVERY_SMTP_HOST", "RECOVERY_SMTP_USER",
                      "RECOVERY_SMTP_PASSWORD", "RECOVERY_MAIL_FROM")
    hosted_unavailable = bool(os.getenv("VERCEL") and not all(os.getenv(key) for key in email_settings))
    with st.container(key="auth_shell"):
        left, right = st.columns([1.08, 1], gap="large", vertical_alignment="top")
        with left:
            st.html('<section class="welcome"><small>RECOVERY COMPANION</small><div><h1>One day<br> at a time.</h1><p>Your plan, your check-ins, and Reco by your side.</p></div><small>Earthrise · NASA / Apollo 8</small></section>')
        with right, st.container(key="auth_panel"):
            ui.appearance(key="appearance_guest", height=36)
            st.html('<div class="reco-brand"><span class="reco-face" aria-hidden="true"></span>Reco</div>')
            if configured:
                st.title("Welcome back")
                if st.button("Sign in or create an account", type="primary"):
                    st.login()
            else:
                login_screen.form(unavailable=hosted_unavailable)
            st.divider()
            st.button("Open demo patient", key="enter_demo", on_click=enter_demo, width="stretch")
            st.caption("Explore a fictional patient’s recovery plan.")


oidc = configured and st.user.is_logged_in
signed = oidc or bool(st.session_state.get("local_identity"))
demo = bool(st.session_state.get("demo")) and not signed
welcome_page = st.Page(welcome, title="Welcome", default=True, visibility="hidden")
guest = not (signed or demo)
# Every run replaces the same main region, including after a page switch.
reco.launcher(guest=guest)
page_slot = st.empty()
if guest:
    navigation = st.navigation([welcome_page], position="hidden")

else:
    if oidc:
        data.bind_account(st.user["iss"], st.user["sub"])
    elif signed:
        data.bind_account("local-email", st.session_state.local_identity)
    pages = [
        st.Page("pages/4_Dashboard.py", title="Today", icon=":material/home:", url_path="today"),
        st.Page("pages/1_Onboarding.py", title="My profile", visibility="hidden"),
        st.Page("pages/2_Upload_papers.py", title="Discharge papers", visibility="hidden"),
        st.Page("pages/3_Check_in.py", title="Daily check-in"),
        st.Page("pages/5_Assistant.py", title="Reco", visibility="hidden"),
        st.Page("pages/6_Calendar.py", title="Calendar"),
        st.Page("pages/directory.py", title="Find my care team", visibility="hidden"),
    ]
    pages.append(st.Page("pages/connections.py", title="Health connections"))
    pages.append(st.Page("pages/settings.py", title="Settings", icon=":material/settings:"))
    if demo:
        pages.append(st.Page("pages/7_Care_team.py", title="Care team demo", visibility="hidden"))
    navigation = st.navigation([welcome_page, *pages])
    if st.sidebar.button("Sign out" if signed else "Leave demo", key="leave_workspace"):
        st.session_state.clear()
        if oidc:
            st.logout()
        st.switch_page(welcome_page)
    with st.sidebar.container(key="sidebar_brand"):
        st.markdown("**Recovery Companion**")
    if signed and (st.session_state.pop("new_signup", False) or not data.get_patient().get("name")) and not st.session_state.get("opened_profile"):
        st.session_state.opened_profile = True
        st.switch_page(pages[1])
    if navigation.url_path == "" or st.session_state.pop("enter_workspace", False):
        st.session_state.pop("enter_workspace", None)
        st.switch_page(pages[0])

with page_slot.container(key="guest_view" if guest else "workspace_view"):
    if not guest:
        ui.appearance(key="appearance_workspace", height=36)
    navigation.run()
