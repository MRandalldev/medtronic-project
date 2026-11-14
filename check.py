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
