"""MCP server. Reads are plain tools; writes are propose_* (a dry-run plan) then apply_plan, which asks the
human through MCP elicitation, or tells them to approve in a terminal when the client cannot ask.
"""

from __future__ import annotations

from typing import Annotated

from mcp import types
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from .connect import AnkiError, Blocked
from .service import Librarian, PlanError

READ_ONLY = types.ToolAnnotations(readOnlyHint=True, openWorldHint=False)
PROPOSE = types.ToolAnnotations(readOnlyHint=True, openWorldHint=False)  # a plan writes nothing to Anki
APPLY = types.ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False)

INSTRUCTIONS = """Anki through a locked door. Reads are free. To change the collection: call a propose_* tool,
show the returned preview to the user (duplicates skipped, similar notes, tag errors), then call apply_plan.
The user approves every plan; never claim a change was made before apply_plan returns status "applied".
Deleting notes and rescheduling are off unless the user switched them on in the config. Flag 1 (red) is the
user's; never try to set it. Search before creating: the server already skips duplicates, but say which ones."""


class BasicNote(BaseModel):
    front: str
    back: str = ""
    tags: list[str] = Field(default_factory=list, description="hierarchical tags, e.g. Economics::Macro::Inflation")


class ClozeNote(BaseModel):
    text: str = Field(description="cloze text, e.g. 'The capital of France is {{c1::Paris}}'")
    back_extra: str = ""
    tags: list[str] = Field(default_factory=list)


class Approval(BaseModel):
    approve: bool = Field(description="Write this plan to Anki?")


def _summary(plan: dict) -> str:
    p = plan["preview"]
    lines = [f"Plan {plan['id']} ({plan['kind']})"]
    if "to_add" in p:
        lines.append(f"Add {p['to_add']} note(s) to '{p['deck']}'" + ("" if p["deck_exists"] else " (new deck)"))
        lines += [f"  + {f}" for f in p["fronts"][:15]]
        if p["skipped_duplicates"]:
            lines.append(f"Skipped as duplicates: {len(p['skipped_duplicates'])}")
        if p["similar_flagged"]:
            lines.append(f"Similar to existing notes: {len(p['similar_flagged'])} (check before approving)")
    elif "diff" in p:
        lines.append(f"Update note {p['note_id']}: {p['diff']}")
    else:
        lines.append(str({k: v for k, v in p.items()}))
    return "\n".join(lines)


