# Demo session: the real server process over stdio, with a practice Anki

### find_notes('taylor')
```json
{
 "query": "taylor",
 "total": 1,
 "shown": 1,
 "notes": [
  {
   "note_id": 1700000000000,
   "model": "Basic",
   "tags": [
    "Economics::Macroeconomics::Applied::Monetary.Economics"
   ],
   "decks": [
    "Economics::Macro"
   ],
   "fields": {
    "Front": "Macroeconomics: Taylor rule What does the Taylor rule set?",
    "Back": "The policy rate, from the inflation gap and the output gap."
   }
  }
 ]
}
```

### propose_add_notes: 4 cards, one with a tag outside the taxonomy
```json
{
 "id": "p-demo1",
 "kind": "add_notes",
 "status": "invalid",
 "expires": "2026-01-01T00:00:00+00:00",
 "errors": [
  "note 4: tag 'economics::macro': unknown root 'economics' (did you mean Economics?)",
  "note 4: no taxonomy tag (needs one under Economics, Humanities, Exact.Sciences, Biological.Sciences, Specifics)"
 ],
 "preview": {
  "deck": "Economics::Macro",
  "deck_exists": true,
  "model": "Basic",
  "to_add": 3,
  "fronts": [
   "Macroeconomics: Taylor rule What does the Taylor rule target?",
   "Macroeconomics: Taylor rule What is the Taylor principle?",
   "Macroeconomics: Okun law How do output and unemployment move together?"
  ],
  "skipped_duplicates": [
   {
    "note": 1,
    "front": "Macroeconomics: Taylor rule What does the Taylor rule set?",
    "duplicate_of": 1700000000000
   }
  ],
  "skipped_conflicts": [],
  "similar_flagged": [
   {
    "note": 2,
    "front": "Macroeconomics: Taylor rule What does the Taylor rule target?",
    "similar_to": 1700000000000,
    "existing_front": "Macroeconomics: Taylor rule What does the Taylor rule set?",
    "existing_back": "The policy rate, from the inflation gap and the output gap.",
    "score": 0.96
   },
   {
    "note": 3,
    "front": "Macroeconomics: Taylor rule What is the Taylor principle?",
    "similar_to": 1700000000000,
    "existing_front": "Macroeconomics: Taylor rule What does the Taylor rule set?",
    "existing_back": "The policy rate, from the inflation gap and the output gap.",
    "score": 0.86
   }
  ],
  "images": 0,
  "cards": [
   {
    "note": 1,
    "layer": "mnemonic",
    "weight": 1,
    "chars": 59
   },
   {
    "note": 2,
    "layer": "mnemonic",
    "weight": 1,
    "chars": 16
   },
   {
    "note": 3,
    "layer": "mnemonic",
    "weight": 1,
    "chars": 63
   },
   {
    "note": 4,
    "layer": "mnemonic",
    "weight": 1,
    "chars": 54
   }
  ],
  "warnings": []
 },
 "next": "fix the errors and propose again; an invalid plan cannot be approved"
}
```

### propose_add_notes: corrected
```json
{
 "id": "p-demo2",
 "kind": "add_notes",
 "status": "pending",
 "expires": "2026-01-01T00:00:00+00:00",
 "errors": [],
 "preview": {
  "deck": "Economics::Macro",
  "deck_exists": true,
  "model": "Basic",
  "to_add": 2,
  "fronts": [
   "Macroeconomics: Taylor rule What does the Taylor rule target?",
   "Macroeconomics: Taylor rule What is the Taylor principle?"
  ],
  "skipped_duplicates": [
   {
    "note": 1,
    "front": "Macroeconomics: Taylor rule What does the Taylor rule set?",
    "duplicate_of": 1700000000000
   }
  ],
  "skipped_conflicts": [],
  "similar_flagged": [
   {
    "note": 2,
    "front": "Macroeconomics: Taylor rule What does the Taylor rule target?",
    "similar_to": 1700000000000,
    "existing_front": "Macroeconomics: Taylor rule What does the Taylor rule set?",
    "existing_back": "The policy rate, from the inflation gap and the output gap.",
    "score": 0.96
   },
   {
    "note": 3,
    "front": "Macroeconomics: Taylor rule What is the Taylor principle?",
    "similar_to": 1700000000000,
    "existing_front": "Macroeconomics: Taylor rule What does the Taylor rule set?",
    "existing_back": "The policy rate, from the inflation gap and the output gap.",
    "score": 0.86
   }
  ],
  "images": 0,
  "cards": [
   {
    "note": 1,
    "layer": "mnemonic",
    "weight": 1,
    "chars": 59
   },
   {
    "note": 2,
    "layer": "mnemonic",
    "weight": 1,
    "chars": 16
   },
   {
    "note": 3,
    "layer": "mnemonic",
    "weight": 1,
    "chars": 63
   }
  ],
  "warnings": []
 },
 "next": "show this preview to the human, then call apply_plan; the human approves it"
}
```

### Approval form shown to you
```
Plan p-demo2 (add_notes)
Add 2 note(s) to 'Economics::Macro'
  + Macroeconomics: Taylor rule What does the Taylor rule target?
  + Macroeconomics: Taylor rule What is the Taylor principle?
Skipped as duplicates: 1
Similar to existing notes: 2 (check before approving)

Write this to Anki?
```

### apply_plan
```json
{
 "id": "p-demo2",
 "status": "applied",
 "result": {
  "created": [
   1700000000002,
   1700000000004
  ],
  "not_created": 0,
  "mismatched_after_write": [],
  "flagged_blue": 0
 }
}
```

### propose_delete_notes
```
is_error=True: Error executing tool propose_delete_notes: BLOCKED: deleteNotes is off. Turning it on is the human's decision (allow_delete = true in the config).
```

### Audit log
```
{"event": "proposed", "plan": "p-demo1", "kind": "add_notes", "status": "invalid", "errors": ["note 4: tag 'economics::macro': unknown root 'economics' (did you mean Economics?)", "note 4: no taxonomy tag (needs one under Economics, Humanities, Exact.Sciences, Biological.Sciences, Specifics)"], "steps": ["addNotes"]}
{"event": "proposed", "plan": "p-demo2", "kind": "add_notes", "status": "pending", "errors": [], "steps": ["addNotes"]}
{"event": "approved", "plan": "p-demo2", "via": "mcp elicitation"}
{"event": "applied", "plan": "p-demo2", "kind": "add_notes", "result": {"created": [1700000000002, 1700000000004], "not_created": 0, "mismatched_after_write": [], "flagged_blue": 0}}
{"event": "blocked", "error": "BLOCKED: deleteNotes is off. Turning it on is the human's decision (allow_delete = true in the config)."}
```

Actions that reached the practice Anki: ['addNotes', 'cardsInfo', 'deckNames', 'findNotes', 'notesInfo']
