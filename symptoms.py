"""Short, sourced responses for symptom reports, including consecutive chat turns."""
import re

BELLY = "belly pain"
VOMIT = "vomiting"
NAUSEA = "nausea"
RECTAL = "pain around the anus or during a bowel movement"
SOURCES = {
    BELLY: "MedlinePlus · Abdominal pain · https://medlineplus.gov/ency/article/003120.htm",
    VOMIT: "MedlinePlus · Nausea and vomiting · https://medlineplus.gov/ency/article/003117.htm",
    RECTAL: "NHS · Anal pain · https://www.nhs.uk/symptoms/anal-pain/",
}
SOURCES[NAUSEA] = SOURCES[VOMIT]

ACHE = r"(?:hurt(?:s|ing)?|ach(?:e|es|ing)|pain(?:ful)?)"
PATTERNS = {
    BELLY: rf"\b(?:(?:stomach|belly|tummy|abdomen|abdominal)\s*(?:is |has been )?{ACHE}|pain in (?:my |the )?(?:belly|stomach|abdomen))\b",
    VOMIT: r"\b(?:vomit(?:ing|ed)?|throw(?:ing)? up|threw up|puk(?:e|ed|ing)|being sick)\b",
    NAUSEA: r"\b(?:nausea(?:ted)?|nauseous|queasy|feel sick to my stomach)\b",
    RECTAL: rf"\b(?:(?:anus|rectum|bottom|butthole|butt|anal|rectal) (?:is )?{ACHE}|painful (?:bowel movements?|poops?)|{ACHE} (?:when|to|while) (?:i )?(?:poop|pass stool|have a bowel movement))\b",
}
DANGER = r"\b(?:(?:vomit(?:ing|ed)?|threw up|throwing up) (?:bright red |fresh |some )?blood|blood in (?:my |the )?vomit|(?:vomit(?:ed|ing)? (?:what |something |material )?(?:that )?(?:looks? like )?coffee grounds)|(?:heavy|nonstop|non-stop|uncontrolled) (?:rectal )?bleeding)\b"
FLUIDS = r"\b(?:can(?:not|'t)|unable to) keep (?:any |even )?(?:water|fluids?|liquids?|anything) down\b"
NON_REPORT = re.compile(r"\b(?:what if|what (?:is|causes)|if (?:i|someone)|used to|last year|my (?:mother|father|friend|wife|husband|child)|(?:he|she|they) (?:is|was|has|had|keeps))\b")


def matches(pattern, text):
    for clause in re.split(r"[.,;!?]|\b(?:but|however)\b", text):
        for found in re.finditer(pattern, clause):
            prefix = clause[:found.start()]
            if not re.search(r"\b(?:no|not|never|without|denies|isn't|wasn't|haven't|hasn't|didn't|don't)(?:\s+\w+){0,4}\s*$", prefix):
                return True
    return False


def reply(message, history):
    text = message.casefold().replace("’", "'").strip()
    educational = re.match(r"^(?:can|could|does|why|how|what|is|are|tell me about)\b", text)
    first_person = re.search(r"\b(?:i|my|i'm|i've)\b", text)
    if NON_REPORT.search(text) or (educational and not first_person):
        return None
    prior = history[-1].get("symptoms", []) if history else []
    if matches(DANGER, text) or (VOMIT in prior and re.fullmatch(r"(?:yes[, ]+)?(?:blood|coffee grounds)[.! ]*", text)):
        return {"answer": "Get emergency help now. Call 911 in the US or your local emergency number. Tell them about the bleeding and your recent surgery.",
                "flag": "red", "sources": [SOURCES[RECTAL] if "bleeding" in text else SOURCES[VOMIT]]}
    current = [name for name, pattern in PATTERNS.items() if matches(pattern, text)]
    fluids = matches(FLUIDS, text)
    if VOMIT in prior and re.search(r"\b(?:[3-9]|[1-9]\d+|three|four|five|six|seven|eight|nine|ten) times (?:today|in (?:a|one) day)\b", text):
        return {"answer": "Call your surgical team now. Tell them how many times you’ve vomited today and whether you can keep fluids down.",
                "sources": [SOURCES[VOMIT]], "flag": "yellow", "symptoms": prior}
    if not current and not fluids:
        if prior and re.fullmatch(r"(?:since |about |for |it (?:started|began) )?(?:yesterday|today|last night|this morning|(?:a|one|two|three|four|five|\d+) (?:times|hours?|days?)(?: ago)?)[.! ]*", text):
            return {"answer": "Tell your surgical team that detail along with the symptoms you described: " + ", ".join(prior) + ". If these symptoms are continuing, call your team today.",
                    "sources": list(dict.fromkeys(SOURCES[s] for s in prior)), "symptoms": prior}
        return None
    combined = list(dict.fromkeys([*prior, *current]))
    sources = list(dict.fromkeys(SOURCES[k] for k in combined))
    if fluids:
        return {"answer": "Call your surgical team now and tell them you can’t keep liquids down. If you feel faint or very unwell and can’t reach them, seek urgent medical care.",
                "sources": list(dict.fromkeys([SOURCES[VOMIT], *sources])), "flag": "yellow", "symptoms": combined}
    if len(combined) > 1:
        lead = "You’ve mentioned " + ", ".join(combined[:-1]) + " and " + combined[-1] + ". "
    else:
        lead = ""
    if RECTAL in current:
        detail = "Pain when passing stool is worth discussing with your surgical team today. Have you noticed any bleeding? If bleeding is heavy or won’t stop, get emergency help now."
    elif VOMIT in current:
        detail = "Call your surgical team today about the vomiting. How many times have you vomited, and can you keep liquids down? If you vomit blood or material that looks like coffee grounds, get emergency help now."
    elif NAUSEA in current:
        detail = "When did the nausea start, and can you keep liquids down? Tell your surgical team about new or persistent nausea during recovery."
    else:
        detail = "Where in your belly does it hurt, and when did it start? If the pain is sudden or severe, get emergency help now. For new pain during recovery, contact your surgical team."
    result = {"answer": lead + detail, "sources": sources, "symptoms": combined}
    if VOMIT in current or RECTAL in current:
        result["flag"] = "yellow"
    return result