def build_server(lib: Librarian) -> MCPServer:
    app = MCPServer("anki-librarian", instructions=INSTRUCTIONS)

    def _safe(fn):
        """Run a tool body; a refusal comes back to the model as a readable tool error (and, if the lock
        refused it, a line in the audit log), never as a crash."""
        try:
            return fn()
        except Blocked as e:
            lib.audit.log("blocked", error=str(e))
            raise ToolError(str(e)) from e
        except (PlanError, AnkiError) as e:
            raise ToolError(str(e)) from e

    @app.tool(annotations=READ_ONLY)
    def list_decks() -> dict:
        """List all decks and which of them this server may write to."""
        return _safe(lambda: lib.list_decks())

    @app.tool(annotations=READ_ONLY)
    def find_notes(query: str, limit: int = 20) -> dict:
        """Search notes with Anki search syntax (e.g. 'deck:Economics tag:Economics::Macro inflation').
        Returns note ids, model, decks, tags and field excerpts."""
        return _safe(lambda: lib.find_notes(query, limit))

    @app.tool(annotations=READ_ONLY)
    def get_notes(note_ids: list[int]) -> list[dict]:
        """Full fields and tags of up to 100 notes."""
        return _safe(lambda: lib.get_notes(note_ids))

    @app.tool(annotations=PROPOSE)
    def propose_add_notes(deck: str, notes: Annotated[list[BasicNote], Field(min_length=1)]) -> dict:
        """Dry run for adding basic (front/back) notes, one or many. Searches the collection first:
        exact duplicates are skipped, 'same front, different back' is left for the user, similar fronts are
        flagged, tags are checked against the taxonomy. Nothing is written: call apply_plan after the user sees it."""
        return _safe(lambda: lib.propose_add_notes(deck, [n.model_dump() for n in notes]))

    @app.tool(annotations=PROPOSE)
    def propose_add_cloze_notes(deck: str, notes: Annotated[list[ClozeNote], Field(min_length=1)]) -> dict:
        """Dry run for adding cloze notes (one or many); cloze syntax is validated for the whole batch."""
        return _safe(lambda: lib.propose_add_cloze_notes(deck, [n.model_dump() for n in notes]))

    @app.tool(annotations=PROPOSE)
    def propose_update_note(note_id: int, fields: dict[str, str] | None = None, tags: list[str] | None = None) -> dict:
        """Dry run for editing one note's fields and/or replacing its tags. Shows a before/after diff.
        If the note changes in Anki before apply_plan, the plan is refused (no stale writes)."""
        return _safe(lambda: lib.propose_update_note(note_id, fields, tags))

    @app.tool(annotations=PROPOSE)
    def propose_create_deck(name: str) -> dict:
        """Dry run for creating a deck (only inside the writable decks)."""
        return _safe(lambda: lib.propose_create_deck(name))

    @app.tool(annotations=PROPOSE)
    def propose_delete_notes(note_ids: Annotated[list[int], Field(min_length=1, max_length=50)]) -> dict:
        """Dry run for deleting notes (and their review history). Off unless the user enabled it in the
        config; at most 50 ids, no delete-by-query."""
        return _safe(lambda: lib.propose_delete_notes(note_ids))

    @app.tool(annotations=PROPOSE)
    def propose_set_due_date(card_ids: list[int], days: str) -> dict:
        """Dry run for rescheduling cards (Anki's set due date, e.g. days='0' or '1-3'). Off unless enabled."""
        return _safe(lambda: lib.propose_set_due_date(card_ids, days))

    @app.tool(annotations=PROPOSE)
    def propose_flag_cards(card_ids: list[int], color: int) -> dict:
        """Dry run for flagging cards with an agent color (default: 4 blue, or 0 to clear one the agent set).
        Cards carrying a flag the user set are skipped, never overwritten."""
        return _safe(lambda: lib.propose_flag_cards(card_ids, color))

    @app.tool(annotations=READ_ONLY)
    def list_plans(status: str | None = None) -> list[dict]:
        """Plans and their status (pending, approved, applied, rejected, expired, invalid, failed)."""
        return _safe(lambda: [lib.view(p) for p in lib.plans.list(status)])

    @app.tool(annotations=APPLY)
    async def apply_plan(plan_id: str, ctx: Context) -> dict:
        """Write an approved plan to Anki and read it back to confirm. If the plan is still pending, the server
        asks the user to approve it (the model cannot approve on the user's behalf)."""
        plan = _safe(lambda: lib.get_plan(plan_id))
        if plan["status"] == "pending" and lib.s.approval == "elicit":
            caps = getattr(ctx, "client_capabilities", None)
            if caps is not None and getattr(caps, "elicitation", None):
                try:
                    res = await ctx.elicit(_summary(plan) + "\n\nWrite this to Anki?", Approval)
                except Exception:
                    res = None
                if res is not None:
                    if res.action == "accept" and res.data and res.data.approve:
                        lib.approve(plan_id, via="mcp elicitation")
                    else:
                        return lib.reject(plan_id, via="mcp elicitation", reason=f"user answered {res.action}")
            if lib.get_plan(plan_id)["status"] == "pending":
                return lib.view(plan) | {
                    "next": "this client cannot ask the user; the user approves in a "
                    f"terminal: anki-librarian-mcp approve {plan_id}, then call apply_plan"
                }
        return _safe(lambda: lib.apply(plan_id))

    @app.tool(annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def reject_plan(plan_id: str, reason: str = "") -> dict:
        """Discard a plan the user does not want."""
        return _safe(lambda: lib.reject(plan_id, via="model on the user's request", reason=reason))

    return app
