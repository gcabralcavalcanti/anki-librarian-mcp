"""Card rules, the collection index and pictures, against the fake collection."""

import base64
import json

import pytest
from conftest import librarian, make_settings

from anki_librarian_mcp import cards, media
from anki_librarian_mcp.retrieval import CollectionIndex

TAG = ["Economics::Macro::MonetaryPolicy"]
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


# ---------------------------------------------------------------- card rules
def test_layer_and_weight():
    w = cards.weight(
        "[Macro] Econometrics: OLS <br><br> How does minimising the squared residuals lead to the estimator?",
        "Start from the sum of squared residuals. <br><br> → the first-order condition gives the normal equations."
        " <br><br> → with full column rank the system has one solution.",
    )
    assert w["layer"] == cards.MACRO and w["pc"] == 5 and not w["problems"]
    short = cards.weight("Biochemistry: citric acid cycle <br><br> Where does it take place?", "Mitochondrial matrix.")
    assert short["layer"] == cards.MNEMONIC


def test_ceiling_breach_is_reported():
    back = " <br><br> ".join(f"<b>Step {i}:</b> A → B → C" for i in range(6))
    w = cards.weight("Economics: trade <br><br> How does the chain work?", back)
    assert w["layer"] == cards.RECONSTRUCTION and w["problems"]


@pytest.mark.parametrize(
    ("front", "tags", "expected"),
    [
        ("Economics: trade <br><br> Which three circumstances raise productivity?", [], "reveals how many"),
        ("History: crises <br><br> What happened to banks in the 1930s?", ["Humanities::History::World"], "date"),
        ("[Map] Period X <br><br> How do context, conflict, policy and result fit together?", [], "structure"),
    ],
)
def test_front_checks(front, tags, expected):
    assert any(expected in p for p in cards.front_problems(front, tags))


def test_front_checks_allow_names_with_numbers():
    assert cards.front_problems("Physics: mechanics <br><br> What do Newton's three laws state?", []) == []


def test_tsv_round_trip():
    rows = [{"front": "Q <br><br> a?", "back": "line<br>two", "tags": ["Economics::Macro"]}]
    deck, back = cards.from_tsv(cards.to_tsv("Inbox::Test", rows))
    assert deck == "Inbox::Test" and back == rows


def test_oversized_card_makes_the_plan_invalid(lib):
    back = " <br><br> ".join(f"<b>Step {i}:</b> A → B → C" for i in range(6))
    plan = lib.propose_add_notes(
        "Economics::Macro", [{"front": "Economics: x <br><br> How?", "back": back, "tags": TAG}]
    )
    assert plan["status"] == "invalid" and any("cognitive weight" in e for e in plan["errors"])


def test_card_rules_can_be_relaxed(tmp_path, fake):
    lib = librarian(make_settings(tmp_path, card_rules="warn"), fake)
    back = " <br><br> ".join(f"<b>Step {i}:</b> A → B → C" for i in range(6))
    plan = lib.propose_add_notes(
        "Economics::Macro", [{"front": "Economics: x <br><br> How?", "back": back, "tags": TAG}]
    )
    assert plan["status"] == "pending" and plan["preview"]["warnings"]


# ---------------------------------------------------------------- retrieval
def test_index_finds_a_reworded_card_and_cites_it(lib, fake):
    fake.seed(
        "Economics::Macro",
        "Economics: monetary policy <br><br> Why do central banks raise interest rates when inflation rises?",
        "Higher rates make credit more expensive, cool demand and pull inflation back to target.",
        tags=TAG,
    )
    plan = lib.propose_add_notes(
        "Economics::Macro",
        [
            {
                "front": "Economics: monetary policy <br><br> How does a higher policy rate bring inflation down?",
                "back": "Credit gets more expensive, demand cools and inflation falls back to the target.",
                "tags": TAG,
            }
        ],
    )
    similar = plan["preview"]["similar_flagged"]
    assert similar and "raise interest rates" in similar[0]["existing_front"]
    assert "credit more expensive" in similar[0]["existing_back"]


def test_index_refresh_reads_only_new_or_changed_notes(fake, settings):
    idx = CollectionIndex(librarian(settings, fake).anki, settings.state_dir)
    assert idx.refresh()["read"] == 3
    assert idx.refresh()["read"] == 0
    nid = next(iter(fake.notes))
    fake.notes[nid]["mod"] += 1
    fake.seed("Economics::Macro", "Okun law", "Output and unemployment move together", tags=TAG)
    assert idx.refresh()["read"] == 2
    del fake.notes[nid]
    assert idx.refresh()["removed"] == 1
    assert json.loads((settings.state_dir / "similarity-index.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- pictures
def test_new_card_with_a_picture_and_credit(lib, fake, tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(PNG)
    note = {
        "front": "Biology: cells <br><br> What does a mitochondrion look like?",
        "back": "Double membrane.",
        "tags": ["Biology::Cells"],
        "image": {"path": str(img), "credit": "Jane Doe · CC BY 4.0 · Wikimedia Commons"},
    }
    plan = lib.propose_add_notes("Inbox::Bio", [note])
    assert plan["status"] == "pending" and plan["preview"]["images"] == 1
    lib.approve(plan["id"], via="test")
    created = lib.apply(plan["id"])["result"]["created"][0]
    back = fake.notes[created]["fields"]["Back"]
    name = next(iter(fake.media))
    assert f'<img src="{name}">' in back and "Photo: Jane Doe" in back
    assert base64.b64decode(fake.media[name]) == PNG


def test_attach_picture_to_an_existing_note(lib, fake):
    nid = next(iter(fake.notes))
    lib.fetch = lambda url, timeout=20.0: PNG
    plan = lib.propose_attach_image(nid, {"url": "https://upload.example.org/a.png"})
    assert fake.notes[nid]["fields"]["Back"].count("<img") == 0
    lib.approve(plan["id"], via="test")
    lib.apply(plan["id"])
    assert fake.notes[nid]["fields"]["Back"].count("<img") == 1


def test_bad_images_are_refused(lib, tmp_path):
    txt = tmp_path / "x.png"
    txt.write_bytes(b"not an image")
    plan = lib.propose_add_notes("Inbox::Bio", [{"front": "Q <br><br> q?", "back": "a", "image": {"path": str(txt)}}])
    assert plan["status"] == "invalid" and "not a PNG" in " ".join(plan["errors"])
    with pytest.raises(media.MediaError):
        media.prepare({"url": "http://insecure.example/a.png"}, tmp_path, "x")


def test_search_keeps_only_free_licences():
    page = lambda title, lic: {  # noqa: E731
        "title": f"File:{title}",
        "imageinfo": [
            {
                "thumburl": f"https://u/{title}",
                "descriptionurl": "https://p",
                "extmetadata": {"LicenseShortName": {"value": lic}, "Artist": {"value": "<a>Ann</a>"}},
            }
        ],
    }
    body = {
        "query": {
            "pages": {
                "1": page("a.jpg", "CC BY-SA 4.0"),
                "2": page("b.jpg", "CC BY-NC 2.0"),
                "3": page("c.jpg", "Public domain"),
                "4": page("d.pdf", "CC0"),
            }
        }
    }
    found = media.search_commons("mitochondrion", fetch=lambda url, timeout=20.0: json.dumps(body).encode())
    assert [f["title"] for f in found] == ["a.jpg", "c.jpg"]
    assert found[0]["credit_required"] and not found[1]["credit_required"]
    assert found[0]["credit"].startswith("Ann")
