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


# 1. Rules file: 20 sourced rules, no placeholders, every answer rule has a check-in question.
rules = list(csv.DictReader(open(ROOT / "sources/thresholds.csv", encoding="utf-8-sig")))
question_ids = {q["id"] for q in backend.checkin_questions(p, 7)}
expect(len(rules) == 20, f"thresholds.csv should have 20 rules, has {len(rules)}")
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
    "When is my next appointment?": "Nov 19", "What if I faint?": "Dizziness or fainting",
    "Can I take a bath?": "bath", "What time do I take metoprolol?": "8:00", "When can I drive?": "drive",
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

# 8. Reco knowledge base: sourced everyday answers, honest "not sure", crisis support.
import reco_kb
kb_cases = {
    "can I eat pizza?": "diet", "can I have a beer?": "alcohol", "when can I have sex again?": "sex", "I can't sleep": "sleep",
    "I feel sad": "sad", "can I go back to work?": "work", "can I climb stairs?": "stairs", "what is metoprolol for?": "metoprolol_why",
    "can I take Tylenol?": "acetaminophen_why", "can I take advil": "ibuprofen", "can I take aleve for pain": "ibuprofen",
    "should I stop smoking now": "smoking", "can I fly on a plane?": "travel", "who are you?": "who", "what can you do?": "help",
    "what's the capital of France?": None, "how do I fix my wifi": None, "can I lie down on my side": None, "write me a poem": None,
}
for message, entry_id in kb_cases.items():
    found, _ = reco_kb.match(message)
    expect((found or {}).get("id") == entry_id, f"knowledge base: {message!r} should match {entry_id}, got {(found or {}).get('id')}")
for entry in reco_kb.ENTRIES:
    if entry["kind"] == "medical" and entry["id"] not in ("caffeine", "fluids"):
        expect(entry.get("url", "").startswith("https://"), f"knowledge base entry {entry['id']} has no source link")
# Unseen-question regression: written after tuning. Wrong answers matter more than unanswered ones.
unseen = {
    "is green tea ok for me": "caffeine", "how soon can I drive": "driving", "can I push a lawn mower": "chores", "when is sex ok after bypass": "sex",
    "can I take a long hot bath": "bath", "can I wash my hair in the shower": "shower", "my incision is itchy at night": "incision_itch",
    "should I keep my leg propped up": "leg_incision", "I'm nervous about going home": "anxious", "I keep waking up every night": "sleep",
    "how many weeks is the recovery": "timeline", "what is the beta blocker for": "metoprolol_why", "what does a statin do": "atorvastatin_why",
    "can I have a cigarette after dinner": "smoking", "is it safe to get back to my construction job": "work", "thanks a bunch": "thanks",
    "can you remind me to eat": None, "what's the news today": None, "can I take excedrin": None,
}
right = wrong = 0
for message, entry_id in unseen.items():
    found, _ = reco_kb.match(message)
    got = (found or {}).get("id")
    right += got == entry_id
    wrong += got is not None and got != entry_id
expect(wrong <= 1, f"knowledge base gave {wrong} wrong answers on the unseen set (allowed: 1)")
expect(right >= 13, f"knowledge base answered only {right}/{len(unseen)} unseen questions correctly (expected 13+)")
crisis = grounding.answer("I want to kill myself", demo, mode="none")
expect("988" in crisis["answer"] and crisis.get("flag") == "red", "a crisis message did not get 988 and a red flag")
expect(reco_kb.crisis("what if my friend wants to hurt himself") is None, "crisis check fired on someone else's situation")
offtopic = grounding.answer("what's your favorite color", demo, mode="none")["answer"]
expect("not sure" in offtopic.lower(), f"off-topic question was not answered honestly: {offtopic[:70]!r}")
drive = grounding.answer("When can I drive?", demo, mode="none")
expect("Your discharge papers say" in drive["answer"], "Reco did not quote the patient's own papers for driving")
bath = grounding.answer("Can I take a bath?", demo, mode="none")["answer"]
expect("aspirin" not in bath.lower(), "an unrelated line from the papers was attached to the bath answer")
guard_rows = grounding.retrieve("how many acetaminophen tablets can I take for pain", p, [])
for fake in ({"kind": "lookup", "reply": "You can safely take 10 tablets a day.", "ids": [1]},
             {"kind": "social", "reply": "Take as many as you like.", "ids": []}):
    shown = grounding.finish("how many acetaminophen tablets can I take for pain", guard_rows, fake, [])["answer"]
    expect(fake["reply"] not in shown, f"a language model's own medical text reached the patient: {fake['reply']!r}")
