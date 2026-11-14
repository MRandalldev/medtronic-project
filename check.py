"""Run `python check.py` after changing backend.py. It checks every function still returns the agreed shape."""
import json
import backend

p = json.load(open("data/sample_patient.json"))
plan = backend.extract_plan("sample text")
assert set(plan) >= {"medications", "warning_signs", "follow_ups"}, "extract_plan shape changed"
qs = backend.checkin_questions(p, 2)
assert all({"id", "text", "options"} <= set(q) for q in qs), "checkin_questions shape changed"
ans = {q["id"]: q["options"][0] for q in qs}
r = backend.score_checkin(ans, p["vitals"][-1])
assert r["level"] in ("green", "yellow", "red") and isinstance(r["reasons"], list), "score_checkin shape changed"
m = backend.check_mismatch(ans, p["vitals"][-1])
assert m is None or isinstance(m, str), "check_mismatch shape changed"
a = backend.ask_assistant("Can I shower?", p)
assert isinstance(a["answer"], str) and isinstance(a["sources"], list), "ask_assistant shape changed"
s = backend.care_team_summary(p)
assert {"summary", "flags", "next_follow_up"} <= set(s), "care_team_summary shape changed"
print("All 6 backend functions match the contract.")


# Chat regressions from the mobile demo. Each turn owns its own flag and sources.
import grounding
assert "19" in grounding.immediate_reply("What's 9 + 10?", {})["answer"]
assert "flag" not in grounding.immediate_reply("my stomach hurts", {})
for message in ("i am in tremendous pain", "i am dying"):
    urgent = grounding.immediate_reply(message, {})
    assert urgent["flag"] == "red" and "911" in urgent["answer"]
assert grounding.immediate_reply("I have no chest pain", {}) is None
assert grounding.immediate_reply("No chest pain, but I cannot breathe", {})
assert "flag" not in grounding.immediate_reply("help", {"assistant_history": [urgent]})
print("Reco message and flag checks passed.")

history = []
for message, expected in [
        ("my stomach hurts", ["belly pain"]),
        ("i have been vomiting", ["belly pain", "vomiting"]),
        ("my anus hurts when i poop", ["belly pain", "vomiting", "bowel movement"])]:
    reply = grounding.immediate_reply(message, {}, history)
    assert reply["sources"] and all(word in reply["answer"].lower() for word in expected[1:] or ["belly"])
    assert all(any(word in symptom for symptom in reply["symptoms"]) for word in expected)
    history.append({"question": message, **reply})
assert "vomiting" in grounding.immediate_reply("since yesterday", {}, history)["answer"]
assert grounding.immediate_reply("vomiting, belly pain, and painful bowel movements", {})["symptoms"] == history[-1]["symptoms"]
assert grounding.immediate_reply("vomiting blood and belly pain", {})["flag"] == "red"
assert grounding.immediate_reply("no vomiting or nausea", {}) is None
assert grounding.immediate_reply("my friend has been vomiting", {}) is None
assert grounding.immediate_reply("I can't keep water down", {}, history)["flag"] == "yellow"
assert grounding.immediate_reply("I have belly pain but no vomiting", {})["symptoms"] == ["belly pain"]
print("Consecutive symptom reports, combined reports, and warning signs passed.")


# =====================================================================================
# Demo-safety checks (Jaiden). These protect the judged demo path. If any line prints
# FAIL, do not merge: the change broke something a judge will see.
# Run all: python check.py      Skip the slower app click-through: python check.py --quick
# =====================================================================================
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
failures = []


def expect(ok, what):
    if not ok:
        failures.append(what)
        print("  FAIL:", what)


# 1. Rules file: 18 sourced rules, no placeholders, every answer rule has a check-in question.
rules = list(csv.DictReader(open(ROOT / "sources/thresholds.csv", encoding="utf-8-sig")))
question_ids = {q["id"] for q in backend.checkin_questions(p, 7)}
expect(len(rules) == 18, f"thresholds.csv should have 18 rules, has {len(rules)}")
for rule in rules:
    expect("PLACEHOLDER" not in ",".join(rule.values()), f"placeholder left in rule {rule['key']}")
    expect(rule["source"].startswith("https://"), f"rule {rule['key']} has no source link")
    expect(rule["level"] in ("red", "yellow"), f"rule {rule['key']} has level {rule['level']!r}")
    if rule["kind"] == "answer":
        expect(rule["key"] in question_ids, f"rule {rule['key']} has no matching check-in question")
print("1. Rules file checked.")

