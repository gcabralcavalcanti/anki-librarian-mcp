# anki-librarian-mcp - demo session (fake Anki, real server process over stdio)

### find_notes(query='taylor')
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
    "Economics::Macro::MonetaryPolicy"
   ],
   "decks": [
    "Economics::Macro"
   ],
   "fields": {
    "Front": "What does the Taylor rule set?",
    "Back": "The policy rate, from the inflation and output gaps"
   }
  }
 ]
}
```

### propose_add_notes (4 notes, one with a bad tag)
```json
{
 "id": "p-dea5c1",
 "kind": "add_notes",
 "status": "invalid",
 "expires": "2026-10-19T23:41:15+00:00",
 "errors": [
  "note 4: tag 'economics::macro': unknown root 'economics' (did you mean Economics?)",
  "note 4: no taxonomy tag (needs one under Economics, Humanities, Exact, Biology, Specific)"
 ],
 "preview": {
  "deck": "Economics::Macro",
  "deck_exists": true,
  "model": "Basic",
  "to_add": 3,
  "fronts": [
   "What does the Taylor rule target?",
   "Taylor principle",
   "Okun law"
  ],
  "skipped_duplicates": [
   {
    "note": 1,
    "front": "What does the Taylor rule set?",
    "duplicate_of": 1700000000000
   }
  ],
  "skipped_conflicts": [],
  "similar_flagged": [
   {
    "note": 2,
    "front": "What does the Taylor rule target?",
    "similar_to": 1700000000000,
    "existing_front": "What does the Taylor rule set?",
    "score": 0.92
   }
  ]
 },
 "next": "fix the errors and propose again; an invalid plan cannot be approved"
}
```

### propose_add_notes (bad note removed)
```json
{
 "id": "p-ca1365",
 "kind": "add_notes",
 "status": "pending",
 "expires": "2026-10-19T23:41:15+00:00",
 "errors": [],
 "preview": {
  "deck": "Economics::Macro",
  "deck_exists": true,
  "model": "Basic",
  "to_add": 2,
  "fronts": [
   "What does the Taylor rule target?",
   "Taylor principle"
  ],
  "skipped_duplicates": [
   {
    "note": 1,
    "front": "What does the Taylor rule set?",
    "duplicate_of": 1700000000000
   }
  ],
  "skipped_conflicts": [],
  "similar_flagged": [
   {
    "note": 2,
    "front": "What does the Taylor rule target?",
    "similar_to": 1700000000000,
    "existing_front": "What does the Taylor rule set?",
    "score": 0.92
   }
  ]
 },
 "next": "show this preview to the human, then call apply_plan; the human approves it"
}
```

### Elicitation shown to the human
```
Plan p-ca1365 (add_notes)
Add 2 note(s) to 'Economics::Macro'
  + What does the Taylor rule target?
  + Taylor principle
Skipped as duplicates: 1
Similar to existing notes: 1 (check before approving)

Write this to Anki?
```
-> the human clicks **approve**

### apply_plan
```json
{
 "id": "p-ca1365",
 "status": "applied",
 "result": {
  "created": [
   1700000000002,
   1700000000004
  ],
  "not_created": 0,
  "mismatched_after_write": []
 }
}
```

### propose_delete_notes
```
is_error=True: Error executing tool propose_delete_notes: BLOCKED: deleteNotes is off. Turning it on is the human's decision (allow_delete = true in the config).
```

### Audit log
```
{"event": "proposed", "plan": "p-dea5c1", "kind": "add_notes", "status": "invalid", "errors": ["note 4: tag 'economics::macro': unknown root 'economics' (did you mean Economics?)", "note 4: no taxonomy tag (needs one under Economics, Humanities, Exact, Biology, Specific)"], "steps": ["addNotes"]}
{"event": "proposed", "plan": "p-ca1365", "kind": "add_notes", "status": "pending", "errors": [], "steps": ["addNotes"]}
{"event": "approved", "plan": "p-ca1365", "via": "mcp elicitation"}
{"event": "applied", "plan": "p-ca1365", "kind": "add_notes", "result": {"created": [1700000000002, 1700000000004], "not_created": 0, "mismatched_after_write": []}}
{"event": "blocked", "error": "BLOCKED: deleteNotes is off. Turning it on is the human's decision (allow_delete = true in the config)."}
```

Actions that reached the (fake) Anki: ['addNotes', 'cardsInfo', 'deckNames', 'findNotes', 'notesInfo']
