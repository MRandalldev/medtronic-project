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
            st.html('<section class="welcome"><small>RECOVERY COMPANION</small><div><h1>One day<br> at a time.</h1><p>Your plan, your check-ins, and Reco by your side.</p></div><small>Every beat, a new day</small></section>')
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
if guest:
    navigation = st.navigation([welcome_page], position="hidden")

else:
    if oidc:
        data.bind_account(st.user["iss"], st.user["sub"])
    elif signed:
        data.bind_account("local-email", st.session_state.local_identity)
    today = st.Page("pages/4_Dashboard.py", title="Today", icon=":material/home:", url_path="today")
    checkin = st.Page("pages/3_Check_in.py", title="Daily check-in", icon=":material/fact_check:")
    calendar = st.Page("pages/6_Calendar.py", title="Calendar", icon=":material/calendar_month:")
    papers = st.Page("pages/2_Upload_papers.py", title="Discharge papers", icon=":material/description:")
    devices = st.Page("pages/watch.py", title="Devices", icon=":material/watch:")
    connections = st.Page("pages/connections.py", title="Health connections", icon=":material/favorite:")
    profile = st.Page("pages/1_Onboarding.py", title="My profile", icon=":material/person:")
    assistant = st.Page("pages/5_Assistant.py", title="Ask Reco", icon=":material/chat:")
    directory = st.Page("pages/directory.py", title="Find my care team", icon=":material/local_hospital:")
    settings_page = st.Page("pages/settings.py", title="Settings", icon=":material/settings:")
    progress = st.Page("pages/progress.py", title="Recovery dashboard", icon=":material/monitoring:")
    inbox = st.Page("pages/messages.py", title="Messages", icon=":material/forum:")
    sections = {"Today": [today, checkin, calendar],
                "My recovery": [progress, papers, devices, profile],
                "Support": [assistant, inbox, directory, settings_page]}
    if demo:
        sections["Demo views"] = [st.Page("pages/7_Care_team.py", title="Care team view", icon=":material/groups:"),
                                  st.Page("pages/caregiver.py", title="Caregiver view", icon=":material/family_restroom:")]
    pages = [p for group in sections.values() for p in group] + [connections]
    navigation = st.navigation([welcome_page, *pages], position="hidden")
    with st.sidebar:
        ui.patient_card(data.get_patient())
        for section, items in sections.items():
            st.html(f'<p class="nav-section">{section}</p>')
            for page in items:
                current = page.url_path == navigation.url_path
                with st.container(key=f"nav_current" if current else f"nav_{page.url_path or 'home'}"):
                    new = data.unread(data.get_patient(), "Care team") if page is inbox else 0
                    st.page_link(page, label=f"Messages · {new} new" if new else None)
        with st.container(key="help_box"):
            st.html('<p class="help-title">Need help now?</p>')
            ui.call_button("Call 911", "tel:911", "side_911", primary=True,
                           demo_note="Demo: on a phone this opens the dialer with 911. Your phone asks you to confirm.")
            care = data.care_phone(data.get_patient())
            if care:
                ui.call_button(f"Call care team · {care}", "tel:" + ui._digits(care), "side_care")
    if st.sidebar.button("Sign out" if signed else "Leave demo", key="leave_workspace"):
        st.session_state.clear()
        if oidc:
            st.logout()
        st.switch_page(welcome_page)
    with st.sidebar.container(key="sidebar_brand"):
        st.markdown("**Recovery Companion**")
    if signed and (st.session_state.pop("new_signup", False) or not data.get_patient().get("name")) and not st.session_state.get("opened_profile"):
        st.session_state.opened_profile = True
        st.switch_page(profile)
    if navigation.url_path == "" or st.session_state.pop("enter_workspace", False):
        st.session_state.pop("enter_workspace", None)
        st.switch_page(today)

# A plain keyed container, not st.empty(): an empty placeholder can be torn down and rebuilt on a rerun,
# which reset the page and its scroll position after ticking a dose.
with st.container(key="guest_view" if guest else "workspace_view"):
    if not guest:
        ui.appearance(key="appearance_workspace", height=36)
    navigation.run()
