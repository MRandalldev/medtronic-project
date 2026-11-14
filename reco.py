"""Shared patient conversation for the full page and floating Reco launcher."""
from datetime import datetime
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


def record_turn(question, result, history, patient, guest):
    history.append({"question": question, **result})
    if guest:
        return
    if result.get("flag"):
        patient.setdefault("alerts", []).append({
            "time": datetime.now().isoformat(timespec="minutes"), "level": result["flag"],
            "reasons": [{"message": "Reported in chat: " + question, "source": result["sources"][0]}]})
    data.save_patient(patient)


def chat(scope, guest=False):
    patient = {} if guest else data.get_patient()
    history = st.session_state.setdefault("guest_chat", []) if guest else patient.setdefault("assistant_history", [])
    transcript = st.container()
    with st.form("ask_" + scope, clear_on_submit=True):
        question = st.text_input("Ask Reco", placeholder="How can I get started?" if guest else "When is my next visit?", max_chars=1200)
        sent = st.form_submit_button("Ask", type="primary")
    if sent and question.strip():
        question = question.strip()
        result = grounding.immediate_reply(question, patient)
        rows = grounding.candidates(question, patient)
        if guest:
            terms = set(question.lower().split())
            relevant = sorted(WELCOME, key=lambda r: len(terms.intersection(r["tags"].split())), reverse=True)
            rows = [r for r in relevant if terms.intersection(r["tags"].split())] or rows
        if not result:
            try:
                with st.spinner("Reco is reading your sources…"):
                    result = grounding.finish(question, rows, grounding.select(question, rows, history), history)
            except (requests.RequestException, ValueError, KeyError, TypeError):
                st.session_state["reco_pending"] = dict(id=uuid4().hex, rows=rows, question=question, guest=guest)
        if result:
            st.session_state.pop("reco_pending", None)
            record_turn(question, result, history, patient, guest)

    pending = st.session_state.get("reco_pending")
    if pending and pending["guest"] == guest:
        rows = pending["rows"]
        panel = st.empty()
        with panel.container():
            st.caption("Preparing your reply on this device. First use downloads language files.")
            choice = select_passage(id=pending["id"], schema=grounding.selection_schema(len(rows)),
                                    messages=[{"role": "system", "content": grounding.SYSTEM},
                                              {"role": "user", "content": grounding.prompt(pending["question"], rows, history)}],
                                    key=scope + pending["id"])
            use_sources = st.button("Reply without waiting", key="source_" + scope)
        if use_sources or (choice and choice.get("id") == pending["id"]):
            model_result = None if use_sources or choice.get("unavailable") else choice
            result = grounding.finish(pending["question"], rows, model_result, history)
            record_turn(pending["question"], result, history, patient, guest)
            st.session_state.pop("reco_pending")
            panel.empty()

    with transcript:
        for turn in history[-4:]:
            st.chat_message("user").text(turn["question"])
            with st.chat_message("assistant"):
                urgent = grounding.urgent_guidance(turn["question"])
                if urgent:
                    st.error(urgent["answer"])
                else:
                    st.text(turn["answer"])
                if turn.get("flag") and not guest:
                    st.caption("Flag saved in your recovery record. Contact your care team directly.")
                for source in (urgent or turn)["sources"]:
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
