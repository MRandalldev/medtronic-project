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
  "messages":  [{"from": "Patient" | "Care team", "text", "time", "read"}],
  "alerts":    [{"time", "level", "reasons": [...], "ack": {"by", "time"}}],
  "prn_log":   [{"time", "name", "count"}],            as-needed medicine taken
  "visit_questions": [str], "refilled": {"<med name>": "<refill date marked done>"}
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


def add_checkin(answers: dict, level: str, reasons: list, numbers: dict | None = None) -> None:
    p = get_patient()
    p.setdefault("checkins", []).append(
        {"date": now_local().date().isoformat(), "answers": answers, "level": level, "reasons": reasons,
         "numbers": numbers or {}}
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
    """sender is "Patient" or "Care team". A message is unread until the other side opens the thread."""
    p = get_patient()
    p.setdefault("messages", []).append(
        {"from": sender, "text": text, "time": now_local().strftime("%Y-%m-%d %H:%M"), "read": False}
    )
    save_patient(p)


def latest_vitals(patient: dict) -> dict:
    """The newest value of each measurement from the 24 hours before the newest reading.
    (A watch row has a pulse but no temperature; a check-in row may have only a temperature.)"""
    v = patient.get("vitals", [])
    if not v:
        return {}

    def when(row):
        try:
            return datetime.fromisoformat(str(row.get("time", ""))).replace(tzinfo=None)
        except ValueError:
            return None

    t_last = when(v[-1])
    latest = {}
    for row in v:
        t = when(row)
        if row is v[-1] or (t is not None and t_last is not None and t_last - timedelta(hours=24) < t <= t_last):
            latest.update(row)
    latest["time"] = v[-1].get("time", "")

    def weight_at_or_before(cutoff):
        for row in reversed(v):
            t = when(row)
            if t is not None and t <= cutoff and "weight_lb" in row:
                return row["weight_lb"]
        return None

    t_weight = next((when(r) for r in reversed(v) if "weight_lb" in r and when(r) is not None), None)
    if "weight_lb" in latest and t_weight is not None:
        w1 = weight_at_or_before(t_weight - timedelta(hours=20))
        w7 = weight_at_or_before(t_weight - timedelta(days=6))
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
    return {"countdown": False, "caregiver_phone": "", "checkin_time": "09:00", **patient.get("settings", {})}


def human_date(iso: str, relative: bool = True) -> str:
    """'2026-11-19' -> 'Thu, Nov 19 · in 5 days'. Unknown or empty dates come back as given."""
    try:
        day = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or "Date to be set"
    text = day.strftime("%a, %b ") + str(day.day)
    if relative:
        delta = (day - now_local().date()).days
        text += {0: " · today", 1: " · tomorrow", -1: " · yesterday"}.get(delta,
                 f" · in {delta} days" if delta > 0 else f" · {-delta} days ago")
    return text


# ---------------------------------------------------------------- recovery helpers (Jaiden)
# Everything below is computed from the patient's own record. No AI, no invented thresholds.
VITAL_KEYS = ("heart_rate", "temp_f", "weight_lb", "bp_sys", "bp_dia")


def record_numbers(numbers: dict) -> None:
    """Save numbers typed into the check-in as a reading, so the same sourced rules apply to them."""
    row = {k: numbers[k] for k in VITAL_KEYS if numbers.get(k) is not None}
    if row:
        p = get_patient()
        p.setdefault("vitals", []).append({"time": now_local().strftime("%Y-%m-%d %H:%M"), **row, "source": "check-in"})
        save_patient(p)


def scheduled_doses(patient: dict) -> list:
    """[(medicine name, "HH:MM")] for doses with a clock time ("as needed" medicines are not scheduled)."""
    return [(m["name"], t) for m in patient.get("plan", {}).get("medications", []) for t in m.get("times", [])
            if len(t) == 5 and t[2] == ":"]


def adherence(patient: dict, days: int = 7) -> dict:
    """Doses taken vs due over the last `days` days, counted from the first day the patient logged a dose.
    Today counts only doses whose time has passed. Returns {"taken", "due", "missed": [(day, name, time)], "since"}."""
    log = patient.get("med_log", {})
    doses = scheduled_doses(patient)
    now = now_local()
    today = now.date()
    logged_days = sorted(d for d, marks in log.items() if any(marks.values()))
    if not doses or not logged_days:
        return {"taken": 0, "due": 0, "missed": [], "since": None}
    start = max(date.fromisoformat(logged_days[0]), today - timedelta(days=days - 1))
    taken, due, missed = 0, 0, []
    day = start
    while day <= today:
        for name, clock in doses:
            if day == today and clock > now.strftime("%H:%M"):
                continue
            due += 1
            if log.get(day.isoformat(), {}).get(f"{name} {clock}"):
                taken += 1
            else:
                missed.append((day.isoformat(), name, clock))
        day += timedelta(days=1)
    return {"taken": taken, "due": due, "missed": missed, "since": start.isoformat()}


def overdue_doses(patient: dict, grace_minutes: int = 60) -> list:
    """Today's doses that are more than an hour late and not marked taken: [(name, time)]."""
    now = now_local()
    cutoff = (now - timedelta(minutes=grace_minutes)).strftime("%H:%M")
    logged = patient.get("med_log", {}).get(now.date().isoformat(), {})
    if now.hour * 60 + now.minute < grace_minutes:
        return []
    return [(n, t) for n, t in scheduled_doses(patient) if t <= cutoff and not logged.get(f"{n} {t}")]


def prn_meds(patient: dict) -> list:
    """As-needed medicines with the limits written in the patient's own papers."""
    import re
    found = []
    for m in patient.get("plan", {}).get("medications", []):
        if any(len(t) == 5 and t[2] == ":" for t in m.get("times", [])):
            continue
        dose = m.get("dose", "")
        limit = re.search(r"(?:more than|max(?:imum)?(?: of)?|up to)\s+(\d+)\s+\w+\s+(?:in|per|every|a)\s+(?:24 hours|day)", dose, re.I)
        gap = re.search(r"every\s+(\d+)(?:\s*(?:to|-)\s*\d+)?\s+hours", dose, re.I)
        found.append({"name": m["name"], "dose": dose, "max_24h": int(limit.group(1)) if limit else None,
                      "gap_hours": int(gap.group(1)) if gap else None})
    return found


def prn_status(patient: dict, med: dict) -> dict:
    """How much of an as-needed medicine was taken in the last 24 hours, and when the next dose is allowed."""
    now = now_local()
    rows = []
    for row in patient.get("prn_log", []):
        try:
            t = datetime.fromisoformat(row["time"])
        except (KeyError, ValueError):
            continue
        if row.get("name") == med["name"] and now - t < timedelta(hours=24):
            rows.append((t, int(row.get("count", 1))))
    taken = sum(c for _, c in rows)
    last = max((t for t, _ in rows), default=None)
    next_ok = last + timedelta(hours=med["gap_hours"]) if last and med.get("gap_hours") else None
    left = med["max_24h"] - taken if med.get("max_24h") is not None else None
    return {"taken_24h": taken, "left": left, "last": last, "next_ok": next_ok if next_ok and next_ok > now else None}


def log_prn(name: str, count: int) -> None:
    p = get_patient()
    p.setdefault("prn_log", []).append({"time": now_local().strftime("%Y-%m-%d %H:%M"), "name": name, "count": count})
    save_patient(p)


def refill_reminders(patient: dict, within: int = 14) -> list:
    """Refills due in the next `within` days (or overdue) that are not marked done: [{"name","date","days"}]."""
    today = now_local().date()
    done = patient.get("refilled", {})
    out = []
    for m in patient.get("plan", {}).get("medications", []):
        try:
            day = date.fromisoformat(m.get("refill_date", ""))
        except (TypeError, ValueError):
            continue
        if (day - today).days <= within and done.get(m["name"]) != m["refill_date"]:
            out.append({"name": m["name"], "date": m["refill_date"], "days": (day - today).days})
    return sorted(out, key=lambda r: r["days"])


def mark_refilled(name: str, refill_date: str) -> None:
    p = get_patient()
    p.setdefault("refilled", {})[name] = refill_date
    save_patient(p)


def checked_in_today(patient: dict) -> bool:
    today = now_local().date().isoformat()
    return any(c.get("date") == today for c in patient.get("checkins", []))


def unread(patient: dict, sender: str) -> int:
    """Messages from `sender` ("Care team" or "Patient") that the other side has not opened."""
    return sum(m.get("from") == sender and m.get("read") is False for m in patient.get("messages", []))


def mark_read(sender: str) -> None:
    p = get_patient()
    changed = False
    for m in p.get("messages", []):
        if m.get("from") == sender and m.get("read") is False:
            m["read"] = True
            changed = True
    if changed:
        save_patient(p)


def acknowledge_alert(index: int, by: str = "Care team") -> None:
    p = get_patient()
    alert = p["alerts"][index]
    if not alert.get("ack"):
        alert["ack"] = {"by": by, "time": now_local().strftime("%Y-%m-%d %H:%M")}
        save_patient(p)


def set_visit_status(index: int, status: str) -> None:
    """status: "confirmed" or "reschedule requested". The care team sees it and gets a message."""
    p = get_patient()
    visit = p["plan"]["follow_ups"][index]
    visit["status"] = status
    save_patient(p)
    when = human_date(visit.get("date", ""), relative=False)
    add_message("Patient", (f"I confirmed my visit with {visit['with']} on {when}." if status == "confirmed"
                            else f"I need to reschedule my visit with {visit['with']} on {when}. Please call me."))


def schedule_visit(index: int, day: str) -> None:
    """The care team sets or changes a visit date; the patient is told in Messages."""
    p = get_patient()
    visit = p["plan"]["follow_ups"][index]
    visit["date"], visit["status"] = day, None
    save_patient(p)
    add_message("Care team", f"Your visit with {visit['with']} is set for {human_date(day, relative=False)}. "
                             "Please confirm it on your Today page.")


def next_visit(patient: dict):
    """(index, visit) of the next dated visit from today on, or None."""
    today = now_local().date().isoformat()
    dated = [(i, f) for i, f in enumerate(patient.get("plan", {}).get("follow_ups", [])) if f.get("date", "") >= today and f.get("date")]
    return min(dated, key=lambda pair: pair[1]["date"]) if dated else None


def visit_questions(patient: dict) -> list:
    """Things worth raising at the next visit, built by rule from the record plus the patient's own notes."""
    out = []
    seen = set()
    for a in patient.get("alerts", []):
        for r in a.get("reasons", []):
            topic = r["message"].split(":")[0].strip()
            if topic not in seen:
                seen.add(topic)
                out.append(f"On {human_date(a.get('time', '')[:10], relative=False)} I reported: {topic[0].lower() + topic[1:]}. What should I watch for?")
    missed = adherence(patient)["missed"]
    if missed:
        names = sorted({name for _, name, _ in missed})
        out.append(f"I missed {len(missed)} dose{'s' if len(missed) != 1 else ''} this week ({', '.join(names)}). What should I do when I miss one?")
    pains = [c["numbers"]["pain"] for c in patient.get("checkins", []) if c.get("numbers", {}).get("pain") is not None]
    if pains and pains[-1] >= 1:
        out.append(f"My pain was {pains[-1]} out of 10 at my last check-in" + (f" (it was {pains[0]} at my first)" if len(pains) > 1 else "") + ". Is that expected?")
    for q in patient.get("assistant_history", []):
        if q.get("unsure") and q.get("question"):
            out.append("Reco could not answer: " + q["question"])
    return out + list(patient.get("visit_questions", []))


def milestones(patient: dict) -> list:
    """Recovery milestones read from the patient's record and papers: [{"date", "label", "done"}], dated ones first."""
    import re
    today = now_local().date()
    out = []

    def add(day, label, done=None):
        out.append({"date": day.isoformat() if day else "", "label": label, "done": (day <= today) if done is None and day else bool(done)})

    try:
        surgery = date.fromisoformat(patient.get("surgery_date", ""))
    except (TypeError, ValueError):
        surgery = None
    text = " ".join(d.get("text", "") for d in patient.get("documents", []))
    if surgery:
        add(surgery, "Surgery" + (f": {patient['surgery']}" if patient.get("surgery") else ""))
    home = re.search(r"Discharge date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if home:
        try:
            add(datetime.strptime(home.group(1), "%B %d, %Y").date(), "Went home from the hospital")
        except ValueError:
            pass
    checkins = patient.get("checkins", [])
    if checkins:
        try:
            add(date.fromisoformat(checkins[0]["date"]), "First daily check-in in Reco")
        except (KeyError, ValueError):
            pass
    else:
        add(None, "First daily check-in in Reco", done=False)
    for visit in patient.get("plan", {}).get("follow_ups", []):
        label = f"Visit: {visit.get('with', '')}" + (f" ({visit['purpose']})" if visit.get("purpose") and visit.get("date") else "")
        try:
            add(date.fromisoformat(visit.get("date", "")), label)
        except (TypeError, ValueError):
            add(None, f"{visit.get('with', 'Visit')}: date to be set", done=False)
    if surgery:
        for limit, weeks in dict.fromkeys(re.findall(r"(Do not [^.]*?) for (\d+) weeks", text)):
            add(surgery + timedelta(weeks=int(weeks)), f"{weeks} weeks since surgery. Until then: {limit[0].lower() + limit[1:]}. Ask your surgeon before changing this.")
    return sorted(out, key=lambda m: (m["date"] == "", m["date"]))


def daily_update(patient: dict) -> str:
    """A short plain-text update for the caregiver, built only from today's record."""
    today = now_local().date()
    first = (patient.get("name") or "Your family member").split(" ")[0]
    day = days_since_surgery(patient)
    parts = [f"{first}'s recovery update for {today.strftime('%a, %b ')}{today.day}" + (f" (day {day} after surgery)" if day is not None else "") + "."]
    todays = [c for c in patient.get("checkins", []) if c.get("date") == today.isoformat()]
    if todays:
        last = todays[-1]
        parts.append({"green": "Check-in: all clear.", "yellow": "Check-in: needs a call to the care team today.",
                      "red": "Check-in: emergency warning sign reported."}.get(last.get("level"), "Check-in done."))
        n = last.get("numbers", {})
        bits = ([f"pain {n['pain']}/10"] if n.get("pain") is not None else []) + ([f"walked {n['walk_min']} min"] if n.get("walk_min") else [])
        if bits:
            parts.append(("; ".join(bits) + ".").capitalize())
    else:
        parts.append("No check-in yet today.")
    doses = scheduled_doses(patient)
    if doses:
        logged = patient.get("med_log", {}).get(today.isoformat(), {})
        parts.append(f"Medicines: {sum(bool(logged.get(f'{n} {t}')) for n, t in doses)} of {len(doses)} doses marked taken.")
    nxt = next_visit(patient)
    if nxt:
        parts.append(f"Next visit: {human_date(nxt[1]['date'])} with {nxt[1]['with']}.")
    return " ".join(parts)


def next_action(patient: dict) -> dict:
    """The one thing to do now, in priority order: {"kind", "title", "body", "page", "link"}."""
    today = now_local().date().isoformat()
    open_alerts = [a for a in patient.get("alerts", []) if a.get("time", "").startswith(today)]
    level = "red" if any(a["level"] == "red" for a in open_alerts) else "yellow" if open_alerts else None
    if level:
        seen = all(a.get("ack") for a in open_alerts)
        return {"kind": level, "title": "Call 911 if you still have that symptom" if level == "red" else "Call your care team today",
                "body": ("Your care team has seen today's alert. " if seen else "Today's check-in or chat found a warning sign. ")
                        + "Open your check-in for the call buttons.",
                "page": "pages/3_Check_in.py", "link": "Open my check-in result"}
    late = overdue_doses(patient)
    if late:
        return {"kind": "dose", "title": f"Take your {late[0][0]}", "body": f"It was due at {clock_12(late[0][1])}"
                + (f", and {len(late) - 1} more dose{'s are' if len(late) > 2 else ' is'} waiting" if len(late) > 1 else "")
                + ". Mark it taken once you have.", "page": "pages/6_Calendar.py", "link": "Mark my doses"}
    if not checked_in_today(patient):
        return {"kind": "checkin", "title": "Do today's check-in", "body": "About a minute. It is how warning signs get caught early.",
                "page": "pages/3_Check_in.py", "link": "Start check-in"}
    dose = next_dose(patient)
    if dose:
        return {"kind": "dose", "title": f"Next: {dose[1]} at {clock_12(dose[0])}", "body": "Nothing else is due right now.",
                "page": "pages/6_Calendar.py", "link": "Open my schedule"}
    return {"kind": "done", "title": "You're done for today", "body": "Check-in complete and no more doses scheduled. Rest well.",
            "page": "pages/progress.py", "link": "See my progress"}


def human_time(stamp: str) -> str:
    """'2026-11-14 10:42' -> 'Sat, Nov 14 at 10:42 AM'."""
    try:
        t = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return stamp or ""
    return t.strftime("%a, %b ") + str(t.day) + " at " + t.strftime("%I:%M %p").lstrip("0")


def clock_12(hhmm: str) -> str:
    """'20:00' -> '8:00 PM'. Anything that is not a clock time comes back as given."""
    try:
        return datetime.strptime(hhmm, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except (TypeError, ValueError):
        return hhmm