# 2. Paper to plan, using the on-device reader (no API key needed).
import plan_reader
papers = (ROOT / "data/demo_discharge_papers.txt").read_text(encoding="utf-8")
plan = plan_reader.read(papers)
names = [m["name"] for m in plan["medications"]]
expect(names == ["Aspirin 81 mg", "Metoprolol 25 mg", "Atorvastatin 40 mg", "Acetaminophen 500 mg"], f"medicines read as {names}")
meto = next((m for m in plan["medications"] if m["name"].startswith("Metoprolol")), {})
expect(meto.get("times") == ["08:00", "20:00"] and meto.get("refill_date") == "2026-11-26", f"metoprolol read as {meto}")
expect(len(plan["warning_signs"]) == 13, f"expected 13 warning signs, got {len(plan['warning_signs'])}")
expect([f["date"] for f in plan["follow_ups"]] == ["2026-11-19", "2026-12-03", ""], f"follow-ups read as {plan['follow_ups']}")
expect(plan_reader.validate({"medications": [{"name": "X", "times": "08:00, 20:00"}]})["medications"][0]["times"] == ["08:00", "20:00"],
       "an AI reply with times as one string is split into characters")
junk = plan_reader.read("hello, this is not a discharge paper")
expect(not (junk["medications"] or junk["warning_signs"] or junk["follow_ups"]), "random text produced a plan")
print("2. Paper-to-plan checked.")

# 3. Check-in scoring and the mismatch ("I'm fine" but the readings changed).
calm = {q["id"]: ("Same" if q["id"] == "leg_swelling" else "No") for q in backend.checkin_questions(p, 7)}
normal = {"heart_rate": 80, "spo2": 96, "temp_f": 98.6, "weight_gain_24h_lb": 0.4, "weight_gain_7d_lb": -0.5}
expect(backend.score_checkin(calm, normal)["level"] == "green", "a calm check-in with normal readings is not green")
expect(backend.score_checkin({**calm, "chest_pain": "Yes"}, normal)["level"] == "red", "chest pain is not red")
expect(backend.score_checkin({**calm, "incision_signs": "Yes"}, normal)["level"] == "yellow", "incision signs are not yellow")
expect(backend.score_checkin(calm, {**normal, "temp_f": 100.4})["level"] == "yellow", "a 100.4 F fever is not yellow")
expect(backend.score_checkin(calm, {**normal, "weight_gain_24h_lb": 2})["level"] == "yellow", "a 2 lb one-day gain is not yellow")
racing = {**normal, "heart_rate": 112}
expect(backend.score_checkin(calm, racing)["level"] == "yellow", "a resting pulse of 112 is not yellow")
expect(isinstance(backend.check_mismatch(calm, racing), str), "the mismatch question did not appear for 'fine' + pulse 112")
expect(backend.check_mismatch({**calm, "chest_pain": "Yes"}, racing) is None, "the mismatch question appeared when the patient reported a symptom")
import data
gain = data.latest_vitals({"vitals": [{"time": "2026-11-12 08:00", "weight_lb": 180}, {"time": "2026-11-13 08:00", "weight_lb": 182.5}]})
expect(gain.get("weight_gain_24h_lb") == 2.5, f"one-day weight gain computed as {gain.get('weight_gain_24h_lb')}")
expect(isinstance(data.latest_vitals({"vitals": [{"time": "not a time", "heart_rate": 70}]}), dict), "an odd reading time crashes latest_vitals")
print("3. Check-in scoring checked.")

# 4. Reco safety: a symptom typed into chat must get the same answer level as the check-in rules.
demo = {**p, "assistant_history": []}
chat_cases = {
    "I have chest pain": "red", "My chest feels tight": "red", "I fainted": "red", "I feel dizzy": "red",
    "my heart is racing": "red", "my face is drooping": "red", "I'm sweating a lot": "red",
    "I can't breathe": "red", "I have a fever of 101": "yellow", "I've had a fever for 10 days": "yellow",
    "I gained 3 pounds since yesterday": "yellow", "I gained 6 pounds this week": "yellow", "my pulse is 112": "yellow",
    "my incision is red and oozing": "yellow", "my legs are swollen": "yellow", "I keep coughing": "yellow",
    "my breastbone clicks": "yellow", "I have chills": "yellow", "I ran out of my metoprolol": "yellow",
    "I can’t keep water down": "yellow", "I've been vomiting": "yellow",
    "I don't feel dizzy": None, "my incision is not red": None, "I have no fever": None, "my temp is 99.1": None,
    "I gained 1 pound": None, "my pulse is 72": None, "I coughed once": None, "my wife feels dizzy": None,
    "What if I faint?": None, "is it normal to feel dizzy?": None, "Can I take a bath?": None, "hi": None,
}
for message, level in chat_cases.items():
    reply = grounding.answer(message, demo, mode="none")
    expect(reply.get("flag") == level, f"Reco: {message!r} should be {level}, got {reply.get('flag')}")
    if level == "red":
        expect("911" in reply["answer"], f"Reco: {message!r} is red but does not say 911")
    if level:
        expect(bool(reply["sources"]), f"Reco: {message!r} gave a warning with no source")
