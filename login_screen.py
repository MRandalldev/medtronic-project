import os
import streamlit as st
import account_access
import data
from registration import account_fields


def form():
    challenge = st.session_state.get("challenge")
    if challenge:
        st.subheader("Verify your account")
        if os.getenv("RECOVERY_SMTP_HOST"):
            st.write("Enter the six-digit code sent to your email.")
        else:
            st.info(f"Local demo delivery Â· In VS Code open .local/dev-mail/{challenge}.txt for your code.")
        with st.form("verification", clear_on_submit=True):
            code = st.text_input("Verification code", max_chars=6)
            if st.form_submit_button("Verify and continue", type="primary"):
                email = account_access.verify(challenge, code)
                if email:
                    name = st.session_state.get("signup_name")
                    st.session_state.clear()
                    st.session_state.local_identity = email
                    data.bind_account("local-email", email)
                    if name:
                        patient = data.get_patient()
                        patient["name"] = name
                        data.save_patient(patient)
                        st.session_state.new_signup = True
                    st.rerun()
                st.error("Invalid or expired code. Request a new one if needed.")
        if st.button("Start again"):
            st.session_state.pop("challenge", None)
            st.rerun()
        return
    mode = st.radio("Account", ["Sign in", "Sign up"], horizontal=True, label_visibility="collapsed")
    signup = mode == "Sign up"
    fields = account_fields(data={"signup": signup}, key="register" if signup else "signin",
                            on_submit_change=lambda: None)
    if fields.submit:
        values = fields.submit
        if signup and (not values["name"].strip() or values["password"] != values["confirm"]):
            st.error("Enter your name and make sure both passwords match.")
            return
        try:
            challenge = account_access.begin(values["email"], values["password"], signup)
            st.session_state.challenge = challenge
            st.session_state.signup_name = values["name"].strip()[:100] if signup else None
            st.rerun()
        except ValueError as error:
            st.error(str(error))
