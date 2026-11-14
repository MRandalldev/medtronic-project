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
