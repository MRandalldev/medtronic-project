"""
plan_reader.py — turns discharge-paper text into a recovery plan without AI.

Used as the fallback when no API key is set or the AI reply can't be parsed,
so "paper to plan" always works in a demo. It reads common discharge layouts:
numbered medication lines, "CALL 911" / "CALL YOUR CARE TEAM" bullet lists,
and dated follow-up lines.
"""
import re
from datetime import datetime

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"({MONTHS})\s+(\d{{1,2}}),\s*(\d{{4}})", re.I)
CLOCK_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)", re.I)


def _iso(match) -> str:
    try:
        return datetime.strptime(" ".join(match.groups()), "%B %d %Y").date().isoformat()
    except ValueError:
        return ""


def _times(text: str) -> list:
    low = text.lower()
    clocks = []
    for h, m, ampm in CLOCK_RE.findall(text):
        h = int(h) % 12 + (12 if ampm.upper() == "PM" else 0)
        clocks.append(f"{h:02d}:{m}")
    if clocks:
        return sorted(set(clocks))
    if "as needed" in low:
        return ["as needed"]
    if "twice a day" in low or "two times a day" in low:
        return ["08:00", "20:00"]
    if "bedtime" in low or "every night" in low or "evening" in low:
        return ["21:00"]
    if "morning" in low or "once a day" in low or "daily" in low:
        return ["08:00"]
    return ["as needed"]


def _section(lines, start_pattern):
    """Return the bullet lines under the first heading matching start_pattern."""
    out, inside = [], False
    for line in lines:
        s = line.strip()
        if re.search(start_pattern, s, re.I):
            inside = True
            continue
        if inside:
            if s.startswith("***"):
                break
            if s.startswith(("-", "•", "*")):
                out.append(s.lstrip("-•* ").strip())
            elif s and s.isupper():
                break
    return out


def read(text: str) -> dict:
    lines = text.splitlines()
    meds = []
    for line in lines:
        m = re.match(r"\s*\d+\.\s*([A-Za-z][A-Za-z\- ]+?\s+\d+(?:\.\d+)?\s*(?:mg|mcg|g|units?))\s*[-–:]\s*(.+)", line, re.I)
        if m:
            name, rest = m.group(1).strip(), m.group(2).strip()
            refill = DATE_RE.search(rest.split("Refill", 1)[1]) if "Refill" in rest else None
            dose = re.split(r"\.\s*Refill", rest)[0].strip().rstrip(".")
            dose = re.sub(r"^take\s+", "", dose, flags=re.I)
            dose = dose[:1].upper() + dose[1:]
            meds.append({"name": name, "dose": dose, "times": _times(rest),
                         "refill_date": _iso(refill) if refill else ""})

    warnings = [f"Call 911: {w}" for w in _section(lines, r"CALL 911")]
    warnings += [f"Call your care team: {w}" for w in _section(lines, r"CALL YOUR (CARE TEAM|DOCTOR)")]

    follow_ups = []
    for item in _section(lines, r"FOLLOW.?UP"):
        d = DATE_RE.search(item)
        rest = item[d.end():] if d else item
        rest = re.sub(r"^\s*(at\s+\d{1,2}:\d{2}\s*(AM|PM))?\s*[:\-–]\s*", "", rest, flags=re.I)
        who, _, why = rest.partition(" - ") if " - " in rest else rest.partition(": ")
        follow_ups.append({"date": _iso(d) if d else "", "with": who.strip() or rest.strip(),
                           "purpose": why.strip()})
    return validate({"medications": meds, "warning_signs": warnings, "follow_ups": follow_ups})


def validate(plan: dict) -> dict:
    """Coerce any plan (AI or reader) into the exact shape the screens expect."""
    meds = []
    for m in plan.get("medications", []) or []:
        if isinstance(m, dict) and m.get("name"):
            times = m.get("times") or ["as needed"]
            if isinstance(times, str):  # an AI may return "08:00" instead of ["08:00"]
                times = [t.strip() for t in times.split(",") if t.strip()]
            meds.append({"name": str(m["name"]), "dose": str(m.get("dose", "")),
                         "times": [str(t) for t in times], "refill_date": str(m.get("refill_date") or "")})
    warns = [str(w) for w in plan.get("warning_signs", []) or [] if w]
    fus = [{"date": str(f.get("date", "")), "with": str(f.get("with", "")), "purpose": str(f.get("purpose", ""))}
           for f in plan.get("follow_ups", []) or [] if isinstance(f, dict)]
    return {"medications": meds, "warning_signs": warns, "follow_ups": fus}
