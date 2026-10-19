"""Command line: run the server, and the human's side of the approval (approve / reject / plans / audit)."""

from __future__ import annotations

import argparse
import json
import sys

from . import config
from .connect import AnkiError, Blocked
from .service import Librarian, PlanError


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def approve(lib: Librarian, pid: str, stdin=sys.stdin, ask=input) -> int:
    """Approval must be typed by a person: an agent's shell has no interactive terminal."""
    if not stdin.isatty():
        print("REFUSED: approve must be typed by a human in an interactive terminal.", file=sys.stderr)
        return 2
    plan = lib.get_plan(pid)
    _print(lib.view(plan))
    if ask(f"Type the plan id to approve it ({pid}): ").strip() != pid:
        print("Not approved.")
        return 1
    _print(lib.approve(pid, via="cli"))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="anki-librarian-mcp", description="Anki MCP server with a write lock.")
    ap.add_argument("--config", help="TOML settings (default: $ANKI_LIBRARIAN_CONFIG or ./anki-librarian.toml)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="run the MCP server on stdio (default)")
    sub.add_parser("check", help="show the settings and ping AnkiConnect")
    p = sub.add_parser("plans", help="list plans")
    p.add_argument("--status")
    p = sub.add_parser("show", help="show one plan")
    p.add_argument("plan")
    p = sub.add_parser("approve", help="approve a pending plan (interactive terminal only)")
    p.add_argument("plan")
    p = sub.add_parser("reject", help="reject a plan")
    p.add_argument("plan")
    p.add_argument("reason", nargs="?", default="")
    p = sub.add_parser("audit", help="last audit events")
    p.add_argument("-n", type=int, default=20)
    a = ap.parse_args(argv)
    settings = config.load(a.config)
    lib = Librarian(settings)
    try:
        if a.cmd in (None, "serve"):
            from .server import build_server

            build_server(lib).run("stdio")
            return 0
        if a.cmd == "check":
            _print(
                {
                    "anki_url": settings.anki_url,
                    "writable_decks": settings.writable_decks,
                    "allow_delete": settings.allow_delete,
                    "allow_reschedule": settings.allow_reschedule,
                    "approval": settings.approval,
                    "state_dir": str(settings.state_dir),
                    "taxonomy_roots": settings.taxonomy.roots,
                    "ankiconnect_version": lib.anki.call("version"),
                }
            )
        elif a.cmd == "plans":
            _print([lib.view(p) for p in lib.plans.list(a.status)])
        elif a.cmd == "show":
            _print(lib.get_plan(a.plan))
        elif a.cmd == "approve":
            return approve(lib, a.plan)
        elif a.cmd == "reject":
            _print(lib.reject(a.plan, via="cli", reason=a.reason))
        elif a.cmd == "audit":
            for e in lib.audit.tail(a.n):
                print(json.dumps(e, ensure_ascii=False))
    except (PlanError, Blocked, AnkiError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
