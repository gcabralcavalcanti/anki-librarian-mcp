"""Similarity index over the whole collection, used to find existing cards close to a new one before creating it.

TF-IDF over word unigrams and bigrams of front + back, cosine similarity, pure Python. The index is cached in the
state folder and refreshed incrementally: only notes that are new or changed since the last run (Anki's `mod`
stamp) are read again, so a large collection is read in full once.
"""

from __future__ import annotations

import itertools
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

STOPWORDS = frozenset(
    """
    a an the of and or to in on at for by with from is are was were be been it its this that these those
    what which who whom how why when where does do did as into than then so not no can could would
    should their there they them his her our your you i we he she
    """.split()
)
BATCH = 200


def tokens(text: str) -> list[str]:
    text = re.sub(r"<[^>]+>|\\\(|\\\)", " ", text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    words = [w for w in re.findall(r"[a-z0-9]+", text) if w not in STOPWORDS and len(w) > 1]
    return words + [f"{a}_{b}" for a, b in itertools.pairwise(words)]


class CollectionIndex:
    def __init__(self, anki, state_dir: Path):
        self.anki = anki
        self.path = Path(state_dir) / "similarity-index.json"
        self.notes: dict[str, dict] = {}  # note id -> {"mod", "front", "back", "tf"}
        if self.path.exists():
            self.notes = json.loads(self.path.read_text(encoding="utf-8"))
        self._idf: dict[str, float] = {}
        self._norms: dict[str, float] = {}

    def refresh(self) -> dict:
        """Read only new or changed notes; drop deleted ones. Returns counts."""
        ids = self.anki.call("findNotes", {"query": "deck:*"})
        live = {str(i) for i in ids}
        removed = [k for k in self.notes if k not in live]
        for k in removed:
            del self.notes[k]
        read = 0
        for start in range(0, len(ids), BATCH):
            chunk = ids[start : start + BATCH]
            for n in self.anki.call("notesInfo", {"notes": chunk}):
                if not n:
                    continue
                key, mod = str(n["noteId"]), n.get("mod")
                if key in self.notes and self.notes[key]["mod"] == mod and mod is not None:
                    continue
                values = [v["value"] for _, v in sorted(n["fields"].items(), key=lambda kv: kv[1]["order"])]
                front, back = values[0], values[1] if len(values) > 1 else ""
                self.notes[key] = {
                    "mod": mod,
                    "front": front,
                    "back": back,
                    "tf": dict(Counter(tokens(front) * 2 + tokens(back))),
                }
                read += 1
        self.path.write_text(json.dumps(self.notes, ensure_ascii=False), encoding="utf-8")
        self._build()
        return {"notes": len(self.notes), "read": read, "removed": len(removed)}

    def _build(self) -> None:
        df = Counter(t for n in self.notes.values() for t in n["tf"])
        total = max(1, len(self.notes))
        self._idf = {t: math.log((1 + total) / (1 + c)) + 1 for t, c in df.items()}
        self._norms = {k: self._norm(n["tf"]) for k, n in self.notes.items()}

    def _norm(self, tf: dict) -> float:
        return math.sqrt(sum((c * self._idf.get(t, 1.0)) ** 2 for t, c in tf.items())) or 1.0

    def search(self, front: str, back: str = "", k: int = 3) -> list[dict]:
        """Top-k existing notes by cosine similarity, with the text to cite in a preview."""
        if not self._idf:
            self._build()
        query = Counter(tokens(front) * 2 + tokens(back))
        qnorm = self._norm(query)
        scores = []
        for key, n in self.notes.items():
            dot = sum(c * n["tf"].get(t, 0) * self._idf.get(t, 1.0) ** 2 for t, c in query.items())
            if dot:
                scores.append((dot / (qnorm * self._norms[key]), key))
        scores.sort(reverse=True)
        return [
            {
                "note_id": int(key),
                "score": round(score, 2),
                "front": self.notes[key]["front"],
                "back": self.notes[key]["back"],
            }
            for score, key in scores[:k]
        ]
