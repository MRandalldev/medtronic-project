from datetime import date

import streamlit as st

import data

p = data.get_patient()


def saved_date(key):
    try:
        return date.fromisoformat(p.get(key, ""))
    except (TypeError, ValueError):
        return None


# One question at a time. Answers live in a draft until the last step saves them to the profile in one write
# (widgets that are not on screen lose their state, so each step copies its answers into the draft on Continue).
STEPS = [
    {"q": "What should we call you?", "hint": "This is how Reco and your dashboard greet you.",
     "fields": [("name", "text", "Preferred name")]},
    {"q": "What surgery did you have?", "hint": "Write it the way your discharge papers do, if you can.",
     "fields": [("surgery", "text", "Procedure"), ("surgery_date", "date", "Surgery date")]},
    {"q": "Where was your surgery?", "hint": "Your hospital helps Reco find the right care-team number.",
     "fields": [("hospital", "text", "Hospital"), ("last_appointment", "date", "Last appointment")]},
    {"q": "Who is your doctor or care team?", "hint": "The surgeon or clinic you call with questions.",
     "fields": [("doctor", "text", "Doctor or care team")]},
    {"q": "Which medicines are you taking?", "hint": "One per line. Your discharge papers will fill in the schedule.",
     "fields": [("reported_meds", "area", "Medicines you report taking")]},
    {"q": "Who is helping you at home?", "hint": "Optional. A family member or friend who can get your daily update.",
     "fields": [("caregiver", "text", "Caregiver (optional)")]},
    {"q": "A little about you", "hint": "Optional. Only used to read your numbers in context.",
     "fields": [("age", "int", "Age (optional)"), ("height_in", "int", "Height in inches (optional)")]},
    {"q": "Anything Reco should remember?", "hint": "Optional. For example: “I'm hard of hearing, so text me instead of calling.”",
     "fields": [("preference", "text", "Something you want the assistant to remember")]},
]

state = st.session_state
draft = state.setdefault("profile_draft", {key: (saved_date(key) if kind == "date" else p.get(key, 0 if kind == "int" else ""))
                                           for s in STEPS for key, kind, _ in s["fields"]})
index = min(state.setdefault("profile_step", 0), len(STEPS) - 1)
current = STEPS[index]

with st.container(key="quiz"), st.container(key="profile_quiz"):
    top = st.columns([1, 6], vertical_alignment="center")
    if index > 0 and top[0].button("←", key="profile_back", help="Back to the previous question"):
        state.profile_step = index - 1
        st.rerun()
    done = (index + 1) / len(STEPS)
    dots = "".join(f'<span class="dot{" done" if i <= index else ""}" style="left:{(i + 1) * 100 / len(STEPS) - 0.01:.2f}%"></span>'
                   for i in range(len(STEPS)))
    top[1].html(f'<div class="quiz-progress" role="img" aria-label="Question {index + 1} of {len(STEPS)}">'
                f'<span class="label">YOUR PROFILE · {index + 1} OF {len(STEPS)}</span>'
                f'<div class="track"><div class="fill" style="transform:scaleX({done:.3f})"></div>{dots}</div></div>')
    with st.container(key=f"q_{index}"):
        st.html(f'<h2 class="quiz-question">{current["q"]}</h2><p class="quiz-hint">{current["hint"]}</p>')
        values = {}
        for key, kind, label in current["fields"]:
            widget = f"profile_{key}"
            if kind == "text":
                values[key] = st.text_input(label, draft.get(key) or "", key=widget)
            elif kind == "area":
                values[key] = st.text_area(label, draft.get(key) or "", key=widget, height=140)
            elif kind == "date":
                values[key] = st.date_input(label, value=draft.get(key), key=widget, format="MM/DD/YYYY")
            else:
                values[key] = st.number_input(label, 0, 120, min(int(draft.get(key) or 0), 120), key=widget)
        last = index == len(STEPS) - 1
        if st.button("Save profile" if last else "Continue", type="primary", width="stretch", key="profile_next"):
            if index == 0 and not values["name"].strip():
                st.warning("Enter a preferred name.")
            else:
                draft.update(values)
                if not last:
                    state.profile_step = index + 1
                    st.rerun()
                if (draft.get("hospital") or "").strip() != p.get("hospital", ""):
                    p.pop("facility_id", None)
                if (draft.get("doctor") or "").strip() != p.get("doctor", ""):
                    p.pop("npi", None)
                p.update(name=draft["name"].strip(), age=draft["age"], height_in=draft["height_in"], surgery=(draft["surgery"] or "").strip(),
                         surgery_date=draft["surgery_date"].isoformat() if draft.get("surgery_date") else "",
                         last_appointment=draft["last_appointment"].isoformat() if draft.get("last_appointment") else "",
                         hospital=(draft["hospital"] or "").strip(), doctor=(draft["doctor"] or "").strip(),
                         caregiver=(draft["caregiver"] or "").strip(), reported_meds=(draft["reported_meds"] or "").strip(),
                         preference=(draft["preference"] or "").strip())
                data.save_patient(p)
                state.pop("profile_draft", None)
                state.profile_step = 0
                st.success("Profile saved. Reco now uses these details in its answers.")
    if 0 < index < len(STEPS) - 1:
        st.button("Skip this question", key="profile_skip", on_click=lambda: state.update(profile_step=index + 1))

st.page_link("pages/2_Upload_papers.py", label="Add discharge instructions →")
st.page_link("pages/directory.py", label="Find my hospital or clinician →")
