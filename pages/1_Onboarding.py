from datetime import date

import streamlit as st

import data
import hospital_index
import quiz

p = data.get_patient()
state = st.session_state

PROCEDURES = ["Coronary artery bypass surgery (CABG)", "Heart valve repair or replacement", "Bypass and valve surgery together",
              "Stent or angioplasty (PCI)", "Pacemaker or defibrillator implant", "Not sure"]
# Hospitals offered when the full CMS list is not available: real cardiac hospitals in North Carolina, plus the demo's.
STARTER_HOSPITALS = ["Greensboro Heart & Vascular Center (fictional)", "Cone Health Moses Cone Hospital · Greensboro",
                     "Duke University Hospital · Durham", "UNC Medical Center · Chapel Hill", "WakeMed Raleigh Campus · Raleigh",
                     "Atrium Health Wake Forest Baptist · Winston-Salem", "Novant Health Forsyth Medical Center · Winston-Salem",
                     "Atrium Health Carolinas Medical Center · Charlotte", "Novant Health Presbyterian Medical Center · Charlotte",
                     "ECU Health Medical Center · Greenville", "Cape Fear Valley Medical Center · Fayetteville"]
DOCTORS = ["Dr. Sample Surgeon (fictional, demo)", "My heart surgeon (I'll add the name later)", "My cardiologist",
           "My primary care doctor", "Not sure yet"]
MEDICINES = ["Aspirin 81 mg", "Clopidogrel (Plavix) 75 mg", "Ticagrelor (Brilinta) 90 mg", "Apixaban (Eliquis) 5 mg", "Warfarin",
             "Metoprolol 25 mg", "Carvedilol", "Atorvastatin 40 mg", "Rosuvastatin", "Lisinopril", "Losartan", "Furosemide (Lasix)",
             "Amiodarone", "Potassium chloride", "Pantoprazole", "Acetaminophen (Tylenol) 500 mg", "Oxycodone", "Docusate (stool softener)"]
FREQUENCIES = {"Once a day, morning": ["08:00"], "Once a day, evening": ["20:00"], "Twice a day": ["08:00", "20:00"],
               "Three times a day": ["08:00", "14:00", "20:00"], "Every night at bedtime": ["21:00"], "Only when needed": []}
RELATIONS = ["Spouse or partner", "Daughter", "Son", "Mother", "Father", "Sister", "Brother", "Cousin", "Grandchild", "Friend", "Neighbor"]
NO_CAREGIVER = "No one right now"


def saved_date(key):
    try:
        return date.fromisoformat(p.get(key, ""))
    except (TypeError, ValueError):
        return None


def hospital_options():
    index = hospital_index.load()
    if index is None:
        return STARTER_HOSPITALS
    rows = [f"{r[0]} · {r[1]}" for r in index.by_state.get(p.get("hospital_state") or "NC", [])]
    return [STARTER_HOSPITALS[0]] + sorted(rows) if rows else STARTER_HOSPITALS


def start_draft():
    name, _, rest = p.get("caregiver", "").partition("(")
    reported = p.get("reported_med_list") or [{"name": line.strip(), "frequency": ""}
                                               for line in p.get("reported_meds", "").splitlines() if line.strip()]
    if not reported:   # start from the medicines on their papers, with how often read from the times
        by_times = {tuple(v): k for k, v in FREQUENCIES.items()}
        reported = [{"name": m["name"], "frequency": by_times.get(tuple(t for t in m.get("times", []) if len(t) == 5), "")}
                    for m in p.get("plan", {}).get("medications", [])]
    return {"name": p.get("name", ""), "surgery": p.get("surgery", ""), "surgery_date": saved_date("surgery_date"),
            "hospital": p.get("hospital", ""), "last_appointment": saved_date("last_appointment"), "doctor": p.get("doctor", ""),
            "meds": reported, "caregiver_name": name.strip(), "relation": rest.rstrip(")").strip().capitalize() if rest else "",
            "age": p.get("age") or 0, "height_in": p.get("height_in") or 0, "preference": p.get("preference", "")}


def pick_or_type(label, options, current, key, none_label):
    """A searchable dropdown with Other (type it) and a 'none' choice."""
    listed = options + [quiz.OTHER, none_label]
    at = options.index(current) if current in options else (len(options) if current else None)
    picked = st.selectbox(label, listed, index=at, placeholder="Start typing to search", key=key)
    if picked == quiz.OTHER:
        return st.text_input(f"{label} (type it)", current if current not in options else "", key=key + "_other").strip()
    return "" if picked in (none_label, None) else picked


draft = state.setdefault("profile_draft", start_draft())
STEPS = ["name", "surgery", "hospital", "doctor", "meds", "frequency", "caregiver", "about", "remember"]
index = min(state.setdefault("profile_step", 0), len(STEPS) - 1)
step = STEPS[index]

