import streamlit as st

import backend
import data
import ui

PULSE_SOURCE = "https://medlineplus.gov/ency/patientinstructions/000102.htm"

ui.demo_badge()
p = data.get_patient()
day = data.days_since_surgery(p)
import quiz

ui.page_header("Daily check-in", f"Day {day} after surgery. About a minute." if day is not None else "How are you feeling today?")

today = data.now_local().date().isoformat()
result = st.session_state.get("last_result") if st.session_state.get("last_result_date") == today else None

# The result goes first, so a frightened patient sees the next step without scrolling.
state = st.session_state
if result and not state.get("ci_again"):
    ui.alert_banner(result["level"], result["reasons"])
    question = st.session_state.get("mismatch")
    if question:
        with st.container(border=True, key="mismatch_box"):
            st.markdown("**One more question**")
            st.write(question)
            answered = st.session_state.get("mismatch_answer")
            if answered is None:
                yes, no = st.columns(2)
                if yes.button("Yes, I feel worse than I said", width="stretch", key="mismatch_yes"):
                    data.add_alert("yellow", [{"message": "Said they feel worse than reported after their readings changed: "
                                                          "call your care team today.", "source": PULSE_SOURCE}])
                    st.session_state["mismatch_answer"] = "yes"
                    st.rerun()
                if no.button("No, I really feel fine", width="stretch", key="mismatch_no"):
                    st.session_state["mismatch_answer"] = "no"
                    st.rerun()
            elif answered == "yes":
                st.success("Thanks for being honest. Your care team now sees that you feel worse, along with your reading.")
            else:
                st.info("Thanks. Your care team still sees the reading, so they can decide whether to check in.")
    ui.checkin_recap(p)
    if st.button("Check in again", key="ci_again_btn"):
        state.update(ci_again=True, ci_step=0, ci_draft=None)
        st.rerun()
    st.stop()

questions = backend.checkin_questions(p, day)
EMERGENCY = ["chest_pain", "breathless_at_rest", "dizzy_or_fainting", "stroke_signs", "heart_racing", "heavy_sweating"]
text = {q["id"]: q["text"] for q in questions}
warning_items = [(i, text[i]) for i in EMERGENCY]
other_items = [(q["id"], q["text"]) for q in questions if q["options"] == ["No", "Yes"] and q["id"] not in EMERGENCY]
WALK = {"I didn't walk": 0, "Under 10 minutes": 5, "10 to 20 minutes": 15, "20 to 30 minutes": 25, "More than 30 minutes": 35}

# Questions tailored to the medicines the patient told us about or that their papers list. They are recorded for the
# care team and shown at the next visit; no rule scores them, because we have no sourced threshold for them.
meds = " ".join([m.get("name", "") for m in p.get("plan", {}).get("medications", [])] + [p.get("reported_meds", "")]).lower()
TAILORED = [("t_bleeding", ("aspirin", "clopidogrel", "plavix", "ticagrelor", "brilinta", "apixaban", "eliquis", "warfarin", "rivaroxaban"),
             "Any unusual bleeding or bruising? (You take a medicine that thins your blood.)"),
            ("t_lightheaded", ("metoprolol", "carvedilol", "lisinopril", "losartan"),
             "Light-headed when you stand up? (Your heart or blood-pressure medicine can cause this.)"),
            ("t_constipated", ("oxycodone",), "Constipated today? (Pain medicine can cause this.)"),
            ("t_swollen_ankles", ("amlodipine",), "Swollen ankles today?")]
tailored = [(key, question) for key, words, question in TAILORED if any(w in meds for w in words)]

draft = state.get("ci_draft") or {"warn": None, "other": None, "other_text": "", "leg": None, "overall": None, "pain": None,
                                  "walk": None, "tailored": None, "numbers": {}}
state.ci_draft = draft
STEPS = ["warn", "other", "leg", "overall", "pain", "walk"] + (["tailored"] if tailored else []) + ["numbers"]
index = min(state.get("ci_step", 0), len(STEPS) - 1)
step = STEPS[index]

