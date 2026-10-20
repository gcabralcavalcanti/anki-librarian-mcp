"""Tool logic, independent of MCP. Every write is a plan first (reconciled with the collection, tags and decks
checked), applied only after the human approves, and read back afterwards.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from . import cards, checks, media
from .config import Settings
from .connect import AnkiConnect, Blocked
from .plans import Audit, PlanStore
from .retrieval import CollectionIndex


class PlanError(Exception):
    """A plan cannot move to the requested state; the message says why and what to do."""


def _excerpt(text: str, n: int = 90) -> str:
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = " ".join(t.split())
    return t if len(t) <= n else t[: n - 1] + "…"


class Librarian:
    def __init__(self, settings: Settings, anki: AnkiConnect | None = None):
        self.s = settings
        self.anki = anki or AnkiConnect(
            settings.anki_url,
            timeout=settings.timeout_s,
            switches={"allow_delete": settings.allow_delete, "allow_reschedule": settings.allow_reschedule},
        )
        self.plans = PlanStore(settings.state_dir, settings.plan_ttl_minutes)
        self.audit = Audit(settings.state_dir)
        self.index = CollectionIndex(self.anki, settings.state_dir)
        self.fetch = media.http_get

    # ================================================================== reads (always free)
    def list_decks(self) -> dict:
        decks = sorted(self.anki.call("deckNames"))
        return {
            "decks": decks,
            "writable": [d for d in decks if self.s.deck_writable(d)],
            "writable_patterns": self.s.writable_decks,
        }

    def find_notes(self, query: str, limit: int = 20) -> dict:
        ids = self.anki.call("findNotes", {"query": query})
        notes = self._notes(ids[: max(1, min(limit, 100))])
        return {"query": query, "total": len(ids), "shown": len(notes), "notes": notes}

    def get_notes(self, note_ids: list[int]) -> list[dict]:
        return self._notes(note_ids[:100], full=True)

    def _notes(self, ids: list[int], full: bool = False) -> list[dict]:
        if not ids:
            return []
        info = self.anki.call("notesInfo", {"notes": ids})
        card_ids = [c for n in info for c in n.get("cards", [])]
        decks = (
            {c["cardId"]: c["deckName"] for c in self.anki.call("cardsInfo", {"cards": card_ids})} if card_ids else {}
        )
        out = []
        for n in info:
            fields = {k: v["value"] for k, v in sorted(n["fields"].items(), key=lambda kv: kv[1]["order"])}
            out.append(
                {
                    "note_id": n["noteId"],
                    "model": n["modelName"],
                    "tags": n["tags"],
                    "decks": sorted({decks[c] for c in n.get("cards", []) if c in decks}),
                    "fields": fields if full else {k: _excerpt(v) for k, v in fields.items()},
                }
            )
        return out

    # ================================================================== proposals (dry runs)
    def propose_add_notes(self, deck: str, notes: list[dict]) -> dict:
        """notes: [{front, back, tags?, image?: {path | url, credit?}}] -> plan. Searches the collection first."""
        rows = [
            {
                "fields": {"Front": n["front"], "Back": n.get("back", "")},
                "tags": n.get("tags", []),
                "image": n.get("image"),
            }
            for n in notes
        ]
        return self._propose_add("add_notes", deck, self.s.basic_model, rows, [])

    def propose_add_cloze_notes(self, deck: str, notes: list[dict]) -> dict:
        """notes: [{text, back_extra?, tags?}]; cloze syntax is checked for the whole batch first."""
        rows, errors = [], []
        for i, n in enumerate(notes):
            errors += [f"note {i + 1}: {e}" for e in checks.cloze_errors(n["text"])]
            rows.append(
                {"fields": {"Text": n["text"], "Back Extra": n.get("back_extra", "")}, "tags": n.get("tags", [])}
            )
        return self._propose_add("add_cloze_notes", deck, self.s.cloze_model, rows, errors)

    def _card_checks(self, i: int, row: dict, errors: list, warnings: list) -> dict:
        front, back = row["fields"]["Front"], row["fields"]["Back"]
        w = cards.weight(front, back)
        found = list(w["problems"])
        for p in cards.front_problems(front, row["tags"]):
            if "missing theme" in p:
                warnings.append(f"note {i}: {p}")
            else:
                found.append(p)
        (errors if self.s.card_rules == "enforce" else warnings).extend(f"note {i}: {p}" for p in found)
        return {"note": i, "layer": w["layer"], "weight": w["pc"], "chars": w["chars"]}

    def _propose_add(self, kind: str, deck: str, model: str, rows: list[dict], errors: list[str]) -> dict:
        if not rows:
            raise PlanError("no notes given")
        if len(rows) > self.s.max_notes_per_plan:
            raise PlanError(f"{len(rows)} notes: the limit is {self.s.max_notes_per_plan} per plan; split the batch")
        if not self.s.deck_writable(deck):
            errors.append(f"deck '{deck}' is outside the writable decks {self.s.writable_decks}")
        warnings, card_report, media_steps = [], [], []
        for i, r in enumerate(rows, 1):
            errors += [f"note {i}: {e}" for e in checks.tag_errors(r["tags"], self.s.taxonomy)]
            if kind == "add_notes" and self.s.card_rules != "off":
                card_report.append(self._card_checks(i, r, errors, warnings))
            if r.get("image"):
                try:
                    name, step = media.prepare(r["image"], self.s.state_dir, r["fields"]["Front"], self.fetch)
                except media.MediaError as e:
                    errors.append(f"note {i}: image: {e}")
                else:
                    media_steps.append(step)
                    r["fields"]["Back"] += media.html(name, r["image"].get("credit", ""))
        self.index.refresh()
        first = next(iter(rows[0]["fields"]))
        to_add, duplicates, conflicts, similar, seen = [], [], [], [], {}
        for i, r in enumerate(rows, 1):
            front, back = r["fields"][first], list(r["fields"].values())[1]
            key = checks.normalize(front)
            if key in seen:
                duplicates.append(
                    {"note": i, "front": _excerpt(front), "duplicate_of": f"note {seen[key]} in this batch"}
                )
                continue
            seen[key] = i
            match = self._reconcile(front, back)
            if match["kind"] == "duplicate":
                duplicates.append({"note": i, "front": _excerpt(front), "duplicate_of": match["note_id"]})
                continue
            if match["kind"] == "conflict":
                conflicts.append(
                    {
                        "note": i,
                        "front": _excerpt(front),
                        "existing": match["note_id"],
                        "existing_back": _excerpt(match["back"], 160),
                        "why": "same front, different back: decide by hand which one stays",
                    }
                )
                continue
            if match["kind"] == "similar":
                similar.append(
                    {
                        "note": i,
                        "front": _excerpt(front),
                        "similar_to": match["note_id"],
                        "existing_front": _excerpt(match["front"]),
                        "existing_back": _excerpt(match["back"], 160),
                        "score": match["score"],
                    }
                )
            to_add.append(
                {
                    "deckName": deck,
                    "modelName": model,
                    "fields": r["fields"],
                    "tags": r["tags"],
                    "options": {"allowDuplicate": False},
                }
            )
        steps = []
        deck_exists = deck in self.anki.call("deckNames")
        if to_add and not deck_exists:
            steps.append({"action": "createDeck", "params": {"deck": deck}})
        if to_add:
            steps += media_steps
            steps.append({"action": "addNotes", "params": {"notes": to_add}})
        preview = {
            "deck": deck,
            "deck_exists": deck_exists,
            "model": model,
            "to_add": len(to_add),
            "fronts": [_excerpt(n["fields"][first]) for n in to_add],
            "skipped_duplicates": duplicates,
            "skipped_conflicts": conflicts,
            "similar_flagged": similar,
            "images": len(media_steps),
            "cards": card_report,
            "warnings": warnings,
        }
        if not to_add and not errors:
            errors.append("nothing to add: every note already exists")
        return self._new_plan(kind, steps, preview, errors)

    def _reconcile(self, front: str, back: str) -> dict:
        """Search the collection BEFORE creating: exact duplicate, conflict, similar, or new.

        Two routes, united: Anki's own search for each key word of the front, and the similarity index over
        the whole collection (front and back), which also finds reworded cards.
        """
        words = checks.keywords(front, 3) or checks.normalize(front).split()[:3]
        ids: list[int] = []
        for w in words:
            ids += [i for i in self.anki.call("findNotes", {"query": f"w:{w.replace('_', '')}"}) if i not in ids]
        candidates = {}
        for n in self.anki.call("notesInfo", {"notes": ids[:50]}) if ids else []:
            vals = [v["value"] for _, v in sorted(n["fields"].items(), key=lambda kv: kv[1]["order"])]
            candidates[n["noteId"]] = (vals[0], vals[1] if len(vals) > 1 else "", 0.0)
        for hit in self.index.search(front, back, k=5):
            old = candidates.get(hit["note_id"], (hit["front"], hit["back"], 0.0))
            candidates[hit["note_id"]] = (old[0], old[1], hit["score"])
        best = {"kind": "new", "score": 0.0}
        for nid, (ofront, oback, cosine) in candidates.items():
            if checks.normalize(ofront) == checks.normalize(front):
                same_back = checks.normalize(oback) == checks.normalize(back)
                kind = "duplicate" if same_back or not back else "conflict"
                return {"kind": kind, "note_id": nid, "front": ofront, "back": oback}
            ratio = checks.similarity(ofront, front)
            score = max(
                ratio if ratio >= self.s.similar_threshold else 0.0,
                cosine if cosine >= self.s.retrieval_threshold else 0.0,
            )
            if score > best["score"]:
                best = {"kind": "similar", "note_id": nid, "front": ofront, "back": oback, "score": round(score, 2)}
        return best

    def propose_attach_image(self, note_id: int, image: dict, field: str = "Back") -> dict:
        """Add a picture (local path or URL, with an optional credit line) to an existing note's field."""
        info = self.anki.call("notesInfo", {"notes": [note_id]})
        if not info or not info[0]:
            raise PlanError(f"note {note_id} not found")
        note = info[0]
        if field not in note["fields"]:
            raise PlanError(f"field {field!r} not in this note: {sorted(note['fields'])}")
        errors = self._scope_errors(note.get("cards", []))
        try:
            name, step = media.prepare(image, self.s.state_dir, note["fields"][field]["value"], self.fetch)
        except media.MediaError as e:
            raise PlanError(f"image: {e}") from e
        value = note["fields"][field]["value"] + media.html(name, image.get("credit", ""))
        steps = [step, {"action": "updateNoteFields", "params": {"note": {"id": note_id, "fields": {field: value}}}}]
        preview = {
            "note_id": note_id,
            "field": field,
            "file": name,
            "credit": image.get("credit", ""),
            "mod_at_preview": note.get("mod"),
        }
        return self._new_plan("attach_image", steps, preview, errors)

    def propose_update_note(self, note_id: int, fields: dict | None = None, tags: list[str] | None = None) -> dict:
        if not fields and tags is None:
            raise PlanError("nothing to change: give fields and/or tags")
        info = self.anki.call("notesInfo", {"notes": [note_id]})
        if not info or not info[0]:
            raise PlanError(f"note {note_id} not found")
        note = info[0]
        errors = self._scope_errors(note.get("cards", []))
        current = {k: v["value"] for k, v in note["fields"].items()}
        unknown = [k for k in (fields or {}) if k not in current]
        if unknown:
            errors.append(f"unknown field(s) {unknown}; this note has {sorted(current)}")
        steps, diff = [], {}
        if fields:
            changed = {k: v for k, v in fields.items() if k in current and v != current[k]}
            diff["fields"] = {
                k: {"before": _excerpt(current[k], 200), "after": _excerpt(v, 200)} for k, v in changed.items()
            }
            if changed:
                steps.append({"action": "updateNoteFields", "params": {"note": {"id": note_id, "fields": changed}}})
        if tags is not None:
            errors += checks.tag_errors(tags, self.s.taxonomy)
            if sorted(tags) != sorted(note["tags"]):
                diff["tags"] = {"before": note["tags"], "after": tags}
                steps.append({"action": "updateNoteTags", "params": {"note": note_id, "tags": tags}})
        if not steps and not errors:
            errors.append("nothing changes: the note already looks like this")
        preview = {"note_id": note_id, "diff": diff, "mod_at_preview": note.get("mod")}
        return self._new_plan("update_note", steps, preview, errors)

    def propose_create_deck(self, name: str) -> dict:
        errors = [] if self.s.deck_writable(name) else [f"deck '{name}' is outside the writable decks"]
        if name in self.anki.call("deckNames"):
            errors.append(f"deck '{name}' already exists")
        return self._new_plan(
            "create_deck", [{"action": "createDeck", "params": {"deck": name}}], {"deck": name}, errors
        )

    def propose_delete_notes(self, note_ids: list[int]) -> dict:
        self.anki.check("deleteNotes", ok=True)  # switch first: no preview of a forbidden action
        if len(note_ids) > 50:
            raise PlanError("at most 50 notes per delete plan; there is no delete-by-query")
        info = [n for n in self.anki.call("notesInfo", {"notes": note_ids}) if n]
        found = {n["noteId"] for n in info}
        errors = self._scope_errors([c for n in info for c in n.get("cards", [])])
        missing = [i for i in note_ids if i not in found]
        preview = {
            "delete": [
                {
                    "note_id": n["noteId"],
                    "front": _excerpt(next(iter(sorted(n["fields"].values(), key=lambda v: v["order"])))["value"]),
                }
                for n in info
            ],
            "not_found": missing,
            "warning": "deleting a note deletes its cards and their review history; this cannot be undone",
        }
        steps = [{"action": "deleteNotes", "params": {"notes": sorted(found)}}] if found else []
        return self._new_plan("delete_notes", steps, preview, errors or ([] if found else ["no note found"]))

    def propose_set_due_date(self, card_ids: list[int], days: str) -> dict:
        self.anki.check("setDueDate", ok=True)
        errors = self._scope_errors(card_ids)
        return self._new_plan(
            "set_due_date",
            [{"action": "setDueDate", "params": {"cards": card_ids, "days": days}}],
            {
                "cards": card_ids,
                "days": days,
                "warning": "rescheduling changes the review history the scheduler learns from",
            },
            errors,
        )

    def propose_flag_cards(self, card_ids: list[int], color: int) -> dict:
        """Flag only with the agent's colors; a card already carrying a human flag is skipped."""
        if color not in self.s.agent_flags:
            raise Blocked(f"BLOCKED: flag {color} is the human's; the agent only writes {self.s.agent_flags}.")
        info = self.anki.call("cardsInfo", {"cards": card_ids})
        if any("flags" not in c for c in info):
            raise Blocked("BLOCKED: cardsInfo has no 'flags' field - cannot prove the human's flag stays intact.")
        target = [c["cardId"] for c in info if c["flags"] in self.s.agent_flags]
        skipped = [c["cardId"] for c in info if c["flags"] not in self.s.agent_flags]
        steps = [
            {"action": "setSpecificValueOfCard", "params": {"card": c, "keys": ["flags"], "newValues": [color]}}
            for c in target
        ]
        return self._new_plan(
            "flag_cards",
            steps,
            {"color": color, "flag": target, "skipped_human_flag": skipped},
            self._scope_errors(target) or ([] if target else ["no card can be flagged"]),
        )

    def _scope_errors(self, card_ids: list[int]) -> list[str]:
        if not card_ids:
            return []
        outside = sorted(
            {
                c["deckName"]
                for c in self.anki.call("cardsInfo", {"cards": card_ids})
                if not self.s.deck_writable(c["deckName"])
            }
        )
        return [f"cards in deck(s) outside the writable decks: {outside}"] if outside else []

    def _new_plan(self, kind: str, steps: list[dict], preview: dict, errors: list[str]) -> dict:
        plan = self.plans.create(kind, steps, preview, errors)
        self.audit.log(
            "proposed",
            plan=plan["id"],
            kind=kind,
            status=plan["status"],
            errors=errors,
            steps=[s["action"] for s in steps],
        )
        return self.view(plan)

    # ================================================================== approval and application
    def view(self, plan: dict) -> dict:
        nxt = {
            "invalid": "fix the errors and propose again; an invalid plan cannot be approved",
            "pending": "show this preview to the human, then call apply_plan; the human approves it",
            "approved": "call apply_plan",
            "applied": "done",
            "rejected": "rejected by the human",
            "expired": f"older than {self.s.plan_ttl_minutes} minutes; propose again",
        }[plan["status"]]
        return {k: plan[k] for k in ("id", "kind", "status", "expires", "errors", "preview")} | {"next": nxt}

    def get_plan(self, pid: str) -> dict:
        plan = self.plans.get(pid)
        if not plan:
            raise PlanError(f"plan {pid} not found")
        return plan

    def approve(self, pid: str, via: str) -> dict:
        plan = self.get_plan(pid)
        if plan["status"] != "pending":
            raise PlanError(f"plan {pid} is {plan['status']}, only a pending plan can be approved")
        self.audit.log("approved", plan=pid, via=via)
        return self.view(
            self.plans.set_status(
                pid, "approved", approved_via=via, approved_at=datetime.now(UTC).isoformat(timespec="seconds")
            )
        )

    def reject(self, pid: str, via: str, reason: str = "") -> dict:
        plan = self.get_plan(pid)
        if plan["status"] not in ("pending", "approved"):
            raise PlanError(f"plan {pid} is {plan['status']}")
        self.audit.log("rejected", plan=pid, via=via, reason=reason)
        return self.view(self.plans.set_status(pid, "rejected", reason=reason))

    def apply(self, pid: str) -> dict:
        plan = self.get_plan(pid)
        if plan["status"] == "pending" and self.s.approval == "none":
            plan = self.get_plan(self.approve(pid, via="config: approval = none")["id"])
        if plan["status"] != "approved":
            raise PlanError(
                f"plan {pid} is {plan['status']}: only an approved plan is applied "
                f"(the human approves it: anki-librarian-mcp approve {pid})"
            )
        if plan["kind"] in ("update_note", "attach_image"):  # stale-write protection
            note = self.anki.call("notesInfo", {"notes": [plan["preview"]["note_id"]]})[0]
            if note.get("mod") != plan["preview"]["mod_at_preview"]:
                self.plans.set_status(pid, "expired")
                self.audit.log("failed", plan=pid, error="note changed after the preview")
                raise PlanError(
                    "the note changed after the preview; propose again so the human sees the current version"
                )
        if plan["kind"] == "flag_cards":  # a human flag set after the preview wins
            cards = [st["params"]["card"] for st in plan["steps"]]
            now = {c["cardId"]: c["flags"] for c in self.anki.call("cardsInfo", {"cards": cards})} if cards else {}
            plan["steps"] = [st for st in plan["steps"] if now.get(st["params"]["card"]) in self.s.agent_flags]
            plan["preview"]["flag"] = [st["params"]["card"] for st in plan["steps"]]
        results = []
        try:
            for step in plan["steps"]:
                results.append(self.anki.call(step["action"], step["params"], ok=True))
        except Exception as e:
            self.audit.log("failed", plan=pid, step=len(results), error=str(e)[:300])
            self.plans.set_status(pid, "failed", error=str(e)[:300], partial_results=results)
            raise
        report = self._verify(plan, results)
        if plan["kind"] == "add_notes" and report.get("created"):
            report["flagged_blue"] = self._flag_large(report["created"])
        self.plans.set_status(pid, "applied", result=report)
        self.audit.log("applied", plan=pid, kind=plan["kind"], result=report)
        return {"id": pid, "status": "applied", "result": report}

    def _flag_large(self, note_ids: list[int]) -> int:
        """Blue flag on new large cards (maps, macros, long backs) so they are easy to find and suspend later."""
        large = [
            n
            for n in self.anki.call("notesInfo", {"notes": note_ids})
            if n and cards.is_large(n["fields"]["Front"]["value"], n["fields"]["Back"]["value"])
        ]
        card_ids = [c for n in large for c in n.get("cards", [])]
        flagged = 0
        for c in self.anki.call("cardsInfo", {"cards": card_ids}) if card_ids else []:
            if c.get("flags") == 0:
                params = {"card": c["cardId"], "keys": ["flags"], "newValues": [4]}
                self.anki.call("setSpecificValueOfCard", params, ok=True)
                flagged += 1
        return flagged

    def _verify(self, plan: dict, results: list) -> dict:
        """Read the collection back and compare with what the plan said it would do."""
        kind = plan["kind"]
        if kind in ("add_notes", "add_cloze_notes"):
            ids = next((r for s, r in zip(plan["steps"], results, strict=False) if s["action"] == "addNotes"), [])
            created = [i for i in ids if i]
            info = self.anki.call("notesInfo", {"notes": created}) if created else []
            wanted = next(s for s in plan["steps"] if s["action"] == "addNotes")["params"]["notes"]
            bad = [
                n["noteId"]
                for n, w in zip(info, [w for w, i in zip(wanted, ids, strict=False) if i], strict=False)
                if {k: v["value"] for k, v in n["fields"].items()} != w["fields"]
                or sorted(n["tags"]) != sorted(w["tags"])
            ]
            return {"created": created, "not_created": len(ids) - len(created), "mismatched_after_write": bad}
        if kind == "update_note":
            note = self._notes([plan["preview"]["note_id"]], full=True)[0]
            return {
                "note_id": note["note_id"],
                "fields_now": {k: _excerpt(v) for k, v in note["fields"].items()},
                "tags_now": note["tags"],
            }
        if kind == "flag_cards":
            cards = plan["preview"]["flag"]
            now = {c["cardId"]: c["flags"] for c in self.anki.call("cardsInfo", {"cards": cards})} if cards else {}
            color = plan["preview"]["color"]
            return {
                "flagged": [c for c in cards if now.get(c) == color],
                "failed": [c for c in cards if now.get(c) != color],
            }
        if kind == "delete_notes":
            ids = plan["steps"][0]["params"]["notes"] if plan["steps"] else []
            still = [n["noteId"] for n in self.anki.call("notesInfo", {"notes": ids}) if n]
            return {"deleted": [i for i in ids if i not in still], "still_present": still}
        return {"results": results}