with st.container(key="quiz"), st.container(key="profile_quiz"):
    if quiz.header("YOUR PROFILE", index, len(STEPS), "profile_back"):
        state.profile_step = index - 1
        st.rerun()
    with st.container(key=f"q_{index}"):
        values, problem = {}, ""
        if step == "name":
            quiz.question("What should we call you?", "This is how Reco and your dashboard greet you.")
            values["name"] = st.text_input("Preferred name", draft["name"], key="profile_name")
            problem = "" if values["name"].strip() else "Enter a preferred name."
        elif step == "surgery":
            quiz.question("What surgery did you have?", "Pick the closest one, or choose Other and type it the way your papers say.")
            values["surgery"] = quiz.choice("Procedure", PROCEDURES, draft["surgery"], "profile_surgery", "Procedure")
            values["surgery_date"] = st.date_input("Surgery date", value=draft["surgery_date"], key="profile_surgery_date", format="MM/DD/YYYY")
        elif step == "hospital":
            quiz.question("Where was your surgery?", "Your hospital helps Reco find the right care-team number.")
            values["hospital"] = pick_or_type("Hospital", hospital_options(), draft["hospital"], "profile_hospital", "Not sure")
            values["last_appointment"] = st.date_input("Last appointment (optional)", value=draft["last_appointment"],
                                                       key="profile_last_appt", format="MM/DD/YYYY")
        elif step == "doctor":
            quiz.question("Who is your doctor or care team?", "The surgeon or clinic you call with questions.")
            values["doctor"] = pick_or_type("Doctor or care team", DOCTORS, draft["doctor"], "profile_doctor", "None yet")
            st.page_link("pages/directory.py", label="Look up a clinician at your hospital →")
        elif step == "meds":
            quiz.question("Which medicines are you taking?", "Pick every one on your discharge list. You'll set how often next.")
            known = [m["name"] for m in draft["meds"]]
            chosen = st.multiselect("Medicines", MEDICINES + ["None"], default=[m for m in known if m in MEDICINES] or None,
                                    placeholder="Search medicines", key="profile_meds")
            extra = st.text_input("Other medicines (comma-separated)", ", ".join(m for m in known if m not in MEDICINES), key="profile_meds_other")
            names = [m for m in chosen if m != "None"] + [x.strip() for x in extra.split(",") if x.strip()]
            values["meds"] = [next((m for m in draft["meds"] if m["name"] == n), {"name": n, "frequency": ""}) for n in names]
            if not chosen and not extra.strip():
                problem = "Pick your medicines, or choose None."
        elif step == "frequency":
            quiz.question("How often do you take each one?", "From your discharge papers. Reco uses this for your reminders.")
            if not draft["meds"]:
                st.info("No medicines picked. Go back to add them, or continue.")
            values["meds"] = []
            for n, med in enumerate(draft["meds"]):
                st.markdown(f"**{med['name']}**")
                freq = quiz.choice(med["name"], list(FREQUENCIES), med.get("frequency") or None, f"profile_freq_{n}", "How often")
                values["meds"].append({"name": med["name"], "frequency": freq})
            if any(not m["frequency"] for m in values["meds"]):
                problem = "Choose how often for each medicine."
        elif step == "caregiver":
            quiz.question("Who is helping you at home?", "Optional. They can get a short daily update from you.")
            values["relation"] = quiz.choice("Relationship", RELATIONS + [NO_CAREGIVER], draft["relation"] or None,
                                             "profile_relation", "Relationship")
            values["caregiver_name"] = (st.text_input("Their name", draft["caregiver_name"], key="profile_caregiver_name")
                                        if values["relation"] and values["relation"] != NO_CAREGIVER else "")
        elif step == "about":
            quiz.question("A little about you", "Optional. Only used to read your numbers in context.")
            left, right = st.columns(2)
            values["age"] = left.number_input("Age", 0, 120, int(draft["age"] or 0), key="profile_age")
            values["height_in"] = right.number_input("Height in inches", 0, 110, int(draft["height_in"] or 0), key="profile_height")
        else:
            quiz.question("Anything Reco should remember?", "Optional. For example: “I'm hard of hearing, so text me instead of calling.”")
            values["preference"] = st.text_input("Something you want the assistant to remember", draft["preference"], key="profile_preference")

        last = index == len(STEPS) - 1
        if st.button("Save and go to Today" if last else "Continue", type="primary", width="stretch", key="profile_next"):
            if problem:
                st.warning(problem)
            else:
                draft.update(values)
                if not last:
                    state.profile_step = index + 1
                    st.rerun()
                meds = draft["meds"]
                caregiver = draft["caregiver_name"].strip()
                relation = draft["relation"] if draft["relation"] != NO_CAREGIVER else ""
                if draft["hospital"] != p.get("hospital", ""):
                    p.pop("facility_id", None)
                if draft["doctor"] != p.get("doctor", ""):
                    p.pop("npi", None)
                p.update(name=draft["name"].strip(), age=draft["age"], height_in=draft["height_in"], surgery=draft["surgery"],
                         surgery_date=draft["surgery_date"].isoformat() if draft.get("surgery_date") else "",
                         last_appointment=draft["last_appointment"].isoformat() if draft.get("last_appointment") else "",
                         hospital=draft["hospital"], doctor=draft["doctor"],
                         caregiver=f"{caregiver} ({relation.lower()})" if caregiver and relation else caregiver,
                         reported_med_list=meds, reported_meds="\n".join(f"{m['name']} · {m['frequency']}" for m in meds),
                         preference=draft["preference"].strip())
                # A new account has no plan from papers yet: the medicines and times they told us become their schedule,
                # marked self-reported, so reminders work from day one. Papers uploaded later replace it.
                plan = p.setdefault("plan", {"medications": [], "follow_ups": [], "warning_signs": []})
                if not plan.get("medications") or all(m.get("source") == "self-reported" for m in plan["medications"]):
                    plan["medications"] = [{"name": m["name"],
                                            "dose": (f"{m['frequency']} (you told us; check your papers)" if FREQUENCIES.get(m["frequency"])
                                                     else "as needed (you told us; check your papers for the limit)"),
                                            "times": FREQUENCIES.get(m["frequency"], []), "refill_date": "", "source": "self-reported"}
                                           for m in meds]
                data.save_patient(p)
                state.pop("profile_draft", None)
                state.profile_step = 0
                state.profile_saved_toast = True
                st.switch_page("pages/4_Dashboard.py")
    if step in ("surgery", "hospital", "doctor", "caregiver", "about"):
        st.button("Skip this question", key="profile_skip", on_click=lambda: state.update(profile_step=index + 1))