print(f"8. Knowledge base checked ({len(reco_kb.ENTRIES)} topics; unseen set {right}/{len(unseen)} right, {wrong} wrong).")

# 9. "Not sure" replies come with clickable next steps that actually answer.
unsure = grounding.answer("can I go to a concert", demo, mode="none")
expect(unsure.get("unsure") and len(unsure.get("suggestions", [])) >= 3, "a 'not sure' reply came without clickable options")
for label in (reco_kb.TODAY_MEDS, reco_kb.NEXT_VISIT, reco_kb.WHEN_CALL):
    reply = grounding.answer(label, demo, mode="none")
    expect(not reply.get("unsure") and bool(reply["sources"]), f"the chip {label!r} does not lead to a real answer")
expect("Metoprolol 25 mg" in grounding.answer(reco_kb.TODAY_MEDS, demo, mode="none")["answer"], "today's medicines list is missing metoprolol")
expect("Call 911 right away for" in grounding.answer(reco_kb.WHEN_CALL, demo, mode="none")["answer"], "the when-to-call list is missing its 911 section")
for entry_id in reco_kb.LABELS:
    reply = grounding.topic_reply(entry_id, p)
    expect(bool(reply and reply["answer"]), f"the topic chip {entry_id!r} has no answer")
expect(grounding.answer("what medicine can I take for pain?", demo, mode="none").get("kb") == "acetaminophen_why",
       "'what medicine can I take for pain' listed all medicines instead of the pain answer")
near_misses = {"can I lift a bag of dog food": "lifting", "when can I fly to see my son": "travel", "is it normal to nap a lot": "tired_normal",
               "can I take aleve instead of tylenol": "ibuprofen", "is it ok to drink champagne at a wedding": "alcohol",
               "can I push a lawn mower": "chores", "is green tea ok for me": "caffeine"}
recovered = 0
for message, entry_id in near_misses.items():
    reply = grounding.answer(message, demo, mode="none")
    recovered += reply.get("kb") == entry_id or entry_id in [c.get("kb") for c in reply.get("suggestions", [])]
expect(recovered >= 6, f"only {recovered}/{len(near_misses)} near-miss questions reached the right topic (answer or chip)")
symptom = grounding.answer("my knee hurts", demo, mode="none")
expect(bool(symptom.get("unsure")) and (symptom.get("suggestions") or [{}])[0].get("page") == "pages/3_Check_in.py",
       "an unplaced symptom did not offer the daily check-in first")
expect("Sample Surgeon" in grounding.answer("who is my surgeon?", demo, mode="none")["answer"], "'who is my surgeon' lost the profile answer")
print(f"9. 'Not sure' chips checked ({recovered}/{len(near_misses)} near misses recovered).")

# 10. Less manual, calmer, consistent: profile autofill, hospital search, dates, emergency flow helpers.
found = plan_reader.read_profile(papers)
expect(found.get("name") == "Marcus Reed" and found.get("surgery_date") == "2026-11-07" and found.get("care_phone") == "(555) 010-0199",
       f"profile fields read from papers as {found}")
expect(plan_reader.read_profile("hello world") == {}, "random text produced profile fields")
from hospital_index import HospitalIndex
hix = HospitalIndex([("Moses H Cone Memorial Hospital", "Greensboro", "NC", "1"), ("Wesley Long Hospital", "Greensboro", "NC", "2"),
                     ("Duke University Hospital", "Durham", "NC", "3"), ("Mayo Clinic Hospital", "Rochester", "MN", "4")])
expect([r[0] for r in hix.search("moses co gre")] == ["Moses H Cone Memorial Hospital"], "hospital prefix search failed")
expect(hix.search("greensboro", state="MN") == [] and len(hix.by_state["NC"]) == 3, "hospital state filter failed")
expect(hix.search("zzz") == [] and hix.search("") == [], "hospital search matched nonsense")
import ui
expect(ui._short("Chest pain or angina symptoms: call 911.") == "Chest pain or angina symptoms", "emergency reason was not shortened")
print("10. Autofill, hospital search and helpers checked.")

