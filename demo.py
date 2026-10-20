"""Run the whole thing on a practice collection (nothing touches a real Anki):

1. output/simulation.html: two examples (econometrics notes, a business case) go from material to cards,
   step by step. The model's answers were recorded on a live run and replay without a key.
2. output/demo_transcript.md: the real server process, started the way Claude Desktop or Claude Code starts it,
   in one session: search, a refused plan, a corrected plan, your approval, the write, a blocked delete.

    python demo.py             # writes both files and opens the page
    python demo.py --no-open   # same, without opening a browser
    python demo.py --live      # call Claude for any answer not recorded yet (needs ANTHROPIC_API_KEY)
"""

import io
import json
import os
import re
import sys
import tempfile
import webbrowser
from contextlib import redirect_stdout
from pathlib import Path

import anyio

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from fake_anki import FakeAnki, FakeAnkiHTTP  # noqa: E402
from mcp import StdioServerParameters, types  # noqa: E402
from mcp.client import Client  # noqa: E402

from anki_librarian_mcp import pipeline, report  # noqa: E402
from anki_librarian_mcp.config import Settings, Taxonomy  # noqa: E402
from anki_librarian_mcp.connect import AnkiConnect  # noqa: E402
from anki_librarian_mcp.llm import LLM  # noqa: E402
from anki_librarian_mcp.service import Librarian  # noqa: E402

OUT = ROOT / "output"
ROOTS = ["Economics", "Humanities", "Exact.Sciences", "Biological.Sciences", "Specifics"]
EXAMPLES = [
    ("econometrics", "Dense topic: heteroskedasticity (econometrics notes)", "Statistics"),
    ("business", "Applied case: unit economics of a subscription", "Business"),
]
MONETARY = ["Economics::Macroeconomics::Applied::Monetary.Economics"]


def practice_collection() -> FakeAnki:
    fake = FakeAnki()
    data = json.loads((ROOT / "data" / "collection.json").read_text(encoding="utf-8"))
    for n in data["notes"]:
        fake.seed(n["deck"], n["front"], n["back"], tags=n["tags"])
    return fake


def simulation(live: bool) -> tuple[list[dict], str]:
    llm = LLM(ROOT / "data" / "recorded", live=live)
    fake = practice_collection()
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            writable_decks=["Statistics*", "Business*"],
            approval="cli",
            state_dir=Path(tmp),
            taxonomy=Taxonomy(roots=ROOTS, operational=["TEMP", "Update"]),
        )
        lib = Librarian(settings, AnkiConnect(transport=fake, sleep=lambda s: None))
        examples = []
        for name, title, deck in EXAMPLES:
            material = (ROOT / "data" / "materials" / f"{name}.md").read_text(encoding="utf-8")
            ex = pipeline.run(llm, lib, name, material, deck)
            ex["title"] = title
            examples.append(ex)
    if llm.calls:
        note = f"This run called Claude {llm.calls} times (about US$ {llm.cost(llm.tokens_in, llm.tokens_out):.4f})."
    else:
        note = "The model's answers were recorded once and replay here, so this runs without an API key."
    return examples, note


