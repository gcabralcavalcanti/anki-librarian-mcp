"""The demo replays without a key, and the skills are served as prompts."""

import sys
from pathlib import Path

import anyio
from conftest import librarian, make_settings
from mcp.client import Client

from anki_librarian_mcp import report
from anki_librarian_mcp.server import build_server

ROOT = Path(__file__).resolve().parent.parent


def test_simulation_replays_from_recordings_and_renders():
    sys.path.insert(0, str(ROOT))
    import demo

    examples, note = demo.simulation(live=False)
    assert note.startswith("Replayed")
    for ex in examples:
        verdicts = {v["verdict"] for v in ex["plan"]["verdicts"]}
        assert "GAP" in verdicts and "ALREADY HAVE" in verdicts  # the search found cards the collection already had
        assert ex["applied"]["result"]["created"] and not ex["applied"]["result"]["mismatched_after_write"]
        assert all(not c["weight"]["problems"] for c in ex["cards"])
    assert any(ex["proposal"]["preview"]["similar_flagged"] for ex in examples)
    page = report.page(examples, note)
    assert page.count('class="row"') == 7 and "Your approval" in page


def test_skills_are_served_as_prompts(tmp_path, fake):
    lib = librarian(make_settings(tmp_path), fake)

    async def main():
        async with Client(build_server(lib), mode="legacy") as c:
            names = [p.name for p in (await c.list_prompts()).prompts]
            text = (await c.get_prompt("make_cards", {"material": "NOTES"})).messages[0].content.text
            return names, text

    names, text = anyio.run(main)
    assert names == ["make_cards", "harvest", "plan_deck", "generate_cards", "tag_cards", "radar"]
    assert "# Harvest" in text and "# Generator" in text and text.endswith("NOTES")
