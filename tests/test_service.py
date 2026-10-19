"""Plans end to end against the fake collection: reconcile, validate, approve, apply, verify, audit."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from anki_librarian_mcp.connect import Blocked
from anki_librarian_mcp.service import PlanError
from conftest import librarian, make_settings

TAG = ["Economics::Macro::MonetaryPolicy"]


def test_add_plan_writes_nothing_until_approved_and_applied(lib, fake):
    before = len(fake.notes)
    plan = lib.propose_add_notes("Economics::Macro", [{"front": "Taylor principle", "back": "Rates move more than "
                                                       "one-for-one with inflation", "tags": TAG}])
    assert plan["status"] == "pending" and plan["preview"]["to_add"] == 1
    assert len(fake.notes) == before
    with pytest.raises(PlanError, match="only an approved plan"):
        lib.apply(plan["id"])
    lib.approve(plan["id"], via="test")
    res = lib.apply(plan["id"])
    assert len(res["result"]["created"]) == 1 and res["result"]["mismatched_after_write"] == []
    assert len(fake.notes) == before + 1


def test_reconciliation_skips_duplicates_and_flags_conflicts_and_similar(lib):
    plan = lib.propose_add_notes("Economics::Macro", [
        {"front": "What does the Taylor rule set?", "back": "The policy rate, from the inflation and output gaps",
         "tags": TAG},
        {"front": "Neutral real interest rate", "back": "something else entirely", "tags": TAG},
        {"front": "What does the Taylor rule set ?!", "back": "x", "tags": TAG},
        {"front": "What does the Taylor rule target?", "back": "The policy rate", "tags": TAG},
        {"front": "Okun law", "back": "Unemployment and output gap", "tags": TAG},
    ])
    p = plan["preview"]
    assert [d["note"] for d in p["skipped_duplicates"]] == [1, 3]       # 3 = same front within the batch
    assert [c["note"] for c in p["skipped_conflicts"]] == [2]           # same front, different back
    assert [s["note"] for s in p["similar_flagged"]] == [4]
    assert p["to_add"] == 2


def test_tag_taxonomy_makes_the_plan_invalid(lib):
    plan = lib.propose_add_notes("Economics::Macro", [{"front": "Okun law", "back": "b", "tags": ["economics::macro"]},
                                                      {"front": "Phillips curve", "back": "b", "tags": ["Misc"]}])
    assert plan["status"] == "invalid"
    assert any("did you mean Economics" in e for e in plan["errors"])
    assert any("no taxonomy tag" in e for e in plan["errors"])
    with pytest.raises(PlanError):
        lib.approve(plan["id"], via="test")


def test_deck_outside_the_writable_scope_is_invalid(lib):
    plan = lib.propose_add_notes("Personal::Journal", [{"front": "x y z w", "back": "b", "tags": TAG}])
    assert plan["status"] == "invalid" and "outside the writable decks" in plan["errors"][0]


def test_new_deck_is_created_inside_the_plan(lib, fake):
    plan = lib.propose_add_notes("Inbox::AI", [{"front": "What is an eval golden set?", "back": "b",
                                                "tags": ["Exact::AI"]}])
    assert plan["preview"]["deck_exists"] is False
    lib.approve(plan["id"], via="test")
    lib.apply(plan["id"])
    assert "Inbox::AI" in fake.decks


def test_cloze_syntax_checked_for_the_whole_batch(lib):
    plan = lib.propose_add_cloze_notes("Economics::Macro", [{"text": "The {{c1::Taylor}} rule", "tags": TAG},
                                                            {"text": "no deletion here", "tags": TAG}])
    assert plan["status"] == "invalid" and "note 2: no cloze deletion" in plan["errors"][0]


def test_batch_limit(lib):
    with pytest.raises(PlanError, match="limit is 50"):
        lib.propose_add_notes("Inbox::X", [{"front": f"front {i}", "tags": TAG} for i in range(51)])


def test_update_shows_diff_and_refuses_stale_writes(lib, fake):
    nid = next(iter(fake.notes))
    plan = lib.propose_update_note(nid, fields={"Back": "The policy rate"}, tags=TAG + ["TEMP::Review"])
    assert plan["preview"]["diff"]["fields"]["Back"]["after"] == "The policy rate"
    lib.approve(plan["id"], via="test")
    fake.notes[nid]["mod"] += 1                       # the human edited the note in Anki meanwhile
    with pytest.raises(PlanError, match="changed after the preview"):
        lib.apply(plan["id"])
    plan = lib.propose_update_note(nid, fields={"Back": "The policy rate"})
    lib.approve(plan["id"], via="test")
    lib.apply(plan["id"])
    assert fake.notes[nid]["fields"]["Back"] == "The policy rate"


def test_update_outside_scope_is_invalid(lib, fake):
    private = [n for n, v in fake.notes.items() if v["fields"]["Front"] == "Private card"][0]
    assert lib.propose_update_note(private, tags=["Specific::X"])["status"] == "invalid"


def test_delete_is_off_by_default(lib, fake):
    with pytest.raises(Blocked, match="allow_delete"):
        lib.propose_delete_notes([next(iter(fake.notes))])


def test_delete_when_switched_on_is_still_a_plan(tmp_path, fake):
    lib = librarian(make_settings(tmp_path, allow_delete=True), fake)
    nid = next(iter(fake.notes))
    plan = lib.propose_delete_notes([nid, 999])
    assert plan["preview"]["not_found"] == [999] and "cannot be undone" in plan["preview"]["warning"]
    assert nid in fake.notes
    lib.approve(plan["id"], via="test")
    assert lib.apply(plan["id"])["result"]["deleted"] == [nid]


def test_reschedule_is_off_by_default(lib, fake):
    with pytest.raises(Blocked, match="allow_reschedule"):
        lib.propose_set_due_date([next(iter(fake.cards))], "0")


def test_flags_never_overwrite_the_human_red_flag(tmp_path, fake):
    lib = librarian(make_settings(tmp_path, writable_decks=["*"]), fake)
    cards = list(fake.cards)
    plan = lib.propose_flag_cards(cards, 4)
    red = [c for c in cards if fake.cards[c]["flags"] == 1]
    assert plan["preview"]["skipped_human_flag"] == red
    with pytest.raises(Blocked):
        lib.propose_flag_cards(cards, 1)
    lib.approve(plan["id"], via="test")
    fake.cards[cards[0]]["flags"] = 1                 # the human flags a card after the preview
    res = lib.apply(plan["id"])
    assert cards[0] not in res["result"]["flagged"] and fake.cards[cards[0]]["flags"] == 1
    assert all(fake.cards[c]["flags"] == 1 for c in red)


def test_plans_expire(lib, settings):
    plan = lib.propose_create_deck("Inbox::Old")
    path = settings.state_dir / "plans.json"
    plans = json.loads(path.read_text(encoding="utf-8"))
    plans[plan["id"]]["expires"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    path.write_text(json.dumps(plans), encoding="utf-8")
    with pytest.raises(PlanError, match="expired"):
        lib.approve(plan["id"], via="test")


def test_approval_none_applies_directly(tmp_path, fake):
    lib = librarian(make_settings(tmp_path, approval="none"), fake)
    plan = lib.propose_create_deck("Inbox::Auto")
    assert lib.apply(plan["id"])["status"] == "applied"


def test_audit_log_records_the_whole_life_of_a_plan(lib, settings):
    plan = lib.propose_create_deck("Inbox::Audit")
    lib.approve(plan["id"], via="test")
    lib.apply(plan["id"])
    lines = (settings.state_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(l)["event"] for l in lines] == ["proposed", "approved", "applied"]


def test_find_notes_returns_decks_and_excerpts(lib):
    res = lib.find_notes("deck:Economics tag:Economics::Macro taylor")
    assert res["total"] == 1 and res["notes"][0]["decks"] == ["Economics::Macro"]
