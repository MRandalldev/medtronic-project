import hashlib
import streamlit as st
from browser_engine import select_passage
import data
import grounding

st.title("Recovery assistant")
st.caption("Find a passage in your synthetic documents or recovery references. For an emergency, call your local emergency number.")
p = data.get_patient()
engine = st.radio("Answer using", ["Source lookup","Ollama","WebLLM"], horizontal=True)
with st.expander("What my assistant remembers"):
    st.caption("Save a preference to use in future searches. Edit it here or in My profile.")
    preference = st.text_input("Personal preference", p.get("preference", ""), max_chars=300)
    if st.button("Save preference"):
        p["preference"] = preference.strip()
        data.save_patient(p)
        st.success("Preference saved.")
question = st.chat_input("Ask about your recovery papers", max_chars=1200)
if question:
    st.session_state.pending_question = question
    st.session_state.pop("answered_request", None)
q = st.session_state.get("pending_question")
if q:
    key = hashlib.sha256((engine + q).encode()).hexdigest()
    if key != st.session_state.get("answered_request"):
        result = grounding.urgent_guidance(q)
        rows = grounding.candidates(q,p)
        if not result and engine == "WebLLM" and rows:
            st.caption("The first use downloads model files to this browser. A WebGPU-capable device is required.")
            selection = select_passage(id=key,count=len(rows),messages=[{"role":"system","content":grounding.SYSTEM},{"role":"user","content":grounding.prompt(q,rows)}],key="browser_"+key)
            if selection and selection.get("id")==key:
                choice = selection.get("choice","")
                if choice in [str(i) for i in range(1,len(rows)+1)]:
                    row=rows[int(choice)-1]
                    result={"answer":row["text"],"sources":[row["title"],row.get("url","")]}
                else:
                    result={"answer":"No supporting passage selected.","sources":[]}
        elif not result:
            with st.spinner("Finding a supporting passage…"):
                result=grounding.answer(q,p,engine)
        if result:
            p.setdefault("assistant_history",[]).append({"question":q,**result})
            data.save_patient(p)
            st.session_state.answered_request=key
            st.session_state.pop("pending_question",None)
            st.rerun()
for turn in p.get("assistant_history",[])[-10:]:
    with st.chat_message("user"):
        st.text(turn["question"])
    with st.chat_message("assistant"):
        st.text(turn["answer"])
        for source in filter(None,turn["sources"]):
            st.caption(source)
