"""Pure checks used before a plan is shown: tag taxonomy, cloze syntax, text normalization, similarity."""
from __future__ import annotations

import difflib
import re
import unicodedata

from .config import Taxonomy

CLOZE = re.compile(r"\{\{c(\d+)::(.+?)\}\}", re.S)


def normalize(text: str) -> str:
    """Lowercase, no HTML, no accents, single spaces: the form used to compare fronts."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def keywords(text: str, n: int = 4) -> list[str]:
    """The n longest distinct words of a front: the search terms used for reconciliation."""
    words = sorted({w for w in normalize(text).split() if len(w) > 3}, key=lambda w: (-len(w), w))
    return words[:n]


def tag_errors(tags: list[str], tax: Taxonomy) -> list[str]:
    """Problems with a note's tags against the taxonomy; each one names a fix when it can."""
    if not tax.roots:
        return []
    allowed = {r.lower(): r for r in tax.roots + tax.operational}
    errors, has_taxonomy_tag = [], False
    for tag in tags:
        parts = tag.split("::")
        root = parts[0]
        if root not in tax.roots + tax.operational:
            hint = f" (did you mean {allowed[root.lower()]}?)" if root.lower() in allowed else \
                f" (allowed roots: {', '.join(tax.roots)})"
            errors.append(f"tag '{tag}': unknown root '{root}'{hint}")
            continue
        if len(parts) > tax.max_depth:
            errors.append(f"tag '{tag}': deeper than {tax.max_depth} levels")
        bad = [p for p in parts if not re.match(tax.segment_pattern, p)]
        if bad:
            errors.append(f"tag '{tag}': segment(s) {bad} break the naming rule (Capitalized, no spaces)")
        if root in tax.roots:
            has_taxonomy_tag = True
    if tax.required and not has_taxonomy_tag:
        errors.append(f"no taxonomy tag (needs one under {', '.join(tax.roots)})")
    return errors


def cloze_errors(text: str) -> list[str]:
    if not CLOZE.search(text):
        return ["no cloze deletion: use {{c1::answer}}"]
    if text.count("{{") != text.count("}}"):
        return ["unbalanced cloze braces"]
    return []
