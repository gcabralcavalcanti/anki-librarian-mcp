"""A fake AnkiConnect: an in-memory collection that answers the same JSON protocol, in-process or over HTTP.

No test ever talks to a real Anki. The fake keeps a log of every action it received, so a test can prove that
a blocked action never left the server.
"""

from __future__ import annotations

import fnmatch
import itertools
import json
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODELS = {"Basic": ["Front", "Back"], "Cloze": ["Text", "Back Extra"]}


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


class FakeAnki:
    def __init__(self):
        self.decks = {"Default"}
        self.notes: dict[int, dict] = {}
        self.cards: dict[int, dict] = {}
        self.received: list[str] = []
        self._ids = itertools.count(1_700_000_000_000)

    # --------------------------------------------------------------- seeding
    def seed(self, deck: str, front: str, back: str = "", tags=(), model: str = "Basic", flags: int = 0) -> int:
        self.decks.add(deck)
        nid = next(self._ids)
        names = MODELS[model]
        self.notes[nid] = {
            "noteId": nid,
            "modelName": model,
            "tags": list(tags),
            "mod": 1,
            "fields": {names[0]: front, names[1]: back},
            "cards": [],
        }
        cid = next(self._ids)
        self.cards[cid] = {"cardId": cid, "note": nid, "deckName": deck, "flags": flags, "due": 0}
        self.notes[nid]["cards"].append(cid)
        return nid

    def card_of(self, nid: int) -> int:
        return self.notes[nid]["cards"][0]

    # --------------------------------------------------------------- protocol
    def handle(self, payload: dict) -> dict:
        action, params = payload["action"], payload.get("params", {})
        self.received.append(action)
        try:
            return {"result": getattr(self, "a_" + action)(**params), "error": None}
        except AttributeError:
            return {"result": None, "error": f"unsupported action {action}"}
        except Exception as e:
            return {"result": None, "error": str(e)}

    __call__ = handle

    def a_version(self):
        return 6

    def a_deckNames(self):
        return sorted(self.decks)

    def a_createDeck(self, deck):
        self.decks.add(deck)
        return 1

    def a_findNotes(self, query):
        return [nid for nid, n in self.notes.items() if self._match(n, query)]

    def _match(self, note, query):
        decks = {self.cards[c]["deckName"] for c in note["cards"]}
        text = _plain(" ".join(note["fields"].values()))
        words = set(text.replace(",", " ").replace(".", " ").split())
        for tok in query.split():
            if tok.startswith("deck:"):
                pat = tok[5:].strip('"')
                if not any(fnmatch.fnmatchcase(d, pat) or fnmatch.fnmatchcase(d, pat + "::*") for d in decks):
                    return False
            elif tok.startswith("tag:"):
                pat = tok[4:].lower()
                if not any(t.lower() == pat or t.lower().startswith(pat + "::") for t in note["tags"]):
                    return False
            elif tok.startswith("w:"):
                if _plain(tok[2:]) not in words:
                    return False
            elif _plain(tok) not in text:
                return False
        return True

    def a_notesInfo(self, notes):
        out = []
        for nid in notes:
            n = self.notes.get(nid)
            if not n:
                out.append({})
                continue
            names = MODELS[n["modelName"]]
            out.append(
                {
                    "noteId": nid,
                    "modelName": n["modelName"],
                    "tags": list(n["tags"]),
                    "mod": n["mod"],
                    "cards": list(n["cards"]),
                    "fields": {k: {"value": n["fields"][k], "order": names.index(k)} for k in names},
                }
            )
        return out

    def a_cardsInfo(self, cards):
        return [dict(self.cards[c]) for c in cards if c in self.cards]

    def a_addNotes(self, notes):
        ids = []
        for n in notes:
            if n["deckName"] not in self.decks:
                raise ValueError(f"deck was not found: {n['deckName']}")
            first = MODELS[n["modelName"]][0]
            dup = any(
                _plain(x["fields"][MODELS[x["modelName"]][0]]) == _plain(n["fields"][first])
                for x in self.notes.values()
                if x["modelName"] == n["modelName"]
            )
            if dup and not n.get("options", {}).get("allowDuplicate"):
                ids.append(None)
                continue
            ids.append(
                self.seed(
                    n["deckName"],
                    *[n["fields"][k] for k in MODELS[n["modelName"]]],
                    tags=n.get("tags", []),
                    model=n["modelName"],
                )
            )
        return ids

    def a_updateNoteFields(self, note):
        self.notes[note["id"]]["fields"].update(note["fields"])
        self.notes[note["id"]]["mod"] += 1
        return None

    def a_updateNoteTags(self, note, tags):
        self.notes[note]["tags"] = list(tags)
        self.notes[note]["mod"] += 1
        return None

    def a_deleteNotes(self, notes):
        for nid in notes:
            for c in self.notes.pop(nid)["cards"]:
                self.cards.pop(c)
        return None

    def a_setDueDate(self, cards, days):
        for c in cards:
            self.cards[c]["due"] = days
        return [True for _ in cards]

    def a_setSpecificValueOfCard(self, card, keys, newValues):
        for k, v in zip(keys, newValues, strict=False):
            self.cards[card][k] = v
        return [True]

    def a_deleteDecks(self, decks, cardsToo=True):
        raise AssertionError("deleteDecks must never reach Anki")

    def a_sync(self):
        raise AssertionError("sync must never reach Anki")


class FakeAnkiHTTP:
    """Serve a FakeAnki on 127.0.0.1:<random port>, so the real HTTP client is exercised end to end."""

    def __init__(self, fake: FakeAnki):
        fake_ref = fake

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                out = json.dumps(fake_ref.handle(body)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
