import streamlit as st

import backend
import data
import ui

ui.demo_badge()
ui.page_header("Recovery assistant", "Answers from your discharge papers and trusted health sources. It does not diagnose.")
p = data.get_patient()

if "chat" not in st.session_state:
    st.session_state["chat"] = []

for msg in st.session_state["chat"]:
    with st.chat_message(msg["role"]):
        st.write(msg["text"])
        if msg.get("sources"):
            st.caption("Sources: " + ", ".join(msg["sources"]))

question = st.chat_input("Ask about your recovery")
if question:
    st.session_state["chat"].append({"role": "user", "text": question})
    with st.spinner("Checking your papers and sources..."):
        result = backend.ask_assistant(question, p)
    st.session_state["chat"].append({"role": "assistant", "text": result["answer"], "sources": result["sources"]})
    st.rerun()

st.caption("Having symptoms? Use the daily check-in, or call 911 in an emergency.")
