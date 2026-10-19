"""The MCP server end to end: a real MCP client session (in memory) against the fake collection."""
import json

import anyio
import pytest

from mcp import types
from mcp.client import Client

from anki_librarian_mcp.server import build_server
from conftest import librarian, make_settings

TAG = ["Economics::Macro::MonetaryPolicy"]
NOTE = {"front": "Taylor principle", "back": "Rates move more than one-for-one with inflation", "tags": TAG}


def payload(result):
    assert not result.is_error, result.content
    return json.loads(result.content[0].text)


def run(lib, script, answer=None):
    """Run `script(client)` in a client session. `answer`: what the human answers in the elicitation form
    (None = the client does not support elicitation)."""
    async def elicit(context, params):
        return types.ElicitResult(action="accept", content={"approve": answer}) if answer is not None else \
            types.ElicitResult(action="decline")

    async def main():
        kw = {"elicitation_callback": elicit} if answer is not None else {}
        async with Client(build_server(lib), mode="legacy", **kw) as c:
            return await script(c)
    return anyio.run(main)


def test_tools_and_annotations(tmp_path, fake):
    lib = librarian(make_settings(tmp_path, approval="elicit"), fake)

    async def script(c):
        return {t.name: t.annotations for t in (await c.list_tools()).tools}
    tools = run(lib, script)
    assert {"list_decks", "find_notes", "propose_add_notes", "propose_add_cloze_notes", "propose_update_note",
            "propose_delete_notes", "apply_plan", "reject_plan"} <= set(tools)
    assert tools["find_notes"].read_only_hint and tools["propose_add_notes"].read_only_hint
    assert tools["apply_plan"].destructive_hint


def test_human_approves_through_elicitation(tmp_path, fake):
    lib = librarian(make_settings(tmp_path, approval="elicit"), fake)
    before = len(fake.notes)

    async def script(c):
        plan = payload(await c.call_tool("propose_add_notes", {"deck": "Economics::Macro", "notes": [NOTE]}))
        return payload(await c.call_tool("apply_plan", {"plan_id": plan["id"]}))
    res = run(lib, script, answer=True)
    assert res["status"] == "applied" and len(fake.notes) == before + 1
    assert lib.audit.tail()[-2]["via"] == "mcp elicitation"


def test_human_declines_through_elicitation(tmp_path, fake):
    lib = librarian(make_settings(tmp_path, approval="elicit"), fake)
    before = len(fake.notes)

    async def script(c):
        plan = payload(await c.call_tool("propose_add_notes", {"deck": "Economics::Macro", "notes": [NOTE]}))
        return payload(await c.call_tool("apply_plan", {"plan_id": plan["id"]}))
    res = run(lib, script, answer=False)
    assert res["status"] == "rejected" and len(fake.notes) == before


def test_without_elicitation_the_model_cannot_approve(tmp_path, fake):
    lib = librarian(make_settings(tmp_path, approval="elicit"), fake)
    before = len(fake.notes)

    async def script(c):
        plan = payload(await c.call_tool("propose_add_notes", {"deck": "Economics::Macro", "notes": [NOTE]}))
        first = payload(await c.call_tool("apply_plan", {"plan_id": plan["id"]}))
        second = payload(await c.call_tool("apply_plan", {"plan_id": plan["id"]}))
        return first, second
    first, second = run(lib, script)
    assert first["status"] == second["status"] == "pending"
    assert "anki-librarian-mcp approve" in first["next"]
    assert len(fake.notes) == before


def test_blocked_action_comes_back_as_a_tool_error(tmp_path, fake):
    lib = librarian(make_settings(tmp_path), fake)

    async def script(c):
        return await c.call_tool("propose_delete_notes", {"note_ids": [next(iter(fake.notes))]})
    res = run(lib, script)
    assert res.is_error and "allow_delete" in res.content[0].text
    assert "deleteNotes" not in fake.received
    assert lib.audit.tail()[-1]["event"] == "blocked"
