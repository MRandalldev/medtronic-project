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
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
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
    return (now_local().date() - d).days


def add_checkin(answers: dict, level: str, reasons: list) -> None:
    p = get_patient()
    p.setdefault("checkins", []).append(
        {"date": now_local().date().isoformat(), "answers": answers, "level": level, "reasons": reasons}
    )
    if level in ("yellow", "red"):
        add_alert(level, reasons)
    save_patient(p)


def add_alert(level: str, reasons: list) -> None:
    p = get_patient()
    p.setdefault("alerts", []).append(
        {"time": now_local().strftime("%Y-%m-%d %H:%M"), "level": level, "reasons": reasons}
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
        {"from": sender, "text": text, "time": now_local().strftime("%Y-%m-%d %H:%M")}
    )
    save_patient(p)


def latest_vitals(patient: dict) -> dict:
    v = patient.get("vitals", [])
    if not v:
        return {}
    latest = dict(v[-1])

    def when(row):
        try:
            return datetime.fromisoformat(str(row.get("time", ""))).replace(tzinfo=None)
        except ValueError:
            return None

    t_last = when(latest)

    def weight_at_or_before(cutoff):
        for row in reversed(v):
            t = when(row)
            if t is not None and t <= cutoff and "weight_lb" in row:
                return row["weight_lb"]
        return None

    if "weight_lb" in latest and t_last is not None:
        w1 = weight_at_or_before(t_last - timedelta(hours=20))
        w7 = weight_at_or_before(t_last - timedelta(days=6))
        latest["weight_gain_24h_lb"] = round(latest["weight_lb"] - w1, 1) if w1 is not None else 0
        latest["weight_gain_7d_lb"] = round(latest["weight_lb"] - w7, 1) if w7 is not None else 0
    return latest



# ---------------------------------------------------------------- shared helpers (Jaiden)
LOCAL_TZ = ZoneInfo("America/New_York")  # demo patient's time zone; servers run on UTC


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def fill_profile(found: dict) -> list:
    """Fill only empty profile fields from the papers, so nothing the patient typed is overwritten."""
    p = get_patient()
    filled = []
    for key, value in found.items():
        if value and not p.get(key):
            p[key] = value
            filled.append(key)
    if filled:
        save_patient(p)
    return filled


def next_dose(patient: dict):
    """(time, medicine name) of the next timed dose today, or None."""
    now = now_local().strftime("%H:%M")
    upcoming = sorted((t, m["name"]) for m in patient.get("plan", {}).get("medications", [])
                      for t in m.get("times", []) if len(t) == 5 and t[2] == ":" and t >= now)
    return upcoming[0] if upcoming else None


def care_phone(patient: dict) -> str:
    return patient.get("care_phone") or patient.get("plan", {}).get("care_phone", "")


def settings(patient: dict) -> dict:
    return {"countdown": False, "caregiver_phone": "", **patient.get("settings", {})}
