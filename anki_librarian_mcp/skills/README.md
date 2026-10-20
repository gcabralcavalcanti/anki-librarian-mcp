# Card-making skills

Five instruction sets that turn study material into Anki cards through this server. They are the public
version of the workflow I use every day; the server enforces the rules a prompt cannot (no write without your
approval, no duplicates, size limits, tag taxonomy).

| Step | Skill | Input | Output |
|---|---|---|---|
| 1 | [harvest](harvest.md) | material, a finished project or a conversation | a debrief: what was learned, grouped by theme, with the doubts that came up |
| 2 | [planner](planner.md) | the debrief or new material | a deck plan; in reconcile mode, what you already have vs. what is missing (searched in your collection) |
| 3 | [generator](generator.md) | the plan | cards in three layers (map, mechanism, atoms) that respect the size limits |
| 4 | [tags](tags.md) | the cards | library-style tags from [the taxonomy](taxonomy.md) |
| 5 | server | the cards | `propose_add_notes` (a dry run) → your approval → cards in Anki, read back |

[radar](radar.md) is a weekly variant: scan news by track, pick what is worth a card, then steps 3 to 5.

## How to use them

- **Claude Desktop or Claude Code with this server connected:** the server publishes each skill as a prompt
  (`make_cards`, `harvest`, `plan_deck`, `generate_cards`, `tag_cards`, `radar`). Pick one and paste the
  material, or just say "make cards from this material".
- **Claude Code skills folder:** copy this folder to `.claude/skills/anki-cards/` and the model will load the
  right file when you ask for cards.

## Rules every step follows

1. Reads are free; nothing is written to Anki until you approve a plan.
2. Search before creating. A card that already exists is reported, not duplicated.
3. Few strong cards. Density comes from more small cards, never from bigger ones.
4. A card must be answerable alone, months later, shuffled among unrelated cards.
5. Never invent: what the material does not say does not go on a card. Divergent sources are marked.
