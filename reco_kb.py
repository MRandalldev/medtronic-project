"""
reco_kb.py: Reco's knowledge base. (Owner: Jaiden)

sources/knowledge.json holds common recovery questions, each with several example
phrasings, an answer written in our own words and the source it came from. A message
is matched with TF-IDF (rare, meaningful words count more than common ones) and cosine
similarity. Below the confidence threshold Reco does not guess.

Safety order in grounding.immediate_reply: crisis -> emergency -> warning-sign rules ->
this knowledge base -> patient records -> optional language model.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

ENTRIES = json.loads((Path(__file__).parent / "sources/knowledge.json").read_text(encoding="utf-8"))
THRESHOLD = 0.42
COVERAGE = 0.45

STOP = set("""a an the i me my mine we our you your yours it its is am are was were be been being do does did
to of in on at for with and or but if so as by from this that these those there here what whats which who
whom how when where why can could should would will shall may might must have has had having im ive id
ill reco please just really very ok okay also about any some get got going go still yet now today
allowed allow safe much many take taking need want again start soon long often bad good fine way thing things
lot little too so time day days week weeks able like know tell explain mean anymore
dont doesnt didnt cant wont isnt arent havent hasnt wasnt shouldnt""".split())

# Words patients use -> the word the knowledge base uses.
SYNONYMS = {
    "tylenol": "acetaminophen", "paracetamol": "acetaminophen", "lopressor": "metoprolol", "toprol": "metoprolol",
    "lipitor": "atorvastatin", "statin": "atorvastatin", "advil": "ibuprofen", "motrin": "ibuprofen",
    "aleve": "ibuprofen", "naproxen": "ibuprofen", "nsaid": "ibuprofen", "beer": "alcohol", "wine": "alcohol",
    "liquor": "alcohol", "booze": "alcohol", "drunk": "alcohol", "vodka": "alcohol", "whiskey": "alcohol",
    "cigarette": "smoke", "cigarettes": "smoke", "vape": "smoke", "vaping": "smoke", "nicotine": "smoke",
    "tobacco": "smoke", "smoking": "smoke", "decaf": "caffeine", "jog": "run", "jogging": "run", "intimate": "sex", "intercourse": "sex", "sexual": "sex", "plane": "fly",
    "flight": "fly", "airplane": "fly", "trip": "travel", "vacation": "travel", "car": "drive",
    "job": "work", "office": "work", "gym": "exercise", "workout": "exercise", "salt": "sodium",
    "salty": "sodium", "coffee": "caffeine", "latte": "caffeine", "espresso": "caffeine", "cappuccino": "caffeine", "margarita": "alcohol", "cocktail": "alcohol", "hiking": "walk", "hike": "walk", "stroll": "walk", "milk": "lifting", "groceries": "lifting", "stockings": "stocking", "socks": "stocking", "trash": "chores", "tea": "caffeine", "soda": "caffeine", "steps": "stairs",
    "staircase": "stairs", "tub": "bath", "pool": "swim", "jacuzzi": "bath", "scar": "incision",
    "wound": "incision", "depressed": "sad", "crying": "sad", "cry": "sad",
    "hopeless": "sad", "worried": "scared", "anxious": "scared", "nervous": "scared",
    "afraid": "scared", "fear": "scared", "insomnia": "sleep", "asleep": "sleep", "poop": "constipated",
    "laxative": "constipated", "grandson": "grandkids", "granddaughter": "grandkids", "baby": "grandkids",
    "kids": "grandkids", "pills": "medicine", "pill": "medicine", "meds": "medicine", "medication": "medicine",
    "medications": "medicine", "tablets": "medicine", "food": "eat", "eating": "eat", "meal": "eat",
    "diet": "eat", "bacon": "eat", "chocolate": "eat", "pizza": "eat", "burger": "eat", "burgers": "eat", "chips": "eat", "steak": "eat", "cheese": "eat", "candy": "eat", "cake": "eat", "cookies": "eat", "icecream": "eat", "sugar": "eat", "dessert": "eat", "sweets": "eat", "fries": "eat", "hamburger": "eat", "sausage": "eat", "eggs": "eat", "fruit": "eat", "vegetables": "eat", "junk": "eat", "fatigue": "tired", "exhausted": "tired", "water": "fluids", "cabg": "bypass",
}


def _stem(word):
    for end in ("ing", "ed", "s"):
        if len(word) > len(end) + 2 and word.endswith(end) and not word.endswith(("eed", "ss")):
            word = word[:-len(end)]
            if end != "s" and len(word) > 3 and word[-1] == word[-2] and word[-1] not in "lsz":
                word = word[:-1]  # swimming -> swimm -> swim, stopped -> stopp -> stop
            return word
    return word


PHRASE_JOIN = {"ice cream": "icecream", "out of state": "travel", "out of town": "travel",
               "take out the trash": "chores", "heart attack": "heartattack"}


def tokens(text):
    text = text.casefold().replace("’", "'").replace("'", "")
    for phrase, joined in PHRASE_JOIN.items():
        text = text.replace(phrase, joined)
    words = re.findall(r"[a-z0-9]+", text)
    return [_stem(SYNONYMS.get(w, w)) for w in words if w not in STOP]


def _norm(text):
    text = re.sub(r"[^a-z0-9 ]+", "", text.casefold().replace("\u2019", "").replace("'", ""))
    text = re.sub(r"^(?:(?:hey|hi|ok|okay|so|reco)\s+)+", "", " ".join(text.split()))
    return re.sub(r"\s+reco$", "", text)


# Chit-chat ("who are you", "thanks") is matched on the whole phrase: its words are too common for TF-IDF.
_PHRASES = {_norm(ex): e for e in ENTRIES if e["kind"] in ("about", "social") for ex in e["examples"]}

# Build TF-IDF vectors for every example phrasing of the medical entries once, at import.
_examples = [(i, tokens(ex)) for i, e in enumerate(ENTRIES) if e["kind"] == "medical" for ex in e["examples"]]
_df = Counter(t for _, toks in _examples for t in set(toks))
_N = len(_examples)
IDF = {t: math.log((1 + _N) / (1 + df)) + 1 for t, df in _df.items()}
_UNKNOWN_IDF = sum(IDF.values()) / len(IDF)


def _vector(toks):
    counts = Counter(toks)
    # Words the library has never seen get an average weight, so one unknown word can't swamp the rest.
    vec = {t: c * IDF.get(t, _UNKNOWN_IDF) for t, c in counts.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {t: v / norm for t, v in vec.items()}


_vectors = [(i, _vector(toks)) for i, toks in _examples]
# Each entry's examples and answer together, so words that only appear in the answer still count.
_entry_vectors = [(i, _vector([t for ex in e["examples"] for t in tokens(ex)] + tokens(e["answer"])))
                  for i, e in enumerate(ENTRIES) if e["kind"] == "medical"]
ENTRY_WEIGHT = 0.85

# Strong topic words. If a message names one, only entries about that topic may answer it,
# so "Aleve for pain" can't be answered with the Tylenol entry.
ANCHORS = {_stem(w) for w in """acetaminophen ibuprofen aspirin metoprolol atorvastatin grapefruit alcohol caffeine
smoke sex drive fly travel work bath swim shower stairs incision sodium constipated sleep stocking rehab
run gym golf tennis basketball bike""".split()}
_entry_words = {i: {t for ex in e["examples"] for t in tokens(ex)} | set(tokens(e["answer"]))
                for i, e in enumerate(ENTRIES) if e["kind"] == "medical"}
VOCAB = set(IDF)
MEDICAL_IDS = {e["id"] for e in ENTRIES if e["kind"] == "medical"}

CHAT_PATTERNS = [
    ("thanks", r"\b(?:thanks|thank you|thx|appreciate it)\b"),
    ("bye", r"^\W*(?:bye|goodbye|good night|see you|talk (?:to you )?later)\b"),
    ("who", r"\b(?:are you|is this)\s+(?:a |an )?(?:bot|robot|ai|human|person|real|doctor|nurse|computer)\b|\bwho (?:are|made) you\b"),
    ("help", r"\bwhat (?:can|are) you (?:able to )?(?:do|help)|\bwhat can i ask\b|\bhow can you help\b"),
]

# Questions about the patient's own data go to his records, not the general library.
PERSONAL = re.compile(r"\b(?:refill|appointment|visit|follow.?up|schedule|next|what time|when do i take|"
                      r"when should i take|my dose|how many .* left|last check.?in|my (?:weight|pulse|heart rate|readings?))\b", re.I)

CRISIS = re.compile(r"\b(?:kill(?:ing)? myself|suicid\w*|want to die|wanna die|end (?:my|it all)|end my life|"
                    r"hurt(?:ing)? myself|harm(?:ing)? myself|self.?harm|don'?t want to (?:live|be here)|"
                    r"better off dead|no reason to live)\b", re.I)


def crisis(question):
    """Thoughts of self-harm always get crisis resources first, never a library passage."""
    text = question.replace("’", "'")
    if CRISIS.search(text) and not re.search(r"\b(?:my (?:mother|father|friend|wife|husband)|what if)\b", text, re.I):
        return {"answer": "I'm really glad you told me. You deserve support right now. Please call or text 988 "
                          "(the Suicide & Crisis Lifeline) any time, day or night. If you might act on these "
                          "thoughts or are in danger, call 911. Can you reach someone you trust to stay with you?",
                "sources": ["988 Suicide & Crisis Lifeline · https://988lifeline.org"], "flag": "red"}
    return None


def match(question):
    """Return (entry, score) for the best knowledge-base entry, or (None, score) if unsure."""
    phrase = _PHRASES.get(_norm(question))
    if phrase:
        return phrase, 1.0
    if len(question.split()) <= 7:
        for entry_id, pattern in CHAT_PATTERNS:
            if re.search(pattern, question, re.I):
                return next(e for e in ENTRIES if e["id"] == entry_id), 1.0
    toks = tokens(question)
    q = _vector(toks)
    if not q:
        return None, 0.0
    anchors = ANCHORS.intersection(toks)
    allowed = {i for i, words in _entry_words.items() if anchors & words} if anchors else None
    if not allowed:
        allowed = None  # an anchor no entry mentions ("tennis") must not block everything
    best, best_score = None, 0.0
    for weight, vectors in ((1.0, _vectors), (ENTRY_WEIGHT, _entry_vectors)):
        for i, vec in vectors:
            if allowed is not None and i not in allowed:
                continue
            score = weight * sum(w * vec.get(t, 0.0) for t, w in q.items())
            if score > best_score:
                best, best_score = ENTRIES[i], score
    if not best or best_score < THRESHOLD:
        return None, best_score
    # The matched entry must cover most of what the question is about, not just one shared word.
    idx = ENTRIES.index(best)
    covered = sum(w for t, w in q.items() if t in _entry_words.get(idx, ()))
    if covered / (sum(q.values()) or 1) < COVERAGE:
        return None, best_score
    return best, best_score


def reply(question, patient):
    """A sourced answer from the knowledge base, personalised with the patient's own plan."""
    if re.match(r"^(?:can|could|will|would) you (?:please )?(?:order|buy|book|call|text|email|send|pay|make me|get me)\b", question.strip(), re.I):
        return {"answer": "I can't do that from here. I'm here for your recovery: your medicines, appointments, "
                          "what's normal, and when to call your care team.", "sources": [], "kb": "redirect"}
    if PERSONAL.search(question):
        return None
    entry, score = match(question)
    if not entry:
        return None
    answer = entry["answer"]
    if entry.get("med"):
        for med in patient.get("plan", {}).get("medications", []):
            if entry["med"] in med.get("name", "").casefold():
                answer += f" Your plan: {med['name']}, {med.get('dose', '')} ({', '.join(med.get('times', []))})."
                break
    sources = [f"{entry['title']} · {entry['url']}"] if entry.get("url") else []
    if entry["kind"] == "medical" and entry.get("url") and "papers" not in answer:
        answer += " If your discharge papers say something different, follow your papers."
    return {"answer": answer, "sources": sources, "kb": entry["id"], "confidence": round(score, 2)}
