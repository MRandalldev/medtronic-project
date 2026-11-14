"""Select traceable source passages for the synthetic recovery demo."""
import json
import os
import re
from pathlib import Path
import requests

LIBRARY = json.loads((Path(__file__).parent / "sources/recovery.json").read_text(encoding="utf-8"))
SYSTEM = ("Compose one answer using the supplied passages. Return JSON with ids containing the "
          "passage numbers in reading order. Include each distinct fact needed to answer all parts "
          "of the question. Exclude unrelated facts. Return an empty list when unsupported.")


def urgent_guidance(question):
    terms = ("my heart hurts", "heart is hurting", "heart hurts", "heart pain", "chest hurts", "chest is hurting", "chest tightness", "chest pain", "chest pressure", "chest discomfort", "shortness of breath",
             "can't breathe", "cannot breathe", "difficulty breathing", "severe bleeding")
    if any(term in question.lower().replace("’", "'") for term in terms):
        return {"answer": "If you are experiencing these symptoms now, call 911 in the US or your local emergency number.",
                "sources": ["American Heart Association · https://www.heart.org/en/health-topics/house-calls/when-to-call-911"]}
    return None


def immediate_reply(question, patient):
    """Handle time-sensitive and conversational intents before looking up passages."""
    urgent = urgent_guidance(question)
    if urgent:
        return urgent
    words = re.findall(r"[a-z0-9]+", question.casefold())
    phrase = " ".join(w for w in words if w not in {"reco", "rico"})
    if phrase in {"hi", "hello", "hey", "good morning", "good evening", ""}:
        name = patient.get("name", "").split()
        greeting = f"Hi, {name[0]}!" if name else "Hi!"
        return {"answer": greeting + " I’m Reco. What would you like help with today?", "sources": []}
    if phrase in {"what happened", "what happened to me", "what surgery did i have"}:
        if patient.get("surgery"):
            return {"answer": "Your profile lists " + patient["surgery"] +
                    (f" on {patient['surgery_date']}" if patient.get("surgery_date") else "") +
                    ". Is that what you wanted to know, or are you asking about how you feel now?",
                    "sources": ["Your profile"]}
        return {"answer": "Do you mean what happened during your procedure, or something you’re feeling now?", "sources": []}
    if phrase in {"thanks", "thank you"}:
        return {"answer": "You’re welcome. I’m here if you have another question.", "sources": []}
    return None


def candidates(question, patient):
    tokens = set(re.findall(r"[a-z0-9]+", question.lower())) - set("i me my the a this is are with in when can do you of for to it and what how after before please should be have on or who tell also where which is follow following".split())
    rows = []
    profile_fields = {"doctor": "Doctor or care team", "hospital": "Hospital",
                      "surgery": "Procedure", "caregiver": "Caregiver", "preference": "Saved preference",
                      "reported_meds": "Self-reported medicines", "name": "Preferred name",
                      "age": "Age", "height_in": "Height in inches", "surgery_date": "Surgery date"}
    for field, label in profile_fields.items():
        if patient.get(field):
            tags = {"preference": "remember preference", "reported_meds": "meds medicines medications taking",
                    "doctor": "physician clinician surgeon"}.get(field, "")
            rows.append(dict(title="Your profile", text=f"{label}: {patient[field]}", tags=tags))
    for med in patient.get("plan", {}).get("medications", []):
        rows.append(dict(title="Your saved medication schedule",
                         text=f"{med['name']} · {med['dose']} · {', '.join(med['times'])}",
                         tags="meds medicines medications dose doses time schedule"))
    for visit in patient.get("plan", {}).get("follow_ups", []):
        rows.append(dict(title="Your saved follow-up", text=f"{visit['date']} · {visit['with']} · {visit['purpose']}", tags="appointment visit follow up followup surgeon date"))
    for doc in patient.get("documents", []):
        for line in doc["text"].splitlines():
            if line.strip():
                rows.append(dict(title=doc["name"], text=line.strip()[:600], tags=""))
    rows.extend(LIBRARY)
    ranked = []
    for row in rows:
        words = set(re.findall(r"[a-z0-9]+", " ".join((row["title"], row["text"], row["tags"])).lower()))
        score = len(tokens & words)
        if row in LIBRARY and not tokens.intersection(row["tags"].split()):
            score = 0
        if score:
            ranked.append((score, row))
    return [r for _, r in sorted(ranked, key=lambda item:-item[0])[:4]]

def prompt(question, rows):
    return json.dumps({"question":question[:1200], "passages":{str(i):f"{r['title']}: {r['text']}" for i,r in enumerate(rows,1)}},ensure_ascii=False)

def selection_schema(count):
    return {"type": "object", "properties": {"ids": {"type": "array", "maxItems": count,
            "items": {"type": "integer", "enum": list(range(1, count + 1))}}}, "required": ["ids"]}


def select(question, rows):
    response = requests.post("http://127.0.0.1:11434/api/chat", json={
        "format": selection_schema(len(rows)), "model": os.getenv("RECOVERY_MODEL", "qwen2.5:0.5b"),
        "stream": False, "messages": [{"role": "system", "content": SYSTEM},
                                      {"role": "user", "content": prompt(question, rows)}],
        "options": {"temperature": 0, "num_predict": 64}}, timeout=(2, 20))
    response.raise_for_status()
    return json.loads(response.json()["message"]["content"])["ids"]


def compose(rows, ids):
    passages, sources = [], []
    for index in ids if isinstance(ids, list) else []:
        if type(index) is int and 1 <= index <= len(rows):
            row = rows[index - 1]
            source = row["title"] + (" · " + row["url"] if row.get("url") else "")
            if row["text"] not in passages:
                passages.append(row["text"])
            if source not in sources:
                sources.append(source)
    return {"answer": "\n\n".join(passages) or "I couldn’t find that in your saved plan or recovery references. Your care team can help.",
            "sources": sources}


def answer(question, patient, mode="Ollama"):
    direct = immediate_reply(question, patient)
    if direct:
        return direct
    rows = candidates(question, patient)
    if rows and mode == "Ollama":
        try:
            return compose(rows, select(question, rows))
        except (ValueError, KeyError, requests.RequestException):
            pass
    return compose(rows, [1])
