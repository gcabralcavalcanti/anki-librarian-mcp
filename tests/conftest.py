"""Fixtures: a fake collection with a few fictitious notes, and a Librarian wired to it. No real Anki."""
import pytest

from anki_librarian_mcp.config import Settings, Taxonomy
from anki_librarian_mcp.connect import AnkiConnect
from anki_librarian_mcp.service import Librarian
from fake_anki import FakeAnki


@pytest.fixture
def fake():
    f = FakeAnki()
    f.seed("Economics::Macro", "What does the Taylor rule set?", "The policy rate, from the inflation and output gaps",
           tags=["Economics::Macro::MonetaryPolicy"])
    f.seed("Economics::Macro", "Neutral real interest rate", "The rate that neither stimulates nor contracts",
           tags=["Economics::Macro::MonetaryPolicy"])
    f.seed("Personal::Journal", "Private card", "never touch", tags=["Specific::Private"], flags=1)
    return f


def make_settings(tmp_path, **kw) -> Settings:
    base = dict(writable_decks=["Economics::*", "Inbox::*"], approval="cli", state_dir=tmp_path / "state",
                taxonomy=Taxonomy(roots=["Economics", "Humanities", "Exact", "Biology", "Specific"],
                                  operational=["TEMP"]))
    base.update(kw)
    return Settings(**base)


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


def librarian(settings, fake) -> Librarian:
    anki = AnkiConnect(transport=fake, switches={"allow_delete": settings.allow_delete,
                                                 "allow_reschedule": settings.allow_reschedule}, sleep=lambda s: None)
    return Librarian(settings, anki)


@pytest.fixture
def lib(settings, fake):
    return librarian(settings, fake)
