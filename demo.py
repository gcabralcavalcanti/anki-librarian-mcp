"""Full session against the real server process (stdio) with a fake Anki: search, propose, approve, apply,
then a blocked delete. The human's approval is simulated by the client's elicitation callback.

    python demo.py     # transcript as Markdown (see output/demo_transcript.md)
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import anyio

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from fake_anki import FakeAnki, FakeAnkiHTTP  # noqa: E402
from mcp import StdioServerParameters, types  # noqa: E402
from mcp.client import Client  # noqa: E402


def show(title, obj):
    print(f"\n### {title}\n```json\n{json.dumps(obj, ensure_ascii=False, indent=1)}\n```")


async def session(url: str, state: Path):
    cfg = state / "anki-librarian.toml"
    cfg.write_text(
        f'anki_url = "{url}"\nwritable_decks = ["Economics::*", "Inbox::*"]\napproval = "elicit"\n'
        f'state_dir = "{(state / "state").as_posix()}"\n[taxonomy]\n'
        'roots = ["Economics", "Humanities", "Exact", "Biology", "Specific"]\n',
        encoding="utf-8",
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "anki_librarian_mcp", "--config", str(cfg), "serve"],
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )

    async def human(context, req):
        print(f"\n### Elicitation shown to the human\n```\n{req.message}\n```\n-> the human clicks **approve**")
        return types.ElicitResult(action="accept", content={"approve": True})

    async with Client(params, mode="legacy", elicitation_callback=human) as c:
        call = lambda name, args: c.call_tool(name, args)  # noqa: E731
        r = await call("find_notes", {"query": "taylor"})
        show("find_notes(query='taylor')", json.loads(r.content[0].text))
        notes = [
            {
                "front": "What does the Taylor rule set?",
                "back": "The policy rate, from the inflation and output gaps",
                "tags": ["Economics::Macro::MonetaryPolicy"],
            },
            {
                "front": "What does the Taylor rule target?",
                "back": "The policy rate",
                "tags": ["Economics::Macro::MonetaryPolicy"],
            },
            {
                "front": "Taylor principle",
                "back": "The policy rate must move more than one-for-one with inflation",
                "tags": ["Economics::Macro::MonetaryPolicy"],
            },
            {"front": "Okun law", "back": "Output gap and unemployment move together", "tags": ["economics::macro"]},
        ]
        r = await call("propose_add_notes", {"deck": "Economics::Macro", "notes": notes})
        show("propose_add_notes (4 notes, one with a bad tag)", json.loads(r.content[0].text))
        r = await call("propose_add_notes", {"deck": "Economics::Macro", "notes": notes[:3]})
        plan = json.loads(r.content[0].text)
        show("propose_add_notes (bad note removed)", plan)
        r = await call("apply_plan", {"plan_id": plan["id"]})
        show("apply_plan", json.loads(r.content[0].text))
        r = await call("propose_delete_notes", {"note_ids": plan_ids(r)})
        print(f"\n### propose_delete_notes\n```\nis_error={r.is_error}: {r.content[0].text}\n```")


def plan_ids(result):
    return json.loads(result.content[0].text)["result"]["created"][:1] or [1]


def main():
    fake = FakeAnki()
    fake.seed(
        "Economics::Macro",
        "What does the Taylor rule set?",
        "The policy rate, from the inflation and output gaps",
        tags=["Economics::Macro::MonetaryPolicy"],
    )
    with FakeAnkiHTTP(fake) as srv, tempfile.TemporaryDirectory() as tmp:
        print("# anki-librarian-mcp - demo session (fake Anki, real server process over stdio)")
        anyio.run(session, srv.url, Path(tmp))
        audit = (Path(tmp) / "state" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        print("\n### Audit log\n```")
        for line in audit:
            e = json.loads(line)
            print(json.dumps({k: v for k, v in e.items() if k != "ts"}, ensure_ascii=False))
        print("```")
        print(f"\nActions that reached the (fake) Anki: {sorted(set(fake.received))}")


if __name__ == "__main__":
    main()
