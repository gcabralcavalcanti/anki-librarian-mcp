"""The human's side: approval only from an interactive terminal, by typing the plan id."""

import io

from anki_librarian_mcp import cli


class TTY(io.StringIO):
    def isatty(self):
        return True


def test_approve_refuses_without_an_interactive_terminal(lib):
    plan = lib.propose_create_deck("Inbox::CLI")
    assert cli.approve(lib, plan["id"], stdin=io.StringIO("")) == 2
    assert lib.get_plan(plan["id"])["status"] == "pending"


def test_approve_needs_the_plan_id_typed(lib):
    plan = lib.propose_create_deck("Inbox::CLI")
    assert cli.approve(lib, plan["id"], stdin=TTY(), ask=lambda prompt: "yes") == 1
    assert lib.get_plan(plan["id"])["status"] == "pending"
    assert cli.approve(lib, plan["id"], stdin=TTY(), ask=lambda prompt: plan["id"]) == 0
    assert lib.get_plan(plan["id"])["status"] == "approved"


def test_example_config_loads(tmp_path):
    from pathlib import Path

    from anki_librarian_mcp import config

    s = config.load(Path(__file__).parent.parent / "anki-librarian.example.toml")
    assert s.allow_delete is False and s.allow_reschedule is False and s.approval == "elicit"
    assert s.deck_writable("Inbox::Today") and not s.deck_writable("Personal::Journal")


def test_client_configs_are_valid_and_start_the_server():
    import json
    from pathlib import Path

    folder = Path(__file__).parent.parent / "docs" / "config"
    files = sorted(set(folder.glob("*.json")) | {folder / ".mcp.json"})
    assert len(files) == 3
    for f in files:
        server = json.loads(f.read_text(encoding="utf-8"))["mcpServers"]["anki"]
        args = " ".join(server["args"])
        assert server["command"] in ("anki-librarian-mcp", "python") and args.endswith("serve") and "--config" in args
