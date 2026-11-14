"""Shared patient conversation for the full page and floating Reco launcher."""
from datetime import datetime
from uuid import uuid4

import requests
import streamlit as st
from html import escape

import data
import grounding
import browser_engine
import health_connection
import os
from ui import artwork
import ui

WELCOME = [
    {"title": "Getting started", "text": "Choose Sign up, enter your email, password and name, then verify your code.", "tags": "create account sign up register verification email password"},
    {"title": "Getting started", "text": "Choose Open demo patient to explore Marcus’s fictional recovery plan.", "tags": "demo try start"},
]


def record_turn(question, result, history, patient, guest):
    result = grounding.with_suggestions(result, question, patient, guest)
    history.append({"question": question, **result})
    if guest:
        return
    if result.get("flag"):
        patient.setdefault("alerts", []).append({
            "time": data.now_local().strftime("%Y-%m-%d %H:%M"), "level": result["flag"],
            "reasons": [{"message": "Reported in chat: " + question, "source": result["sources"][0]}]})
    data.save_patient(patient)


def chat(scope, guest=False):
    patient = {} if guest else data.get_patient()
    history = st.session_state.setdefault("guest_chat", []) if guest else patient.setdefault("assistant_history", [])
    # The dock thread scrolls on its own and follows new messages; the composer stays pinned below it.
    transcript = (st.container(height=440, key="reco_thread", autoscroll=True, border=False) if scope == "dock"
                  else st.container(key="reco_thread_page"))
    pending = st.session_state.get("reco_pending")
    with st.form("ask_" + scope, clear_on_submit=True, border=scope == "dock"):
        with st.container(horizontal=True, key=f"reco_composer" if scope == "dock" else "reco_composer_page", gap="small"):
            question = st.text_input("Ask Reco", placeholder="Message Reco", max_chars=1200, label_visibility="collapsed", width="stretch")
            sent = st.form_submit_button("Ask", type="primary", width="content")
    clicked = st.session_state.pop("reco_click_" + scope, None)
    if clicked and clicked.get("kb"):
        # A clicked topic chip answers exactly that topic.
        st.session_state.pop("reco_pending", None)
        topic = grounding.topic_reply(clicked["kb"], patient)
        if topic:
            record_turn(clicked["label"], topic, history, patient, guest)
    elif clicked and clicked.get("ask"):
        question, sent = clicked["ask"], True
    if sent and question.strip():
        question = question.strip()
        # A new question supersedes any uncommitted inference, especially in an emergency.
        st.session_state.pop("reco_pending", None)
        result = grounding.immediate_reply(question, patient, history)
        if not result:
            context = patient
            if not guest and st.session_state.get("owner"):
                context = {**patient, "synced_readings": health_connection.samples(st.session_state.owner) or []}
            rows = grounding.retrieve(question, context, history)
            if guest:
                terms = set(question.lower().split())
                rows = [r for r in WELCOME if terms.intersection(r["tags"].split())] or rows
            try:  # Claude, when an API key is configured (works on Vercel too)
                choice = grounding.claude_select(question, rows, history)
                if choice:
                    result = grounding.finish(question, rows, choice, history)
            except Exception:
                result = None
            if not result and not os.getenv("VERCEL"):
                try:
                    result = grounding.finish(question, rows, grounding.select(question, rows, history), history)
                except (requests.RequestException, ValueError, KeyError, TypeError):
                    pass
            if not result:
                st.session_state.reco_pending = dict(id=uuid4().hex, rows=rows, question=question, guest=guest)
        if result:
            record_turn(question, result, history, patient, guest)

    pending = st.session_state.get("reco_pending")
    if pending and pending["guest"] == guest:
        rows, question = pending["rows"], pending["question"]
        choice = browser_engine.generate({
            "id": pending["id"], "dialogue": grounding.social_question(question),
            "schema": grounding.selection_schema(len(rows)),
            "messages": [{"role":"system", "content":grounding.SYSTEM},
                         {"role":"user", "content":grounding.prompt(question, rows, history)}]
        }, key="engine_" + scope)
        if isinstance(choice, dict) and choice.get("id") == pending["id"]:
            model = None if choice.get("unavailable") else choice
            record_turn(question, grounding.finish(question, rows, model, history), history, patient, guest)
            st.session_state.pop("reco_pending")
            pending = None

    with transcript:
        if not history and not pending:
            first = (patient.get("name") or "").split(" ")[0]
            hello = f"Hi {escape(first)}, I’m Reco." if first else "Hi, I’m Reco."
            st.html(f'<div class="reco-empty"><strong>{hello}</strong>'
                    'Ask me about your medicines, your visits, a symptom, or anything in your discharge papers.</div>')
        start = max(0, len(history) - 40)   # the whole recent conversation; the thread scrolls
        for index, turn in enumerate(history[start:], start=start):
            with st.container(key=f"turn_{scope}_{index}"):
                st.chat_message("user").text(turn["question"])
                with st.chat_message("assistant"):
                    if turn.get("flag") == "red":
                        st.error(turn["answer"])
                        if index == len(history) - 1:  # one-tap help under the newest emergency answer
                            ui.call_actions(patient if not guest else {}, f"reco_{scope}_{index}", emergency=True)
                    else:
                        st.text(turn["answer"])
                    if turn.get("flag") and not guest:
                        st.caption("Flag saved in your recovery record. Contact your care team directly.")
                    for source in turn["sources"]:
                        st.caption(source)
                    if turn.get("suggestions") and index == len(history) - 1:
                        st.caption("Pick one, or ask it another way:")
                        cols = st.columns(2)
                        for n, chip in enumerate(turn["suggestions"]):
                            with cols[n % 2]:
                                if chip.get("page"):
                                    if not guest:
                                        st.page_link(chip["page"], label=chip["label"], icon=":material/checklist:")
                                else:
                                    # on_click instead of st.rerun(): a full rerun would close the Reco dialog.
                                    st.button(chip["label"], key=f"chip_{scope}_{index}_{n}", width="stretch",
                                              on_click=st.session_state.__setitem__, args=("reco_click_" + scope, chip))
        if pending:
            st.chat_message("user").text(pending["question"])
            st.html('<div class="reco-typing" role="status" aria-label="Reco is writing"><i></i><i></i><i></i></div>')


def launcher(guest=False):
    with st.container(key="reco_dock"):
        if st.button(f"![Ask Reco]({artwork('reco-face.png')})", key="reco_open", help="Open your recovery assistant"):
            conversation(guest)


@st.dialog("Reco · Recovery assistant", dismissible=True)
def conversation(guest):
    if guest:
        st.caption("Ask about signing in or getting started.")
    chat("dock", guest)
