"""The action lock and the transport: blocked actions never leave the process; reads retry, writes do not."""

import urllib.error

import pytest
from fake_anki import FakeAnkiHTTP

from anki_librarian_mcp.connect import AnkiConnect, AnkiError, Blocked


def client(fake, **kw):
    return AnkiConnect(transport=fake, sleep=lambda s: None, **kw)


def test_reads_are_free(fake):
    assert "Economics::Macro" in client(fake).call("deckNames")


def test_write_needs_ok(fake):
    a = client(fake)
    with pytest.raises(Blocked):
        a.call("createDeck", {"deck": "Inbox::New"})
    assert a.call("createDeck", {"deck": "Inbox::New"}, ok=True) == 1


@pytest.mark.parametrize(
    "action",
    [
        "deleteDecks",
        "sync",
        "forgetCards",
        "answerCards",
        "setEaseFactors",
        "importPackage",
        "clearUnusedTags",
        "replaceTagsInAllNotes",
    ],
)
def test_forbidden_even_with_ok_and_never_sent(fake, action):
    with pytest.raises(Blocked):
        client(fake).call(action, {}, ok=True)
    assert fake.received == []


def test_delete_and_reschedule_are_switched_off_by_default(fake):
    with pytest.raises(Blocked, match="allow_delete"):
        client(fake).call("deleteNotes", {"notes": [1]}, ok=True)
    with pytest.raises(Blocked, match="allow_reschedule"):
        client(fake).call("setDueDate", {"cards": [1], "days": "0"}, ok=True)
    assert fake.received == []


def test_switch_on_still_needs_ok(fake):
    a = client(fake, switches={"allow_delete": True})
    with pytest.raises(Blocked):
        a.call("deleteNotes", {"notes": []})
    a.call("deleteNotes", {"notes": []}, ok=True)


def test_unknown_action_blocked(fake):
    with pytest.raises(Blocked, match="not on a known list"):
        client(fake).call("someNewAction", {}, ok=True)


def test_set_specific_value_only_for_flags(fake):
    a = client(fake)
    card = next(iter(fake.cards))
    with pytest.raises(Blocked):
        a.call("setSpecificValueOfCard", {"card": card, "keys": ["due"], "newValues": [0]}, ok=True)
    a.call("setSpecificValueOfCard", {"card": card, "keys": ["flags"], "newValues": [4]}, ok=True)
    assert fake.cards[card]["flags"] == 4


def test_reads_retry_with_backoff_then_succeed(fake):
    calls, delays = {"n": 0}, []

    def flaky(payload):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("connection refused")
        return fake(payload)

    a = AnkiConnect(transport=flaky, sleep=delays.append)
    assert a.call("version") == 6
    assert len(delays) == 2 and delays[1] > delays[0]


def test_writes_are_never_retried(fake):
    calls = {"n": 0}

    def down(payload):
        calls["n"] += 1
        raise TimeoutError("timed out")

    with pytest.raises(AnkiError):
        AnkiConnect(transport=down, sleep=lambda s: None).call("createDeck", {"deck": "Inbox::X"}, ok=True)
    assert calls["n"] == 1


def test_ankiconnect_error_is_raised(fake):
    with pytest.raises(AnkiError, match="deck was not found"):
        client(fake).call(
            "addNotes",
            {"notes": [{"deckName": "Nope", "modelName": "Basic", "fields": {"Front": "a", "Back": "b"}}]},
            ok=True,
        )


def test_real_http_transport_against_fake_server(fake):
    with FakeAnkiHTTP(fake) as srv:
        a = AnkiConnect(srv.url, timeout=5)
        assert a.call("version") == 6
        assert a.call("findNotes", {"query": "w:taylor"})
