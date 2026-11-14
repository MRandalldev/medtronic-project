import os
import streamlit as st
import account_access


def form():
    challenge = st.session_state.get("challenge")
    if challenge:
        st.subheader("Verify your account")
        if os.getenv("RECOVERY_SMTP_HOST"):
            st.write("Enter the six-digit code sent to your email.")
        else:
            st.info(f"Local demo delivery · In VS Code open .local/dev-mail/{challenge}.txt for your code.")
        with st.form("verification", clear_on_submit=True):
            code = st.text_input("Verification code", max_chars=6)
            if st.form_submit_button("Verify and continue", type="primary"):
                email = account_access.verify(challenge, code)
                if email:
                    st.session_state.clear()
                    st.session_state.local_identity = email
                    st.rerun()
                st.error("Invalid or expired code. Request a new one if needed.")
        if st.button("Start again"):
            st.session_state.pop("challenge", None)
            st.rerun()
        return
    mode = st.radio("Account", ["Sign in", "Sign up"], horizontal=True, label_visibility="collapsed")
    with st.form("account_" + mode, clear_on_submit=True):
        email = st.text_input("Email address")
        password = st.text_input("Password", type="password", help="Use at least 10 characters.")
        if st.form_submit_button("Send verification code", type="primary"):
            try:
                st.session_state.challenge = account_access.begin(email, password, mode == "Sign up")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