print(f"4. Reco safety checked ({len(chat_cases)} messages).")

# 5. Reco lookups without any model (the hosted fallback path).
lookups = {
    "When is my next appointment?": "2026-11-19", "What if I faint?": "Dizziness or fainting",
    "Can I take a bath?": "soak", "What time do I take metoprolol?": "8:00", "When can I drive?": "drive",
}
for message, needle in lookups.items():
    answer = grounding.answer(message, demo, mode="none")["answer"]
    expect(needle.lower() in answer.lower(), f"Reco: {message!r} answered {answer[:80]!r}")
for message in ("what was my heart rate?", "how is my weight?"):
    answer = grounding.answer(message, demo, mode="none")["answer"]
    expect(not answer.lstrip().startswith("{"), f"Reco: {message!r} shows raw data {answer[:60]!r}")
print("5. Reco lookups checked.")

# 6. No garbled characters (text saved in the wrong encoding shows up as junk on screen).
garbled = ("Ã", "â€", "Â·")
for path in list(ROOT.glob("*.py")) + list(ROOT.glob("pages/*.py")) + list(ROOT.glob("sources/*")) + list(ROOT.glob("data/*.json")):
    if path.name == "check.py":
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    expect(not any(g in text for g in garbled), f"garbled characters in {path.relative_to(ROOT)}")
summary = backend.care_team_summary(p)
expect("placeholder" not in summary["summary"].lower(), "the care team summary still says placeholder")
print("6. Text and care-team summary checked.")

# 7. Click through the app like a judge would (slower; skip with --quick).
if "--quick" not in sys.argv:
    from streamlit.testing.v1 import AppTest

    def fresh(patient=None):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        at.session_state["demo"] = True
        if patient is not None:
            at.session_state["patient"] = patient
        at.run()
        return at

    def click(at, label):
        buttons = [b for b in at.button if b.label == label]
        expect(bool(buttons), f"app: no button called {label!r}")
        if buttons:
            buttons[0].click().run()

    empty = dict(name="", age=None, height_in=None, surgery="", surgery_date="", doctor="", last_appointment="",
                 caregiver="", vitals=[], documents=[], checkins=[], messages=[], alerts=[], med_log={},
                 plan={"medications": [], "follow_ups": [], "warning_signs": []})
    for label, patient in (("demo patient", None), ("new empty profile", empty)):
        at = fresh(patient)
        for page in sorted(str(x.relative_to(ROOT)).replace("\\", "/") for x in ROOT.glob("pages/*.py")):
            at.switch_page(page).run()
            expect(not at.exception, f"app ({label}): {page} crashed: {[e.message[:120] for e in at.exception]}")

    at = fresh()
    at.switch_page("pages/2_Upload_papers.py").run()
    click(at, "Use the demo patient's papers")
    expect(len(at.session_state["patient"]["plan"]["medications"]) == 4, "app: demo papers did not build 4 medicines")
    at.text_area[0].set_value("hello, this is not a discharge paper")
    click(at, "Build my plan")
    expect(len(at.session_state["patient"]["plan"]["medications"]) == 4, "app: pasting random text wiped the plan")

    at.switch_page("pages/watch.py").run()
    click(at, "Simulate watch reading")
    at.switch_page("pages/3_Check_in.py").run()
    for radio in at.radio:
        radio.set_value("Same")
    at.run()
    click(at, "Submit check-in")
    expect(at.session_state["last_result"]["level"] == "yellow", "app: watch reading + 'fine' check-in is not yellow")
    expect(bool(at.session_state.get("mismatch")), "app: the mismatch question did not appear after the watch reading")

    at.switch_page("pages/5_Assistant.py").run()
    at.text_input[0].set_value("I fainted this morning")
    click(at, "Ask")
    history = at.session_state["patient"].get("assistant_history", [])
    expect(bool(history) and history[-1].get("flag") == "red", "app: 'I fainted' in Reco was not flagged red")
    alerts = at.session_state["patient"]["alerts"]
    expect(any(a["level"] == "red" for a in alerts) and any(a["level"] == "yellow" for a in alerts),
           "app: the care team did not receive both the check-in and the chat flags")
    expect(not at.exception, f"app: demo flow raised {[e.message[:120] for e in at.exception]}")
    print("7. App click-through checked (every page, two profiles, full demo flow).")
else:
    print("7. App click-through skipped (--quick).")

if failures:
    print(f"\n{len(failures)} CHECK(S) FAILED. Do not merge until these pass.")
    sys.exit(1)
print("\nALL CHECKS PASSED. Safe to merge.")
