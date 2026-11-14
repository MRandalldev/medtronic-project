"""
chat_rules.py: a symptom typed into Reco goes through the same sourced rules as the
daily check-in (sources/thresholds.csv). The rules decide; the AI never does.
(Owner: Jaiden)
"""
import csv
import re
from pathlib import Path

RULES = list(csv.DictReader(open(Path(__file__).parent / "sources/thresholds.csv", encoding="utf-8-sig")))
RANK = {"red": 2, "yellow": 1}

# Check-in question id -> phrases a patient might type for it.
PHRASES = {
    "chest_pain": r"chest (?:feels |is )?(?:tight|heavy|pressure|squeez)\w*|angina",
    "breathless_at_rest": r"(?:short|out) of breath|breathless|(?:hard|trouble|difficult) (?:to )?breath\w*|can'?t catch my breath",
    "dizzy_or_fainting": r"dizz\w*|faint(?:ed|ing)?|passed out|black(?:ed)? out|light ?-?headed",
    "stroke_signs": r"(?:face|arm|leg|side)\w* (?:is |are |feels? )?(?:numb|weak|droop)\w*|slurred speech|(?:trouble|can'?t) (?:speak|talk)\w*|(?:sudden|worst|severe) headache",
    "heart_racing": r"heart (?:is |keeps )?(?:racing|pounding|fluttering|skipping|beating (?:really |very )?(?:fast|slow))|palpitation\w*|irregular heart ?beat|skipp(?:ed|ing) beats?",
    "heavy_sweating": r"sweat(?:ing)? (?:a lot|heavily|so much)|heavy sweating|drenched in sweat|cold sweats?|night sweats?",
    "incision_signs": r"(?:incision|wound|scar|stitches|cut)\w* (?:is |are |looks? |seems? )?(?:\w+ )?(?:red|swollen|warm|hot|draining|oozing|leaking|bleeding|open(?:ing)?|pus\w*)|(?:pus|oozing|drainage) (?:from|at|on) (?:my )?(?:incision|wound)",
    "leg_swelling": r"(?:leg|ankle|feet|foot|calf)s? (?:is |are |look |looks |feel |feels )?(?:more )?(?:swollen|puffy)|swelling in my (?:legs?|ankles?|feet|foot)|swollen (?:legs?|ankles?|feet|foot)",
    "cough": r"cough\w* (?:up )?(?:\w+ )?(?:blood|mucus|phlegm|green|yellow)|(?:can'?t|won'?t|doesn'?t|keep|keeps) (?:stop )?cough\w*|cough\w* (?:won'?t|that won'?t|for (?:days|a week|\d+ days)|all (?:day|night)|keeps)",
    "chills": r"\bchills\b|shivering",
    "breath_chest_pain": r"(?:hurts|pain|painful) (?:when|to) (?:i )?(?:take a )?(?:deep )?breath\w*",
    "breastbone_clicking": r"(?:breastbone|sternum)\w* (?:is |keeps )?(?:click|pop|mov|shift|crack)\w*|click\w* in my chest",
    "trouble_with_meds": r"(?:ran|run|running) out of\b|(?:can'?t|cannot|unable to) (?:take|swallow|afford|get)\b|(?:missed|forgot|skipped) (?:to take )?(?:my |a |the )?(?:\w+ )?(?:dose|pill|med\w*|tablet)s?",
}
NEGATION = r"\b(?:no|not|never|without|denies|isn't|aren't|wasn't|haven't|hasn't|don't|doesn't|didn't)\b(?:\s+\w+){0,4}\s*$"
NOT_ME = r"\b(?:what if|what (?:is|are|causes)|is it normal|if i|used to|last year|my (?:mother|father|mom|dad|friend|wife|husband|son|daughter)|(?:he|she|they) (?:is|was|has|had))\b"


def clean(text):
    return (text.casefold().replace("’", "'").replace("‘", "'")
            .replace("â\u0080\u0099", "'"))


def _found(pattern, text):
    for clause in re.split(r"[.;!?]|\b(?:but|however|and)\b", text):
        for m in re.finditer(pattern, clause):
            inside = re.search(r"\b(?:no|not|never|isn't|aren't|doesn't|don't)\b", m.group(0))
            if not inside and not re.search(NEGATION, clause[:m.start()]):
                return True
    return False


def _vital_values(text):
    """Numbers a patient states: temperature, weight gain, pulse."""
    vitals = {}
    temps = [float(t) for t in re.findall(r"(?:fever|temp\w*)\D{0,12}?(\d{2,3}(?:\.\d)?)", text)
             + re.findall(r"(\d{2,3}(?:\.\d)?) ?(?:°|degrees?)", text)]
    temps = [t for t in temps if 95 <= t <= 110]
    if temps:
        vitals["temp_f"] = max(temps)
    elif _found(r"(?:have|had|has|got|running|with) (?:a )?(?:high |bad |slight )?fever|feverish", text):
        vitals["temp_f"] = 100.4  # a stated fever with no number meets the fever rule
    m = re.search(r"(?:gained|up|put on)\s+(\d+(?:\.\d)?)\s*(?:pounds?|lbs?)", text)
    if m:
        week = re.search(r"\b(?:week|7 days|seven days|few days|days)\b", text)
        vitals["weight_gain_7d_lb" if week else "weight_gain_24h_lb"] = float(m.group(1))
    m = re.search(r"(?:pulse|heart ?rate|heart is)\D{0,12}(\d{2,3})\b", text)
    if m:
        vitals["heart_rate"] = float(m.group(1))
    m = re.search(r"(?:blood pressure|\bbp\b)\D{0,15}(\d{2,3})\s*(?:/|over)\s*(\d{2,3})", text)
    if m:
        vitals["bp_sys"], vitals["bp_dia"] = float(m.group(1)), float(m.group(2))
    return vitals


def _fires(rule, actual):
    if actual is None:
        return False
    if rule["operator"] == "==":
        return str(actual) == rule["value"]
    a, b = float(actual), float(rule["value"])
    return {">": a > b, ">=": a >= b, "<": a < b, "<=": a <= b}[rule["operator"]]


def check(message):
    """Return a sourced reply when the patient reports a warning sign, else None."""
    text = clean(message)
    if re.search(NOT_ME, text) or not re.search(r"\b(?:i|i'm|im|i've|ive|my|me)\b", text):
        return None
    answers = {key: ("Worse" if key == "leg_swelling" else "Yes") for key, p in PHRASES.items() if _found(p, text)}
    vitals = _vital_values(text)
    hits = [r for r in RULES if _fires(r, answers.get(r["key"]) if r["kind"] == "answer" else vitals.get(r["key"]))]
    if not hits:
        return None
    hits.sort(key=lambda r: -RANK[r["level"]])
    level = hits[0]["level"]
    messages = list(dict.fromkeys(r["message"] for r in hits))
    lead = ("This needs emergency care. " if level == "red"
            else "Your discharge guidance says to contact your care team about this. ")
    return {"answer": lead + " ".join(messages),
            "sources": list(dict.fromkeys(r["source"] for r in hits)),
            "flag": level, "rules": [r["key"] for r in hits]}