# 11. Password rule (NIST SP 800-63B-4: 8+ with a second factor, blocklist, no composition rules)
#     and one fever threshold everywhere.
import password_policy, account_access
expect(password_policy.score("abc")[0] == 0, "a 3-character password is rejected")
expect(password_policy.score("password123")[0] == 0, "a common password is rejected")
expect(password_policy.score("correct horse")[0] >= 2, "a plain passphrase with no symbol is allowed")
expect(password_policy.score("correct horse battery staple")[1] == "Strong", "a long passphrase is Strong")
expect(password_policy.score("jaidenrocks1", "jaiden@x.com")[0] == 0, "a password containing the email name is rejected")
for bad in ("abc", "password123"):
    try:
        account_access.begin("new@example.com", bad, True); expect(False, f"server rejects {bad!r}")
    except ValueError:
        expect(True, f"server rejects {bad!r}")
import glob as _g
_fever_files = [f for f in _g.glob("**/*.py", recursive=True) + _g.glob("sources/*.*") if "hospitals" not in f and "tools/" not in f and "check.py" not in f]
expect(not any(re.search(r"101(?:\.\d)?\s*°?\s*F", open(f, encoding="utf-8", errors="ignore").read()) for f in _fever_files),
       "no second fever threshold (100.4°F is the only one)")
expect((Path("assets") / "heartrise.svg").exists() and "<svg" in (Path("assets") / "heartrise.svg").read_text(), "login artwork is the original heartbeat drawing")
print("11. Password rule, fever threshold and login art checked.")

