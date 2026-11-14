"""Shared patient conversation for the full page and floating Reco launcher."""
from uuid import uuid4

import requests
import streamlit as st

import data
import grounding
from browser_engine import select_passage

WELCOME = [
    {"title": "Getting started", "text": "Choose Sign up, enter your email, password and name, then verify your code.", "tags": "create account sign up register verification email password"},
    {"title": "Getting started", "text": "Choose Open demo patient to explore Marcus’s fictional recovery plan.", "tags": "demo try start"},
]


def chat(scope, guest=False):
    patient = {} if guest else data.get_patient()
    history = st.session_state.setdefault("guest_chat", []) if guest else patient.setdefault("assistant_history", [])
    transcript = st.container()
    with st.form("ask_" + scope, clear_on_submit=True):
        question = st.text_input("Ask Reco", placeholder="How can I get started?" if guest else "When is my next visit?", max_chars=1200)
        sent = st.form_submit_button("Ask", type="primary")
    if sent and question.strip():
        question = question.strip()
        result = grounding.urgent_guidance(question)
        rows = grounding.candidates(question, patient)
        if guest:
            terms = set(question.lower().split())
            relevant = sorted(WELCOME, key=lambda r: len(terms.intersection(r["tags"].split())), reverse=True)
            rows = [r for r in relevant if terms.intersection(r["tags"].split())] or rows
        if not result and rows:
            try:
                with st.spinner("Reco is reading your sources…"):
                    result = grounding.compose(rows, grounding.select(question, rows))
            except (requests.RequestException, ValueError, KeyError, TypeError):
                st.session_state["reco_pending"] = dict(id=uuid4().hex, rows=rows, question=question, guest=guest)
        if result or not rows:
            st.session_state.pop("reco_pending", None)
            history.append({"question": question, **(result or grounding.compose([], []))})
            if not guest:
                data.save_patient(patient)

    pending = st.session_state.get("reco_pending")
    if pending and pending["guest"] == guest:
        rows = pending["rows"]
        panel = st.empty()
        with panel.container():
            st.caption("Preparing your reply on this device. First use downloads language files.")
            choice = select_passage(id=pending["id"], schema=grounding.selection_schema(len(rows)),
                                    messages=[{"role": "system", "content": grounding.SYSTEM},
                                              {"role": "user", "content": grounding.prompt(pending["question"], rows)}],
                                    key=scope + pending["id"])
            use_sources = st.button("Show saved source now", key="source_" + scope)
        if use_sources or (choice and choice.get("id") == pending["id"]):
            ids = [1] if use_sources or choice.get("unavailable") else choice.get("ids", [])
            history.append({"question": pending["question"], **grounding.compose(rows, ids)})
            st.session_state.pop("reco_pending")
            panel.empty()
            if not guest:
                data.save_patient(patient)


    with transcript:
        for turn in history[-4:]:
            st.chat_message("user").text(turn["question"])
            with st.chat_message("assistant"):
                st.text(turn["answer"])
                for source in turn["sources"]:
                    st.caption(source)


def launcher(guest=False):
    with st.container(key="reco_dock"):
        if st.button("Ask Reco", key="reco_open", help="Open your recovery assistant"):
            conversation(guest)


@st.dialog("Reco · Recovery assistant", dismissible=True)
def conversation(guest):
    if guest:
        st.caption("Ask about signing in or getting started.")
    chat("dock", guest)
