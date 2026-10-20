"""Static HTML page that shows the card-making flow step by step, two examples side by side."""

from __future__ import annotations

import html
import re
from pathlib import Path

from . import cards

STAGES = [
    ("1", "Material", "What you hand over: notes, a chapter, a case."),
    ("2", "Harvest", "What was learned and what was asked, grouped by theme."),
    ("3", "Search and plan", "The collection is searched first; only what is missing gets planned."),
    ("4", "Cards written", "Three layers, each within its size limit; questions that do not give the answer away."),
    ("5", "Server check", "A dry run: duplicates skipped, similar cards cited, tags and sizes checked."),
    ("6", "Your approval", "Nothing is written until you click. The model cannot approve for you."),
    ("7", "In Anki", "Written, read back and compared; large cards get a blue flag."),
]


def esc(text: str) -> str:
    return html.escape(text or "")


def safe_card_html(text: str) -> str:
    """Card fields are HTML; keep only the tags Anki cards here use."""
    text = html.escape(text or "")
    for tag in ("b", "/b", "i", "/i", "br"):
        text = text.replace(f"&lt;{tag}&gt;", f"<{tag}>")
    return re.sub(r"&lt;img src=&quot;([\w.-]+)&quot;&gt;", r'<span class="img">[picture: \1]</span>', text)


def chips(*items: str) -> str:
    return "".join(f'<span class="chip">{esc(i)}</span>' for i in items if i)


def card_box(front: str, back: str, layer: str, weight: dict | None = None, flag: bool = False) -> str:
    meter = ""
    if weight:
        limit = cards.CEILINGS[weight["layer"]][0]
        pct = min(100, 100 * weight["pc"] / limit)
        meter = (
            f'<div class="meter" title="cognitive weight {weight["pc"]} of {limit}"><span style="width:{pct:.0f}%">'
            f"</span></div><small>weight {weight['pc']}/{limit} · {weight['chars']} chars</small>"
        )
    return (
        f'<div class="card{" flag" if flag else ""}"><div class="layer {layer}">{esc(layer)}</div>'
        f'<div class="front">{safe_card_html(front)}</div><div class="back">{safe_card_html(back)}</div>{meter}</div>'
    )


def stage_material(ex: dict) -> str:
    lines = [ln for ln in ex["material"].splitlines() if ln.strip()]
    intro = " ".join(lines[1:3]).replace("**", "")
    return (
        f'<div class="material"><b>{esc(lines[0].lstrip("# "))}</b><br>{esc(intro[:420])}…</div>'
        f"<details><summary>full text</summary><pre>{esc(ex['material'])}</pre></details>"
    )


def stage_harvest(ex: dict) -> str:
    h = ex["harvest"]
    out = [chips(f"style {h['style']}", h["objective"], f"lens: {h['lens']}")]
    for t in h["themes"]:
        items = "".join(
            f"<li><b>{esc(i['anchor'])}</b>: {esc(i['text'])}"
            f"{' <span class=mark>' + esc(i['marker']) + '</span>' if i['marker'] else ''}</li>"
            for i in t["items"]
        )
        out.append(f"<h4>{esc(t['title'])} <small>· {esc(t['output'])}</small></h4><ul>{items}</ul>")
    if h["doubts"]:
        out.append(
            "<h4>Doubts raised</h4><ul>"
            + "".join(f"<li><b>{esc(d['question'])}</b> → {esc(d['resolution'])}</li>" for d in h["doubts"])
            + "</ul>"
        )
    if h["open_doubts"]:
        out.append("<h4>Still open</h4><ul>" + "".join(f"<li>{esc(d)}</li>" for d in h["open_doubts"]) + "</ul>")
    return "".join(out)


def stage_plan(ex: dict) -> str:
    p = ex["plan"]
    bar = "".join(
        f'<span class="reg {r["name"]}" style="flex:{max(r["percent"], 1)}">{r["name"]} {r["percent"]}%</span>'
        for r in p["register"]
        if r["percent"] > 0
    )
    rows = []
    fronts = {e["note_id"]: e["front"] for s in ex["search"] for e in s["existing"]}
    for v in p["verdicts"]:
        cited = esc(fronts.get(v["note_id"], "")) if v["note_id"] else ""
        rows.append(
            f'<tr><td>{esc(v["concept"])}</td><td><span class="verdict {v["verdict"].split()[0]}">'
            f"{esc(v['verdict'])}</span></td><td>{cited or esc(v['reason'])}</td></tr>"
        )
    return (
        f'<div class="regbar">{bar}</div>{chips(p["subject_type"])}<p class="skel">{esc(p["skeleton"])}</p>'
        f"<table><tr><th>Concept</th><th>Verdict</th><th>Existing card / reason</th></tr>{''.join(rows)}</table>"
    )