# 12. Sponsor checklist: check-in numbers, reminders, two-way care team, dashboard, caregiver. All rule-based.
import copy, datetime as _dt
import schedule_export, chat_rules
_real_now = data.now_local
data.now_local = lambda: _dt.datetime(2026, 11, 14, 10, 30)   # fixed clock so date maths is the same on every run
try:
    sp = copy.deepcopy(data.load_sample())
    expect(any(q["id"] == "overall" for q in backend.checkin_questions(sp, 7)), "check-in asks how the patient feels overall (recovery progress)")
    expect(backend.score_checkin(calm, {**normal, "bp_sys": 185, "bp_dia": 95})["level"] == "yellow", "blood pressure 185/95 is yellow (AHA)")
    expect(backend.score_checkin(calm, {**normal, "bp_sys": 180, "bp_dia": 120})["level"] == "green", "blood pressure exactly 180/120 does not fire (rule is 'higher than')")
    bp_chat = chat_rules.check("my blood pressure is 190 over 100")
    expect(bool(bp_chat) and bp_chat["flag"] == "yellow", "blood pressure typed into Reco is scored by the same rule")
    merged = data.latest_vitals({"vitals": [{"time": "2026-11-14 08:00", "heart_rate": 112, "simulated": True},
                                             {"time": "2026-11-14 09:00", "temp_f": 100.6, "source": "check-in"}]})
    expect(merged.get("heart_rate") == 112 and merged.get("temp_f") == 100.6, "a watch pulse and a typed temperature are both scored")
    old = data.latest_vitals({"vitals": [{"time": "2026-11-10 08:00", "heart_rate": 120}, {"time": "2026-11-14 09:00", "temp_f": 98.6}]})
    expect("heart_rate" not in old, "a four-day-old pulse is not treated as today's reading")
    # medicines: adherence, overdue, as-needed limit
    sp["med_log"] = {"2026-11-13": {"Aspirin 81 mg 08:00": True, "Metoprolol 25 mg 08:00": True, "Atorvastatin 40 mg 21:00": True},
                     "2026-11-14": {"Aspirin 81 mg 08:00": True}}
    adh = data.adherence(sp)
    expect((adh["taken"], adh["due"]) == (4, 6), f"adherence counts 4 of 6 doses, got {adh['taken']} of {adh['due']}")
    expect(("2026-11-13", "Metoprolol 25 mg", "20:00") in adh["missed"] and ("2026-11-14", "Metoprolol 25 mg", "08:00") in adh["missed"], "missed doses are named")
    expect(data.adherence({**sp, "med_log": {}})["due"] == 0, "no dose history means no adherence claim, not 0%")
    expect(data.overdue_doses(sp) == [("Metoprolol 25 mg", "08:00")], f"overdue dose list is {data.overdue_doses(sp)}")
    expect("missed" in backend.care_team_summary(sp)["summary"] and "4 of 6" in backend.care_team_summary(sp)["summary"], "care team summary reports missed doses")
    prn = data.prn_meds(sp)
    expect(len(prn) == 1 and prn[0]["max_24h"] == 6 and prn[0]["gap_hours"] == 6, f"as-needed limits read from the papers: {prn}")
    sp["prn_log"] = [{"time": "2026-11-13 09:00", "name": prn[0]["name"], "count": 2}, {"time": "2026-11-13 22:00", "name": prn[0]["name"], "count": 2},
                     {"time": "2026-11-14 09:30", "name": prn[0]["name"], "count": 2}]
    st_prn = data.prn_status(sp, prn[0])
    expect(st_prn["taken_24h"] == 4 and st_prn["left"] == 2, f"as-needed count uses a rolling 24 hours: {st_prn}")
    expect(st_prn["next_ok"] == _dt.datetime(2026, 11, 14, 15, 30), "next as-needed dose is 6 hours after the last one")
    # reminders
    expect([r["name"] for r in data.refill_reminders(sp)] == ["Metoprolol 25 mg"], "refill due within two weeks is listed")
    sp["refilled"] = {"Metoprolol 25 mg": "2026-11-26"}
    expect(data.refill_reminders(sp) == [], "a refill marked done stops reminding")
    entries = list(schedule_export.schedule(sp["plan"], _dt.date(2026, 11, 14), 30, "09:00"))
    ics = schedule_export.calendar_file(entries, "demo", True).decode()
    expect(sum(t == "Daily check-in · Reco" for _, t, _ in entries) == 30, "a daily check-in reminder is in the export")
    refill_block = ics.split("SUMMARY:Refill · Metoprolol")[0].rsplit("BEGIN:VEVENT", 1)[1] + ics.split("SUMMARY:Refill · Metoprolol")[1].split("END:VEVENT")[0]
    expect(refill_block.count("BEGIN:VALARM") == 2 and "-P2DT15H" in refill_block.replace("\r\n ", ""), "refills alert three days before and on the day")
    expect(len(list(schedule_export.schedule(sp["plan"], _dt.date(2026, 11, 14), 1))) == 4, "the month view still shows doses only (no reminder rows)")
    # dashboard, visits, caregiver
    stones = data.milestones(sp)
    expect(any(m["date"] == "2026-12-19" and "lift" in m["label"] for m in stones), "six-week lifting limit from the papers is a milestone")
    expect(any(m["label"] == "Went home from the hospital" and m["done"] for m in stones), "discharge is a completed milestone")
    expect(data.next_visit(sp)[1]["date"] == "2026-11-19", "next visit is Nov 19")
    sp["alerts"] = [{"time": "2026-11-14 09:00", "level": "yellow", "reasons": [{"message": "Chills: call your care team today.", "source": "https://x"}]}]
    qs = data.visit_questions(sp)
    expect(any("chills" in q for q in qs) and any("missed" in q for q in qs), f"visit prep lists flags and missed doses: {qs}")
    expect(data.next_action(sp)["kind"] == "yellow", "an open alert is the first next step")
    sp["alerts"] = []
    expect(data.next_action(sp)["kind"] == "dose", "then an overdue dose")
    sp["med_log"]["2026-11-14"]["Metoprolol 25 mg 08:00"] = True
    expect(data.next_action(sp)["kind"] == "checkin", "then today's check-in")
    sp["checkins"] = [{"date": "2026-11-14", "answers": {"overall": "Better"}, "level": "green", "reasons": [], "numbers": {"pain": 3, "walk_min": 20}}]
    expect(data.next_action(sp)["title"] == "Next: Metoprolol 25 mg at 8:00 PM", f"then the next dose: {data.next_action(sp)['title']}")
    update = data.daily_update(sp)
    expect(all(x in update for x in ("Marcus", "all clear", "Pain 3/10", "2 of 4", "Nov 19")), f"caregiver update is built from today's record: {update}")
    expect(data.human_time("2026-11-14 10:42") == "Sat, Nov 14 at 10:42 AM" and data.clock_12("20:00") == "8:00 PM", "times are written the way people say them")
finally:
    data.now_local = _real_now
