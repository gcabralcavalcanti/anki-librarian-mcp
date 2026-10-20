"""The card-making flow end to end, as the demo runs it: the skills are the model's instructions, code does the
collection search and the checks, and the server's own plan, approval and write steps finish the job.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import cards, checks
from .config import Taxonomy
from .llm import LLM
from .retrieval import CollectionIndex
from .service import Librarian

SKILLS = Path(__file__).parent / "skills"
LAYERS = ["map", "macro", "reconstruction", "mnemonic"]


def skill(name: str) -> str:
    return (SKILLS / f"{name}.md").read_text(encoding="utf-8")


def _obj(props: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


S, INT = {"type": "string"}, {"type": "integer"}
HARVEST = _obj(
    {
        "style": {"type": "string", "enum": list("ABCDEF")},
        "objective": {"type": "string", "enum": ["quick-prep", "deep-study", "reference"]},
        "lens": S,
        "themes": {
            "type": "array",
            "items": _obj(
                {
                    "title": S,
                    "output": {"type": "string", "enum": ["theory", "tools", "story"]},
                    "items": {
                        "type": "array",
                        "items": _obj(
                            {
                                "anchor": S,
                                "text": S,
                                "marker": {"type": "string", "enum": ["", "REVERSE", "APPLIED", "VERIFY"]},
                            }
                        ),
                    },
                }
            ),
        },
        "doubts": {"type": "array", "items": _obj({"question": S, "resolution": S})},
        "open_doubts": {"type": "array", "items": S},
    }
)
PLAN = _obj(
    {
        "register": {
            "type": "array",
            "items": _obj({"name": {"type": "string", "enum": ["TP", "TO", "DP", "CH", "MN"]}, "percent": INT}),
        },
        "subject_type": S,
        "skeleton": S,
        "verdicts": {
            "type": "array",
            "items": _obj(
                {
                    "concept": S,
                    "verdict": {"type": "string", "enum": ["GAP", "ALREADY HAVE", "OUT OF SCOPE"]},
                    "note_id": INT,
                    "reason": S,
                }
            ),
        },
        "nuclei": {
            "type": "array",
            "items": _obj(
                {"name": S, "layers": {"type": "array", "items": {"type": "string", "enum": LAYERS}}, "cards": INT}
            ),
        },
        "essential_core": {"type": "array", "items": S},
        "order": S,
    }
)
CARDS = _obj(
    {
        "cards": {
            "type": "array",
            "items": _obj(
                {
                    "layer": {"type": "string", "enum": LAYERS},
                    "front": S,
                    "back": S,
                    "tags": {"type": "array", "items": S},
                }
            ),
        },
    }
)


def search_existing(index: CollectionIndex, harvest: dict, k: int = 2) -> list[dict]:
    """For every harvested concept and doubt, the closest existing cards (code does the search, not the model)."""
    queries = [(i["anchor"], i["text"]) for t in harvest["themes"] for i in t["items"]]
    queries += [(d["question"], d["resolution"]) for d in harvest["doubts"]]
    found = []
    for anchor, text in queries:
        hits = [h for h in index.search(anchor, text, k=k) if h["score"] >= 0.2]
        if hits:
            found.append(
                {
                    "concept": anchor,
                    "existing": [
                        {"note_id": h["note_id"], "score": h["score"], "front": cards.plain(h["front"])} for h in hits
                    ],
                }
            )
    return found


def card_problems(taxonomy: Taxonomy):
    def check(answer: dict) -> list[str]:
        out = []
        for n, c in enumerate(answer["cards"], 1):
            w = cards.weight(c["front"], c["back"])
            out += [f"card {n}: {p}" for p in w["problems"]]
            out += [f"card {n}: {p}" for p in cards.front_problems(c["front"], c["tags"])]
            out += [f"card {n}: {p}" for p in checks.tag_errors(c["tags"], taxonomy)]
        return out

    return check


def run(llm: LLM, lib: Librarian, name: str, material: str, deck: str, max_cards: int = 10) -> dict:
    """One example through every step. Returns everything the report shows."""
    harvest = llm.ask(f"{name}-harvest", skill("harvest"), f"Harvest this material.\n\n{material}", HARVEST)
    lib.index.refresh()
    found = search_existing(lib.index, harvest)
    plan_prompt = (
        "RECONCILE mode. The harvest is below, followed by the results of a search in the user's collection "
        "(note ids and fronts of the closest existing cards). Judge every concept and every doubt: ALREADY HAVE "
        "(give the note_id) only if an existing card's recall target is that concept at the needed depth; "
        f"otherwise GAP (note_id 0). Plan at most {max_cards} new cards.\n\nHARVEST:\n{json.dumps(harvest)}\n\n"
        f"SEARCH RESULTS:\n{json.dumps(found)}"
    )
    plan = llm.ask(f"{name}-plan", skill("planner"), plan_prompt, PLAN)
    gen_system = "\n\n---\n\n".join([skill("generator"), skill("tags"), skill("taxonomy")])
    gen_prompt = (
        f"Write the cards for the GAP concepts and the doubts of this plan, at most {max_cards} cards, in plan "
        "order. Tags must start with a taxonomy root. Do not write cards for ALREADY HAVE or OUT OF SCOPE.\n\n"
        f"PLAN:\n{json.dumps(plan)}\n\nMATERIAL:\n{material}"
    )
    generated = llm.ask(f"{name}-cards", gen_system, gen_prompt, CARDS, check=card_problems(lib.s.taxonomy))
    for c in generated["cards"]:
        c["weight"] = cards.weight(c["front"], c["back"])
    notes = [{"front": c["front"], "back": c["back"], "tags": c["tags"]} for c in generated["cards"]]
    proposal = lib.propose_add_notes(deck, notes)
    approved = lib.approve(proposal["id"], via="demo (simulated click)") if proposal["status"] == "pending" else None
    applied = lib.apply(proposal["id"]) if approved else None
    written = lib.get_notes(applied["result"]["created"]) if applied else []
    flags = {}
    if written:
        card_ids = [
            c for n in lib.anki.call("notesInfo", {"notes": [w["note_id"] for w in written]}) for c in n["cards"]
        ]
        flags = {c["note"]: c["flags"] for c in lib.anki.call("cardsInfo", {"cards": card_ids})}
    for w in written:
        w["blue_flag"] = flags.get(w["note_id"]) == 4
    return {
        "name": name,
        "deck": deck,
        "material": material,
        "harvest": harvest,
        "search": found,
        "plan": plan,
        "cards": generated["cards"],
        "proposal": proposal,
        "applied": applied,
        "written": written,
    }