async def session(url: str, state: Path, show) -> None:
    cfg = state / "anki-librarian.toml"
    cfg.write_text(
        f'anki_url = "{url}"\nwritable_decks = ["Economics::*", "Inbox::*"]\napproval = "elicit"\n'
        f'state_dir = "{(state / "state").as_posix()}"\n[taxonomy]\nroots = {json.dumps(ROOTS)}\n',
        encoding="utf-8",
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "anki_librarian_mcp", "--config", str(cfg), "serve"],
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )

    async def human(context, req):
        show("Approval form shown to you", req.message, fence="")
        return types.ElicitResult(action="accept", content={"approve": True})

    notes = [
        {
            "front": "Macroeconomics: Taylor rule <br><br> What does the Taylor rule set?",
            "back": "The policy rate, from the inflation gap and the output gap.",
            "tags": MONETARY,
        },
        {
            "front": "Macroeconomics: Taylor rule <br><br> What does the Taylor rule target?",
            "back": "The policy rate.",
            "tags": MONETARY,
        },
        {
            "front": "Macroeconomics: Taylor rule <br><br> What is the Taylor principle?",
            "back": "The policy rate must move more than one-for-one with inflation.",
            "tags": MONETARY,
        },
        {
            "front": "Macroeconomics: Okun law <br><br> How do output and unemployment move together?",
            "back": "When output falls below potential, unemployment rises.",
            "tags": ["economics::macro"],
        },
    ]
    async with Client(params, mode="legacy", elicitation_callback=human) as c:
        r = await c.call_tool("find_notes", {"query": "taylor"})
        show("find_notes('taylor')", json.loads(r.content[0].text))
        r = await c.call_tool("propose_add_notes", {"deck": "Economics::Macro", "notes": notes})
        show("propose_add_notes: 4 cards, one with a tag outside the taxonomy", json.loads(r.content[0].text))
        r = await c.call_tool("propose_add_notes", {"deck": "Economics::Macro", "notes": notes[:3]})
        plan = json.loads(r.content[0].text)
        show("propose_add_notes: corrected", plan)
        r = await c.call_tool("apply_plan", {"plan_id": plan["id"]})
        applied = json.loads(r.content[0].text)
        show("apply_plan", applied)
        r = await c.call_tool("propose_delete_notes", {"note_ids": applied["result"]["created"][:1] or [1]})
        show("propose_delete_notes", f"is_error={r.is_error}: {r.content[0].text}", fence="")


def transcript() -> str:
    out = io.StringIO()

    def show(title, obj, fence="json"):
        body = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=1)
        out.write(f"\n### {title}\n```{fence}\n{body}\n```\n")

    fake = FakeAnki()
    fake.seed(
        "Economics::Macro",
        "Macroeconomics: Taylor rule <br><br> What does the Taylor rule set?",
        "The policy rate, from the inflation gap and the output gap.",
        tags=MONETARY,
    )
    with FakeAnkiHTTP(fake) as srv, tempfile.TemporaryDirectory() as tmp:
        out.write("# Demo session: the real server, started the way Claude Desktop starts it, with a practice Anki\n")
        with redirect_stdout(io.StringIO()):
            anyio.run(session, srv.url, Path(tmp), show)
        audit = (Path(tmp) / "state" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        events = [json.dumps({k: v for k, v in json.loads(line).items() if k != "ts"}) for line in audit]
        out.write("\n### Audit log\n```\n" + "\n".join(events) + "\n```\n")
        out.write(f"\nActions that reached the practice Anki: {sorted(set(fake.received))}\n")
    return out.getvalue()


def stable(text: str) -> str:
    """Same output on every run: plan ids and timestamps change each time, so they are numbered and blanked."""
    ids: dict[str, str] = {}
    text = re.sub(r"\bp-[0-9a-f]{6}\b", lambda m: ids.setdefault(m.group(0), f"p-demo{len(ids) + 1}"), text)
    return re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", "2026-01-01T00:00:00+00:00", text)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    OUT.mkdir(exist_ok=True)
    examples, note = simulation("--live" in argv)
    page = OUT / "simulation.html"
    page.write_text(stable(report.page(examples, note)), encoding="utf-8")
    (OUT / "demo_transcript.md").write_text(stable(transcript()), encoding="utf-8")
    for ex in examples:
        written = len(ex["applied"]["result"]["created"]) if ex["applied"] else 0
        print(f"{ex['title']}: {len(ex['cards'])} cards written by the model, {written} added after approval")
    print(f"{note}\nPage: {page}\nServer session: {OUT / 'demo_transcript.md'}")
    if "--no-open" not in argv:
        webbrowser.open(page.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
