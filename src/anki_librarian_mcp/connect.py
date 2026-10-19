"""connect.py - the only door to AnkiConnect, with the Librarian's action lock.

AnkiConnect is a local add-on that exposes the Anki desktop app as a JSON API (default 127.0.0.1:8765).
Every action is classified BEFORE a request leaves this process:

  READ        always allowed
  WRITE       only with ok=True, which the service passes only when applying an approved plan
  SWITCHED    deleting and rescheduling: forbidden unless switched on in the config, then like WRITE
  FORBIDDEN   never (sync, package import, answering or resetting cards, deleting decks, mass tag rewrites)
  CONDITIONAL setSpecificValueOfCard, only for the `flags` key, only through the flag routine
  unknown     blocked: a new action must be added to a list on purpose (allowlist, not denylist)

Reads are retried with exponential backoff (Anki may be starting up); writes are never retried, so a
timeout can never turn into a duplicate write.

Base: the Anki client of the Librarian agent (personal-ai-agents), moved here as the single home of the code.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable

READ = {"version", "deckNames", "deckNamesAndIds", "getTags", "findNotes", "findCards", "notesInfo", "cardsInfo",
        "modelNames", "modelFieldNames", "getDeckStats", "areSuspended", "getNumCardsReviewedToday",
        "canAddNotes", "canAddNotesWithErrorDetail", "getDeckConfig"}
WRITE = {"addNotes", "updateNoteFields", "updateNoteTags", "addTags", "removeTags", "changeDeck",
         "suspend", "unsuspend", "createDeck"}
SWITCHED = {"deleteNotes": "allow_delete", "setDueDate": "allow_reschedule"}
FORBIDDEN = {"deleteDecks", "removeEmptyNotes", "clearUnusedTags", "replaceTagsInAllNotes", "forgetCards",
             "relearnCards", "answerCards", "setEaseFactors", "importPackage", "sync", "updateModelTemplates",
             "storeMediaFile", "deleteMediaFile", "guiExitAnki"}
CONDITIONAL = {"setSpecificValueOfCard"}


class Blocked(Exception):
    """The lock refused an action. The message says what to do instead."""


class AnkiError(RuntimeError):
    """AnkiConnect answered with an error, or could not be reached."""


def http_transport(url: str, timeout: float) -> Callable[[dict], dict]:
    def send(payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    return send


class AnkiConnect:
    def __init__(self, url: str = "http://127.0.0.1:8765", *, timeout: float = 10.0, read_retries: int = 3,
                 backoff_s: float = 0.5, switches: dict[str, bool] | None = None,
                 transport: Callable[[dict], dict] | None = None, sleep: Callable[[float], None] = time.sleep):
        self.send = transport or http_transport(url, timeout)
        self.read_retries = read_retries
        self.backoff_s = backoff_s
        self.switches = switches or {}
        self.sleep = sleep

    def check(self, action: str, ok: bool = False, field: str | None = None) -> None:
        """Raise Blocked if the lock refuses `action`. Called before anything is sent."""
        if action in FORBIDDEN:
            raise Blocked(f"BLOCKED: {action} is forbidden for the agent (the human does it in Anki).")
        if action in SWITCHED and not self.switches.get(SWITCHED[action]):
            raise Blocked(f"BLOCKED: {action} is off. Turning it on is the human's decision "
                          f"({SWITCHED[action]} = true in the config).")
        if action in CONDITIONAL and field != "flags":
            raise Blocked(f"BLOCKED: {action} only passes for the 'flags' key, through the flag routine.")
        if action not in READ | WRITE | set(SWITCHED) | CONDITIONAL:
            raise Blocked(f"BLOCKED: {action} is not on a known list - add it on purpose, with a test.")
        if action not in READ and not ok:
            raise Blocked(f"BLOCKED: {action} writes to the collection; it only runs when an approved plan is applied.")

    def call(self, action: str, params: dict | None = None, *, ok: bool = False) -> Any:
        field = (params or {}).get("keys", [None])[0] if action in CONDITIONAL else None
        self.check(action, ok=ok, field=field)
        payload = {"action": action, "version": 6, "params": params or {}}
        attempts = self.read_retries + 1 if action in READ else 1
        for attempt in range(attempts):
            try:
                resp = self.send(payload)
                break
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
                if attempt == attempts - 1:
                    raise AnkiError(f"AnkiConnect unreachable ({action}): {e}. Is Anki open with AnkiConnect?") from e
                self.sleep(self.backoff_s * 2 ** attempt)
        if resp.get("error"):
            raise AnkiError(f"AnkiConnect error in {action}: {resp['error']}")
        return resp["result"]