with st.container(key="quiz"), st.container(key="profile_quiz"):
    if quiz.header("DAILY CHECK-IN", index, len(STEPS), "ci_back"):
        state.ci_step = index - 1
        st.rerun()
    with st.container(key=f"q_ci_{index}"):
        value, problem = None, ""
        if step == "warn":
            quiz.question("Do you have any of these right now?", "Tap every one that applies, or None of these.")
            value = quiz.ticks(warning_items, draft["warn"], "ci_warn")
            problem = "" if value is not None else "Tap the ones that apply, or None of these."
        elif step == "other":
            quiz.question("Anything else today?", "Tap every one that applies, or None of these.")
            value = quiz.ticks(other_items, draft["other"], "ci_other")
            other = st.text_input("Something else? Describe it (optional)", draft["other_text"], key="ci_other_text")
            if value is None and other.strip():
                value = set()
            draft["other_text"] = other.strip()
            problem = "" if value is not None else "Tap the ones that apply, or None of these."
        elif step == "leg":
            quiz.question(text["leg_swelling"])
            value = st.radio("Leg swelling", ["Better", "Same", "Worse", "I have no swelling"], key="q_leg_swelling",
                             index=None if draft["leg"] is None else ["Better", "Same", "Worse", "I have no swelling"].index(draft["leg"]),
                             label_visibility="collapsed")
            problem = "" if value else "Pick one."
        elif step == "overall":
            quiz.question("Overall, compared to yesterday, I feel:")
            value = st.radio("Overall", ["Better", "Same", "Worse", "Not sure"], key="q_overall", label_visibility="collapsed",
                             index=None if draft["overall"] is None else ["Better", "Same", "Worse", "Not sure"].index(draft["overall"]))
            problem = "" if value else "Pick one."
        elif step == "pain":
            quiz.question("How much pain do you have right now?", "0 means no pain at all, 10 the worst you can imagine.")
            value = st.pills("Pain right now (0 = none, 10 = worst you can imagine)", list(range(11)), default=draft["pain"],
                             key="n_pain", label_visibility="collapsed")
            problem = "" if value is not None else "Tap a number. Tap 0 if you have no pain."
        elif step == "walk":
            quiz.question("How much did you walk today?", "Walking a little more each day is part of recovery.")
            labels = list(WALK) + [quiz.OTHER]
            current = next((k for k, v in WALK.items() if v == draft["walk"]), quiz.OTHER if draft["walk"] is not None else None)
            picked = st.radio("Walking", labels, index=labels.index(current) if current else None, key="n_walk_pick", label_visibility="collapsed")
            if picked == quiz.OTHER:
                value = st.number_input("Minutes you walked today", 0, 600, draft["walk"] or 0, step=5, key="n_walk")
            else:
                value = WALK.get(picked)
            problem = "" if picked else "Pick one."
        elif step == "tailored":
            quiz.question("A few questions about your medicines", "Tap any that apply, or None of these.")
            value = quiz.ticks(tailored, draft["tailored"], "ci_tail")
            problem = "" if value is not None else "Tap the ones that apply, or None of these."
        else:
            quiz.question("Your numbers (optional)", "Fill in what you measured today. Leave a box empty if you didn't measure it.")
            a, b = st.columns(2)
            pulse = a.number_input("Resting pulse (beats per minute)", 30, 220, None, step=1, key="n_pulse")
            temp = b.number_input("Temperature (°F)", 93.0, 108.0, None, step=0.1, format="%.1f", key="n_temp")
            c, d, e = st.columns(3)
            weight = c.number_input("Weight (lb)", 60.0, 600.0, None, step=0.1, format="%.1f", key="n_weight")
            bp_sys = d.number_input("Blood pressure: top number", 60, 260, None, step=1, key="n_bp_sys")
            bp_dia = e.number_input("Blood pressure: bottom number", 30, 160, None, step=1, key="n_bp_dia")
            value = {"heart_rate": pulse, "temp_f": temp, "weight_lb": weight, "bp_sys": bp_sys, "bp_dia": bp_dia}
            problem = "Enter both blood pressure numbers, or leave both empty." if (bp_sys is None) != (bp_dia is None) else ""

        last = index == len(STEPS) - 1
        if st.button("Submit check-in" if last else "Continue", type="primary", width="stretch", key="ci_next"):
            if problem:
                st.warning(problem)
            else:
                draft[step] = value
                if not last:
                    state.ci_step = index + 1
                    st.rerun()
                ticked = (draft["warn"] or set()) | (draft["other"] or set())
                answers = {q["id"]: ("Yes" if q["id"] in ticked else "No") for q in questions if q["options"] == ["No", "Yes"]}
                answers["leg_swelling"] = "Same" if draft["leg"] == "I have no swelling" else draft["leg"]
                answers["overall"] = draft["overall"]
                for key, _ in tailored:
                    answers[key] = "Yes" if key in (draft["tailored"] or set()) else "No"
                if draft["other_text"]:
                    answers["other_symptom"] = draft["other_text"]
                numbers = {"pain": draft["pain"], "walk_min": draft["walk"], **{k: v for k, v in draft["numbers"].items() if v is not None}}
                numbers = {k: v for k, v in numbers.items() if v is not None}
                data.record_numbers(numbers)  # typed numbers become a reading, so the same sourced rules score them
                vitals = data.latest_vitals(p)
                scored = backend.score_checkin({k: v for k, v in answers.items() if k in text}, vitals)
                data.add_checkin(answers, scored["level"], scored["reasons"], numbers)
                state.update(last_result=scored, last_result_date=today, ci_again=False, ci_step=0, ci_draft=None,
                             mismatch=backend.check_mismatch(answers, vitals), mismatch_answer=None)
                st.rerun()
