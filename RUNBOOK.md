# Runbook

## Run
| Task | Command |
|---|---|
| Check settings and the connection to Anki | `anki-librarian-mcp --config anki-librarian.toml check` |
| Start the server (Claude Desktop and Claude Code do this for you) | `anki-librarian-mcp --config anki-librarian.toml serve` |
| See pending plans | `anki-librarian-mcp plans --status pending` |
| Approve a plan from the terminal | `anki-librarian-mcp approve <plan>` (asks you to type the plan id) |
| Reject a plan | `anki-librarian-mcp reject <plan> "reason"` |
| Last events (what was proposed, approved, written, blocked) | `anki-librarian-mcp audit -n 30` |
| Live demo on GitHub Pages | every push to main runs `.github/workflows/pages.yml` (no key) and publishes the simulation; turn it on once in Settings > Pages > Source = GitHub Actions |
| Demo, no key | `python demo.py` |
| Tests | `pip install -e ".[test]"` then `python -m pytest` |

## Update
1. `pip install -U git+https://github.com/gcabralcavalcanti/anki-librarian-mcp` (or `git pull` in a checkout).
2. Compare your settings with `anki-librarian.example.toml`; new settings always default to the safe value.
3. The similarity index (the word list used to find similar cards) rebuilds itself when notes change. To rebuild it from scratch, delete
   `.anki-librarian/similarity-index.json`.
4. Changed a skill or the demo material? Re-record the demo answers with `python demo.py --live` (needs
   `ANTHROPIC_API_KEY`; costs a few cents) and commit `data/recorded/`.

## When something breaks
| What you see | Cause | Fix |
|---|---|---|
| `AnkiConnect unreachable` | Anki closed, or the add-on not installed | open Anki; install AnkiConnect (code 2055492159); check `anki_url` |
| `BLOCKED: <action> is off` | delete or reschedule switched off | intended; turn it on in the settings only if you mean it |
| `BLOCKED: ... forbidden` / `not on a known list` | an action the server never runs | intended; do it by hand in Anki |
| `deck ... is outside the writable decks` | the deck is not in `writable_decks` | add the deck (or a pattern like `Economics::*`) to the settings |
| `unknown root` / `no taxonomy tag` | a tag outside your taxonomy | fix the tag, or add the root to `[taxonomy]` |
| `cognitive weight ... >` / `back has ... characters` | a card too big for its type | split it; or set `card_rules = "warn"` to accept it |
| `the question reveals how many items` / `date in the question` | the front gives the answer away | rewrite the question |
| `plan ... is expired` | more than 15 minutes between preview and approval | propose again |
| `the note changed after the preview` | you edited the note in Anki meanwhile | propose again, so you approve the current version |
| `this client cannot ask the user` | the app cannot show the approval form | approve in a terminal: `anki-librarian-mcp approve <plan>` |
| `REFUSED: approve must be typed by a human` | approval run from a script or by the assistant | run it yourself in a terminal |
| `image: not a PNG, JPEG, GIF or WebP` / `only https://` | the picture link or file is not usable | pick another image |
| `no recorded answer` in the demo | the skills or material changed since the recording | `python demo.py --live` with a key |
