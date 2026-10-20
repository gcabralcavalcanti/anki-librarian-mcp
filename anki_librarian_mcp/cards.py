"""Card rules applied before anything is written: layer, cognitive weight, size ceilings, front checks, TSV.

Cards come in three layers: a map card (`[Map]`, how the pieces of a topic relate), a mechanism card (`[Macro]`)
and short atoms (one link or one fact). Each layer has a ceiling on cognitive weight and on back length,
because a card that asks for too much at once is the one that keeps failing in review.
"""

from __future__ import annotations

import re

MAP, MACRO, RECONSTRUCTION, MNEMONIC = "map", "macro", "reconstruction", "mnemonic"
CEILINGS = {MAP: (14, 1750), MACRO: (10, 1100), RECONSTRUCTION: (5, 500), MNEMONIC: (3, 300)}
PC_PER_HOUR = 20  # review budget used to size an exam batch: useful hours x 20

YEAR = re.compile(r"\b(?:1[5-9]\d\d|20\d\d)(?:\s?[–-]\s?\d{2,4})?\b")  # noqa: RUF001
DECADE = re.compile(r"\b(?:the\s+)?(?:1[5-9]|20)\d0s\b", re.I)
NUMBER_UNIT = re.compile(r"\d[\d.,]*\s?(?:%|bn|billion|million|mn|k\b)|(?:US\$|\$|€|£)\s?\d", re.I)
NAME = re.compile(r"(?<![.!?:>]\s)(?<!^)\b[A-Z][a-zA-Z'-]+(?:\s+(?:of|de|da|do|and|&)?\s*[A-Z][a-zA-Z'-]+)*")
ACRONYM = re.compile(r"\b[A-Z]{2,6}\b")
COUNT_WORDS = r"two|three|four|five|six|seven|eight|nine|ten"
RUBRIC = ("context", "conflict", "policy", "performance", "diagnosis", "instrument", "result", "legacy", "mechanism")
STOP = {
    "The",
    "A",
    "An",
    "In",
    "On",
    "At",
    "For",
    "From",
    "With",
    "When",
    "If",
    "This",
    "That",
    "It",
    "Its",
    "Start",
    "Then",
    "By",
    "As",
    "Definition",
    "Example",
    "Hypotheses",
    "Reading",
    "Errors",
}


def plain(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def split_front(front: str) -> tuple[str, str, str]:
    """(label, theme, question). The theme is the text before the first <br><br>."""
    label = ""
    m = re.match(r"\s*\[(Map|Macro)\]\s*", front)
    if m:
        label, front = m.group(1), front[m.end() :]
    parts = re.split(r"<br>\s*<br>", front, maxsplit=1)
    theme, question = (parts[0], parts[1]) if len(parts) == 2 else ("", parts[0])
    return label, plain(theme), plain(question)


def layer(front: str, back: str) -> str:
    label, _, _ = split_front(front)
    if label == "Map":
        return MAP
    if label == "Macro":
        return MACRO
    text = plain(back)
    return MNEMONIC if len(text) <= 90 and "→" not in text else RECONSTRUCTION


def _blocks(back: str, kind: str) -> int:
    blocks = [b for b in re.split(r"<br>\s*<br>", back or "") if plain(b)]
    if kind in (MAP, MACRO):
        return len(blocks)
    marked = [b for b in blocks if re.match(r"\s*(<b>|[→•·\-–—])", b)]  # noqa: RUF001
    return len(marked) + (1 if len(marked) < len(blocks) else 0)  # unlabelled paragraphs count once


def weight(front: str, back: str) -> dict:
    """Cognitive weight: blocks + arrows + distinct dates + numbers with a unit + new proper names."""
    kind = layer(front, back)
    text = plain(back)
    _, theme, _ = split_front(front)
    theme_words = set(theme.split())
    names = {n for n in NAME.findall(text) if n not in STOP and not set(n.split()) <= theme_words}
    names |= {a for a in ACRONYM.findall(text) if a not in theme_words}
    parts = {
        "blocks": _blocks(back, kind),
        "arrows": text.count("→"),
        "dates": len(set(YEAR.findall(text))),
        "numbers": len(set(NUMBER_UNIT.findall(text))),
        "names": len(names),
    }
    pc_max, chars_max = CEILINGS[kind]
    pc = sum(parts.values())
    problems = []
    if pc > pc_max:
        problems.append(f"cognitive weight {pc} > {pc_max} for a {kind} card: split it or compress it")
    if len(back) > chars_max:
        problems.append(f"back has {len(back)} characters > {chars_max} for a {kind} card")
    return {"layer": kind, "pc": pc, "chars": len(back), "parts": parts, "problems": problems}


def front_problems(front: str, tags: list[str]) -> list[str]:
    """Checks that the question does not give away its answer (verdict, count, date, map structure)."""
    label, theme, question = split_front(front)
    out = []
    history = any("::History" in t or t.startswith("Humanities::History") for t in tags)
    if history and YEAR.search(theme):
        out.append("date in the theme of a history card: name the period instead, put the date on the back")
    if history and (YEAR.search(question) or DECADE.search(question)):
        out.append("date in the question of a history card: the date is part of what to recall")
    reveals = re.search(rf"\b(which|what|name|list)\b.*\b({COUNT_WORDS})\b", question, re.I)
    if reveals and not re.search(rf"\b({COUNT_WORDS}|first|second|third)\s+laws?\b", question, re.I):
        out.append("the question reveals how many items the answer has")
    if label == "Map" and sum(1 for w in RUBRIC if w in question.lower()) >= 3:
        out.append("map question lists the structure of its own answer")
    if not theme:
        out.append("missing theme: write 'Subject: topic <br><br> question'")
    return out


def is_large(front: str, back: str) -> bool:
    """Large cards get the blue flag: maps, macros, or more than 400 characters of plain text."""
    return front.lstrip().startswith(("[Map]", "[Macro]")) or len(plain(back)) > 400


def to_tsv(deck: str, cards: list[dict], notetype: str = "Basic") -> str:
    head = ["#separator:tab", "#html:true", f"#notetype:{notetype}", f"#deck:{deck}", "#tags column:3"]
    lines = []
    for c in cards:
        fields = [c["front"], c["back"], " ".join(c.get("tags", []))]
        lines.append("\t".join(f.replace("\t", " ").replace("\n", "<br>") for f in fields))
    return "\n".join(head + lines) + "\n"


def from_tsv(text: str) -> tuple[str, list[dict]]:
    deck, cards = "", []
    for line in text.splitlines():
        if line.startswith("#deck:"):
            deck = line[6:].strip()
        elif line and not line.startswith("#"):
            cols = line.split("\t")
            if len(cols) in (2, 3):
                cards.append({"front": cols[0], "back": cols[1], "tags": cols[2].split() if len(cols) == 3 else []})
    return deck, cards
