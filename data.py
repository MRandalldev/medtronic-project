"""
data.py — the ONE place patient data lives. (Owner: Mekhai)

Every page reads and writes the patient through these functions only.
Data is kept in st.session_state for the demo (Streamlit Cloud does not keep
files between restarts), seeded from data/sample_patient.json.

Patient shape (keep these keys; pages depend on them):
{
  "name", "age", "height_in", "surgery", "surgery_date" (YYYY-MM-DD),
  "doctor", "last_appointment", "caregiver",
  "plan": {
      "medications": [{"name", "dose", "times": ["08:00", ...], "refill_date"}],
      "warning_signs": [str, ...],
      "follow_ups": [{"date", "with", "purpose"}]
  },
  "documents": [{"name", "text"}],
  "checkins":  [{"date", "answers": {question_id: answer}, "level", "reasons": [...]}],
  "vitals":    [{"time", "heart_rate", "spo2", "weight_lb"}],
  "med_log":   {"YYYY-MM-DD": {"<med name> <time>": true/false}},
  "messages":  [{"from", "text", "time"}],
  "alerts":    [{"time", "level", "reasons": [...]}]
}
"""
import hashlib
from storage import open_database
from contextlib import closing
import copy
import json
from datetime import date, datetime
from pathlib import Path

import streamlit as st

SAMPLE_PATH = Path(__file__).parent / "data" / "sample_patient.json"


def load_sample() -> dict:
    with open(SAMPLE_PATH) as f:
        return json.load(f)


def get_patient() -> dict:
    """Return the current patient. Loads the sample patient on first use."""
    if "patient" not in st.session_state:
        st.session_state["patient"] = load_sample()
    return st.session_state["patient"]


PROFILE_DB = Path(__file__).parent / ".local" / "accounts.sqlite"


def account_db():
    path = PROFILE_DB
    conn = open_database(path)
    conn.execute("CREATE TABLE IF NOT EXISTS profiles (owner TEXT PRIMARY KEY, body TEXT, revision INTEGER)")
    conn.commit()
    return conn


def bind_account(issuer, subject):
    owner = hashlib.sha256(json.dumps([issuer, subject]).encode()).hexdigest()
    if st.session_state.get("owner") == owner:
        return
    st.session_state.clear()
    if issuer == "local-email":
        st.session_state.local_identity = subject
    with closing(account_db()) as conn:
        row = conn.execute("SELECT body, revision FROM profiles WHERE owner=?", (owner,)).fetchone()
    p = dict(name="", age=None, height_in=None, surgery="", surgery_date="", doctor="",
             last_appointment="", caregiver="", vitals=[], documents=[], checkins=[], messages=[],
             alerts=[], med_log={}, plan={"medications": [], "follow_ups": [], "warning_signs": []})
    st.session_state.update(owner=owner, patient=json.loads(row[0]) if row else p,
                            revision=row[1] if row else 0)


def save_patient(patient: dict) -> None:
    owner = st.session_state.get("owner")
    if owner:
        rev = st.session_state.revision
        with closing(account_db()) as conn, conn:
            cur = conn.execute("INSERT INTO profiles VALUES (?,?,1) ON CONFLICT(owner) DO UPDATE SET body=excluded.body, revision=profiles.revision+1 WHERE profiles.revision=?",
                               (owner, json.dumps(patient), rev))
            if not cur.rowcount:
                st.session_state.pop("owner")
                st.rerun()
        st.session_state.revision += 1
    st.session_state["patient"] = patient


def reset_to_sample() -> None:
    """Judge mode: start fresh from the sample patient."""
    st.session_state["patient"] = copy.deepcopy(load_sample())


def days_since_surgery(patient: dict) -> int | None:
    if not patient.get("surgery_date"):
        return None
    try:
        d = date.fromisoformat(patient["surgery_date"])
    except ValueError:
        return None
    return (date.today() - d).days


def add_checkin(answers: dict, level: str, reasons: list) -> None:
    p = get_patient()
    p.setdefault("checkins", []).append(
        {"date": date.today().isoformat(), "answers": answers, "level": level, "reasons": reasons}
    )
    if level in ("yellow", "red"):
        add_alert(level, reasons)
    save_patient(p)


def add_alert(level: str, reasons: list) -> None:
    p = get_patient()
    p.setdefault("alerts", []).append(
        {"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "level": level, "reasons": reasons}
    )
    save_patient(p)


def add_document(name: str, text: str) -> None:
    p = get_patient()
    p.setdefault("documents", []).append({"name": name, "text": text})
    save_patient(p)


def set_plan(plan: dict) -> None:
    p = get_patient()
    p["plan"] = plan
    save_patient(p)


def log_dose(day: str, key: str, taken: bool) -> None:
    p = get_patient()
    p.setdefault("med_log", {}).setdefault(day, {})[key] = taken
    save_patient(p)


def add_message(sender: str, text: str) -> None:
    p = get_patient()
    p.setdefault("messages", []).append(
        {"from": sender, "text": text, "time": datetime.now().strftime("%Y-%m-%d %H:%M")}
    )
    save_patient(p)


def latest_vitals(patient: dict) -> dict:
    v = patient.get("vitals", [])
    return v[-1] if v else {}
