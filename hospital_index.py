"""
hospital_index.py: fast hospital lookup for "Find my care team". (Owner: Jaiden)

Data: sources/hospitals.json (built once by tools/build_hospitals.py from the CMS Hospital
General Information dataset). If that file is missing, it falls back to the live CMS download.

Structures:
  by_state   dict  state -> hospitals sorted by name     (state dropdown -> hospital dropdown)
  postings   dict  word  -> set of hospital ids          (inverted index for free-text search)
  vocab      list  every indexed word, sorted            (binary search finds all words with a prefix)
A query like "moses co gre" matches hospitals that have a word starting with each typed fragment.
"""
import json
import re
from bisect import bisect_left
from pathlib import Path

import streamlit as st

DATA = Path(__file__).parent / "sources" / "hospitals.json"
STOP = {"of", "the", "and", "at", "inc", "llc"}


def words(text: str) -> list:
    return [w for w in re.findall(r"[a-z0-9]+", text.casefold()) if w not in STOP]


class HospitalIndex:
    def __init__(self, rows):
        # rows: (name, city, state, facility_id)
        self.rows = sorted({tuple(r) for r in rows}, key=lambda r: (r[2], r[0]))
        self.by_state = {}
        self.postings = {}
        for i, (name, city, state, _) in enumerate(self.rows):
            self.by_state.setdefault(state, []).append(self.rows[i])
            for w in set(words(f"{name} {city} {state}")):
                self.postings.setdefault(w, set()).add(i)
        self.vocab = sorted(self.postings)

    def states(self) -> list:
        return sorted(self.by_state)

    def _with_prefix(self, fragment: str) -> set:
        """All hospitals containing a word that starts with fragment: O(log V + matches)."""
        found, start = set(), bisect_left(self.vocab, fragment)
        for word in self.vocab[start:]:
            if not word.startswith(fragment):
                break
            found |= self.postings[word]
        return found

    def search(self, query: str, state: str | None = None, limit: int = 30) -> list:
        fragments = words(query)
        if not fragments:
            return []
        hits = None
        for fragment in fragments:
            matched = self._with_prefix(fragment)
            hits = matched if hits is None else hits & matched
            if not hits:
                return []
        def rank(i):
            name, city, st_, _ = self.rows[i]
            name_words = words(name)
            in_name = sum(any(w.startswith(f) for w in name_words) for f in fragments)
            return (-in_name, not name.casefold().startswith(fragments[0]), len(name), name)
        ordered = sorted((i for i in hits if state is None or self.rows[i][2] == state), key=rank)
        return [self.rows[i] for i in ordered[:limit]]


@st.cache_resource(show_spinner=False)
def _load() -> HospitalIndex:
    """Bundled file first (instant, works offline); the live CMS download as a fallback.
    Raises when neither works, so a temporary outage is not cached (Streamlit doesn't cache exceptions)."""
    rows = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
    if not rows:
        import provider_directory
        rows = provider_directory.hospitals()
    if not rows:
        raise ValueError("no hospital data")
    return HospitalIndex(rows)


def load() -> HospitalIndex | None:
    try:
        return _load()
    except Exception:
        return None