import month_view as _mv, inspect as _insp
expect('"%H:%M") if timed else "All day"' not in _insp.getsource(_mv), "calendar shows 12-hour times like the rest of the app")
meds_answer = grounding.immediate_reply("what medicines do I take today", data.load_sample())["answer"]
expect("8:00 AM, 8:00 PM" in meds_answer and "20:00" not in meds_answer, f"Reco reads times the way people say them: {meds_answer[:120]}")
print("12. Check-in numbers, reminders, care-team loop, dashboard and caregiver update checked.")

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

    def do_checkin(at, ticks=(), pain=0, walk="10 to 20 minutes", temp=None):
        """Walk the one-question-per-screen check-in: tick what is asked (else None of these), Same, a pain level, a walk."""
        at.switch_page("pages/3_Check_in.py").run()
        if any(b.label == "Check in again" for b in at.button):
            click(at, "Check in again")
        for _ in range(12):
            if any(b.label == "Submit check-in" for b in at.button):
                if temp is not None:
                    [n for n in at.number_input if n.label.startswith("Temperature")][0].set_value(temp)
                    at.run()
                click(at, "Submit check-in")
                return
            boxes = [c for c in at.checkbox if c.key and c.key.startswith("ci_")]
            pain_pick = [g for g in at.button_group if g.key == "n_pain"]
            if boxes:
                hits = [c for c in boxes if any(c.label.startswith(t) for t in ticks)]
                for c in hits or [c for c in boxes if c.label == "None of these"]:
                    c.check()
                at.run()
            elif pain_pick:
                pain_pick[0].set_value(pain).run()
            elif at.radio:
                at.radio[0].set_value(walk if at.radio[0].key == "n_walk_pick" else "Same").run()
            click(at, "Continue")
        expect(False, "app: the check-in never reached Submit")

    empty = dict(name="", age=None, height_in=None, surgery="", surgery_date="", doctor="", last_appointment="",
                 caregiver="", vitals=[], documents=[], checkins=[], messages=[], alerts=[], med_log={},
                 plan={"medications": [], "follow_ups": [], "warning_signs": []})
    for label, patient in (("demo patient", None), ("new empty profile", empty)):
        at = fresh(patient)
        for page in sorted(str(x.relative_to(ROOT)).replace("\\", "/") for x in ROOT.glob("pages/*.py")):
            at.switch_page(page).run()
            expect(not at.exception, f"app ({label}): {page} crashed: {[e.message[:120] for e in at.exception]}")
            expect(not at.get("help"), f"app ({label}): {page} printed Streamlit internals (a bare expression)")

    at = fresh()
    at.switch_page("pages/2_Upload_papers.py").run()
    click(at, "Use the demo patient's papers")
    expect(len(at.session_state["patient"]["plan"]["medications"]) == 4, "app: demo papers did not build 4 medicines")
    at.text_area[0].set_value("hello, this is not a discharge paper")
    click(at, "Build my plan")
    expect(len(at.session_state["patient"]["plan"]["medications"]) == 4, "app: pasting random text wiped the plan")

    at.switch_page("pages/watch.py").run()
    click(at, "Simulate watch reading")
    do_checkin(at)
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
    import browser_engine
    real_generate = browser_engine.generate
    browser_engine.generate = lambda request, key: {"id": request["id"], "unavailable": True}  # a cold browser model
    at.text_input[0].set_value("can I go to a concert")
    click(at, "Ask")
    chips = [b.label for b in at.button if b.key and b.key.startswith("chip_")]
    expect(reco_kb.NEXT_VISIT in chips, f"app: 'not sure' reply showed no clickable options ({chips})")
    click(at, reco_kb.NEXT_VISIT)
    last = at.session_state["patient"]["assistant_history"][-1]
    expect("Nov 19" in last["answer"], f"app: clicking the appointment chip answered {last['answer'][:60]!r}")
    browser_engine.generate = real_generate

    # Emergency flow, demo safety, autofill, devices scenario and the mismatch answer, in the real app.
    at = fresh()
    expect(at.session_state["patient"].get("care_phone") == "(555) 010-0199", "app: demo patient has no care team phone")
    do_checkin(at, ticks=("Any chest pain",))
    labels = [b.label for b in at.button]
    expect("1  Call 911" in labels, f"app: red check-in shows no 911 button ({labels[:6]})")
    page_html = " ".join(str(h.proto) for h in at.get("html"))
    expect("tel:911" not in page_html, "app: demo mode rendered a real 911 phone link")
    expect(at.session_state["last_result_date"] == data.now_local().date().isoformat(), "app: check-in result is not dated in local time")
    expect(at.session_state["patient"]["checkins"][-1]["date"] == data.now_local().date().isoformat(), "app: check-in saved with the server's date")
    at.switch_page("pages/watch.py").run()
    click(at, "Play scenario")
    sims = [v for v in at.session_state["patient"]["vitals"] if v.get("simulated")]
    expect(len(sims) == 6 and sims[-1]["heart_rate"] == 112, f"app: heart-rate scenario added {len(sims)} readings")
    do_checkin(at)
    expect(at.session_state["last_result"]["level"] == "yellow" and at.session_state.get("mismatch"),
           "app: the climbing heart rate did not trigger yellow plus the mismatch question")
    before = len(at.session_state["patient"]["alerts"])
    click(at, "Yes, I feel worse than I said")
    expect(len(at.session_state["patient"]["alerts"]) == before + 1, "app: answering the mismatch question did not reach the care team")
    at.switch_page("pages/settings.py").run()
    expect(not at.exception, f"app: settings crashed {[e.message[:100] for e in at.exception]}")
    at.session_state["care_signed_in"] = True
    at.switch_page("pages/7_Care_team.py").run()
    flags = [e.value for e in at.error] + [w.value for w in at.warning]
    expect(any("RED" in f for f in flags), "app: the care team view shows no red flag after a red check-in")
    expect(not at.get("help"), "app: the care team view printed Streamlit internals")
    empty_profile = dict(empty, plan={"medications": [], "follow_ups": [], "warning_signs": []})
    at = fresh(empty_profile)
    at.switch_page("pages/2_Upload_papers.py").run()
    at.text_area[0].set_value(papers)
    click(at, "Build my plan")
    filled = at.session_state["patient"]
    expect(filled.get("name") == "Marcus Reed" and filled.get("care_phone") == "(555) 010-0199", "app: papers did not fill an empty profile")
    filled["name"] = "Marc"
    click(at, "Build my plan")
    expect(at.session_state["patient"]["name"] == "Marc", "app: autofill overwrote a name the patient typed")
    expect(not at.exception, f"app: demo flow raised {[e.message[:120] for e in at.exception]}")
    # Check-in numbers -> sourced rule -> care team acknowledges -> patient sees it. Then messages, visits, refills, pain medicine.
    at = fresh()
    at.switch_page("pages/3_Check_in.py").run()
    click(at, "Continue")
    expect(at.session_state.get("ci_step", 0) == 0 and any("None of these" in w.value for w in at.warning),
           "app: the check-in moved on with nothing tapped (None of these must be chosen explicitly)")
    do_checkin(at, ticks=("Any unusual bleeding",), pain=4, walk="10 to 20 minutes", temp=100.6)
    answers = at.session_state["patient"]["checkins"][-1]["answers"]
    expect(answers.get("t_bleeding") == "Yes", "app: the blood-thinner question was not asked or not saved for a patient on aspirin")
    expect("unusual bleeding" in backend.care_team_summary(at.session_state["patient"])["summary"], "app: care team summary leaves out the tailored answer")
    expect(at.session_state["last_result"]["level"] == "yellow", "app: a typed temperature of 100.6 is not yellow")
    saved = at.session_state["patient"]["checkins"][-1]["numbers"]
    expect(saved.get("pain") == 4 and saved.get("walk_min") == 15 and saved.get("temp_f") == 100.6, f"app: check-in numbers not saved ({saved})")
    expect(any(m.label == "Pain" and m.value == "4/10" for m in at.metric), "app: the check-in recap does not show the pain score")
    expect(any(b.label == "I took 1" for b in at.button), "app: pain reported but no as-needed medicine counter shown")
    click(at, "I took 2")
    expect(not any(b.label in ("I took 1", "I took 2") for b in at.button), "app: a second as-needed dose is offered inside the 6-hour gap")
    expect(sum(r["count"] for r in at.session_state["patient"]["prn_log"]) == 2, "app: as-needed dose not logged")
    at.switch_page("pages/7_Care_team.py").run()
    click(at, "Sign in as care team")
    click(at, "Acknowledge and tell the patient")
    pt = at.session_state["patient"]
    expect(pt["alerts"][-1].get("ack") and data.unread(pt, "Care team") == 1, "app: acknowledging a flag did not notify the patient")
    at.switch_page("pages/4_Dashboard.py").run()
    expect(any("saw today's alert" in s_.value for s_ in at.success), "app: Today does not tell the patient the care team saw the alert")
    expect(any("Call your care team today" in m.value for m in at.markdown), "app: Today's next step is not the open alert")
    [c for c in at.checkbox if "Aspirin" in c.label][0].check().run()
    expect(at.session_state["patient"]["med_log"][data.now_local().date().isoformat()].get("Aspirin 81 mg 08:00") is True, "app: a dose cannot be ticked from Today")
    click(at, "I'll be there")
    expect(at.session_state["patient"]["plan"]["follow_ups"][0].get("status") == "confirmed", "app: visit confirmation not saved")
    click(at, "I refilled it")
    expect(at.session_state["patient"].get("refilled", {}).get("Metoprolol 25 mg") == "2026-11-26", "app: refill not marked done")
    at.switch_page("pages/messages.py").run()
    expect(data.unread(at.session_state["patient"], "Care team") == 0, "app: opening Messages did not mark the reply as read")
    at.text_area[0].set_value("Thank you, I will wait for the call.")
    click(at, "Send message")
    at.switch_page("pages/7_Care_team.py").run()
    expect(any("Thank you, I will wait" in m.value for m in at.markdown), "app: the patient's message does not reach the care team view")
    expect(any("Patient confirmed" in s_.value for s_ in at.success), "app: care team cannot see the visit was confirmed")
    click(at, "Save date and tell the patient")   # cardiac rehab had no date
    rehab = at.session_state["patient"]["plan"]["follow_ups"][2]
    expect(bool(rehab["date"]) and "Cardiac rehabilitation" in at.session_state["patient"]["messages"][-1]["text"], "app: care team could not schedule the undated visit")
    at.switch_page("pages/progress.py").run()
    expect(any(m.label == "Latest pain" and m.value == "4/10" for m in at.metric), "app: dashboard does not show the pain trend")
    at.switch_page("pages/caregiver.py").run()
    expect(any("call the care team today" in w.value for w in at.warning), "app: caregiver view does not show today's alert")
    # Profile questionnaire: one question per screen with dropdowns, Back keeps answers, the end opens Today.
    def profile_flow(at, name, med, freq, relation, caregiver):
        at.switch_page("pages/1_Onboarding.py").run()
        [t for t in at.text_input if t.label == "Preferred name"][0].set_value(name).run()
        click(at, "Continue")
        click(at, "←")
        expect([t for t in at.text_input if t.label == "Preferred name"][0].value == name, "app: Back lost the typed name")
        click(at, "Continue")
        click(at, "Continue")              # surgery
        click(at, "Continue")              # hospital
        click(at, "Continue")              # doctor
        at.multiselect[0].set_value([med]).run()
        click(at, "Continue")              # medicines
        at.radio[0].set_value(freq).run()
        click(at, "Continue")              # how often
        at.radio[0].set_value(relation).run()
        [t for t in at.text_input if t.label == "Their name"][0].set_value(caregiver).run()
        click(at, "Continue")              # caregiver
        click(at, "Continue")              # about
        click(at, "Save and go to Today")
    at = fresh()
    profile_flow(at, "Marcus R.", "Aspirin 81 mg", "Once a day, morning", "Daughter", "Dana Reed")
    saved = at.session_state["patient"]
    expect(saved["name"] == "Marcus R." and saved["caregiver"] == "Dana Reed (daughter)" and saved["surgery"].startswith("Coronary"),
           f"app: profile questionnaire did not save every answer ({saved.get('name')}, {saved.get('caregiver')})")
    expect(len(saved["plan"]["medications"]) == 4, "app: the profile replaced medicines that came from the discharge papers")
    expect(not at.exception, f"app: profile flow raised {[e.message[:120] for e in at.exception]}")
    at = fresh(dict(empty, plan={"medications": [], "follow_ups": [], "warning_signs": []}))
    profile_flow(at, "Lena", "Metoprolol 25 mg", "Twice a day", "Sister", "Ava")
    plan = at.session_state["patient"]["plan"]["medications"]
    expect(plan == [{"name": "Metoprolol 25 mg", "dose": "Twice a day (you told us; check your papers)", "times": ["08:00", "20:00"],
                     "refill_date": "", "source": "self-reported"}], f"app: a new account's medicines did not become reminders ({plan})")
    print("7. App click-through checked (every page, two profiles, full demo flow).")
else:
    print("7. App click-through skipped (--quick).")

if failures:
    print(f"\n{len(failures)} CHECK(S) FAILED. Do not merge until these pass.")
    sys.exit(1)
print("\nALL CHECKS PASSED. Safe to merge.")