def stage_cards(ex: dict) -> str:
    return "".join(card_box(c["front"], c["back"], c["layer"], c["weight"]) for c in ex["cards"])


def stage_server(ex: dict) -> str:
    pv = ex["proposal"]["preview"]
    out = [
        chips(
            f"plan {ex['proposal']['id']}",
            ex["proposal"]["status"],
            f"to add: {pv['to_add']}",
            f"duplicates skipped: {len(pv['skipped_duplicates'])}",
            f"similar flagged: {len(pv['similar_flagged'])}",
            f"sizes and tags checked: {len(pv.get('cards', []))} cards",
        )
    ]
    for d in pv["skipped_duplicates"]:
        out.append(f'<div class="note dup">Skipped, already in the collection: {esc(d["front"])}</div>')
    for s in pv["similar_flagged"]:
        out.append(
            f'<div class="note sim"><b>Similar to an existing card</b> (score {s["score"]}): '
            f"new “{esc(s['front'])}” · existing “{esc(s['existing_front'])}” → {esc(s['existing_back'])}</div>"
        )
    for e in ex["proposal"]["errors"]:
        out.append(f'<div class="note err">{esc(e)}</div>')
    return "".join(out)


def stage_approval(ex: dict) -> str:
    pv = ex["proposal"]["preview"]
    fronts = "".join(f"<li>{esc(f)}</li>" for f in pv["fronts"][:6])
    more = f"<li>… and {len(pv['fronts']) - 6} more</li>" if len(pv["fronts"]) > 6 else ""
    return (
        f'<div class="form"><b>Write this to Anki?</b><p>Add {pv["to_add"]} note(s) to “{esc(pv["deck"])}”</p>'
        f'<ul>{fronts}{more}</ul><div class="buttons"><span class="btn ok">Approve</span>'
        f'<span class="btn">Reject</span></div><small>asked by the server in a form inside the app, '
        f"or typed in a terminal</small></div>"
    )


def stage_written(ex: dict) -> str:
    if not ex["applied"]:
        return '<div class="note err">Not written: the plan was not approved.</div>'
    r = ex["applied"]["result"]
    head = chips(
        f"created {len(r['created'])}",
        f"mismatches after write {len(r['mismatched_after_write'])}",
        f"blue flags {r.get('flagged_blue', 0)}",
    )
    return head + "".join(
        card_box(
            w["fields"]["Front"],
            w["fields"]["Back"],
            cards.layer(w["fields"]["Front"], w["fields"]["Back"]),
            flag=w["blue_flag"],
        )
        for w in ex["written"]
    )


RENDER = [stage_material, stage_harvest, stage_plan, stage_cards, stage_server, stage_approval, stage_written]

CSS = (Path(__file__).parent / "report.css").read_text(encoding="utf-8")


def page(examples: list[dict], cost_note: str, only: tuple[str, ...] = ()) -> str:
    rows = []
    for (num, title, about), render in zip(STAGES, RENDER, strict=True):
        if only and num not in only:
            continue
        cols = "".join(f'<div class="col">{render(ex)}</div>' for ex in examples)
        rows.append(
            f'<div class="row" id="s{num}"><div class="step"><span class="n">{num}</span><b>{title}</b>'
            f"<p>{about}</p></div>{cols}</div>"
        )
    heads = "".join(f"<div>{esc(ex['title'])}</div>" for ex in examples)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>anki-librarian-mcp: from material to cards</title>
<style>{CSS}</style>
<script>window.MathJax={{tex:{{inlineMath:[["\\\\(","\\\\)"]]}}}};</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-chtml.js"></script></head><body>
<header><h1>From study material to Anki cards</h1>
<p>Two examples run through the same steps: a dense technical topic and an applied business case. The steps follow
the card-making instructions Claude uses; the search, the checks, the approval and the write are done by the
server against a practice collection. {esc(cost_note)}</p></header>
<div class="colhead"><div></div>{heads}</div><div class="grid">{"".join(rows)}</div></body></html>"""
