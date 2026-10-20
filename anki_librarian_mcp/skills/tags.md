---
name: tags
description: Give each card library-style hierarchical tags from the taxonomy, so it can be found again; also re-tags existing cards without touching anything else.
---
# Tags

A tag has one job: finding the card later. Content (front and back) decides, not old tags.

## Rules

- Hierarchy with `::`, words joined by `.`, Title.Case, no spaces: `Economics::Macroeconomics::Applied::Monetary.Economics`.
- Start from the roots in [the taxonomy](taxonomy.md); prefer an existing tag (list them with `find_notes`);
  a new tag is born only as a child of an existing path, and is reported.
- Most general tag that still tells the card apart; never a parent and its child on the same card.
- Ordered blocks use a hyphen: `1-Limits`, `2-Derivatives`. Dated nodes: `1914-1991---Age.of.Extremes`.
- One tag usually; 2–3 when the card truly sits in two places (a theory card about an author: the concept tag
  plus the author's school). Hard ceiling 6.
- Forbidden: vague tags (`Misc`, `Other`, `To.Organize`), cross-cutting namespaces (`author::`, `year::`,
  `level::`). An unclear card goes to the best path + `::To.Classify`.
- Working tags are separate from subject tags: `TEMP::<batch>` (a handle to move a batch, removed afterwards)
  and `Update::Monthly | Yearly | On.Event` for values that age (a policy rate, a tax table). Never use them as
  evidence that a subject is covered.

## Sweep each card in this order

1. **Time:** a date or named period that is a recall target → the history node of that period. A theory card
   that only mentions a year gets no period tag.
2. **Place:** the geography node only if the card is about the country as a territory.
3. **Exclusion:** anything before 2010 never goes under `Economics::Production&Markets` (that branch is current
   markets only).
4. **Authors and schools** named as owners of an idea → the school's dated node plus the subject tag.
5. **Intersection:** a card crossing 3 axes (author, period, country, sub-discipline) gets 3 tags.

## Boundaries that cause most mistakes

- Individual agents → micro; aggregates → macro. Inflation, interest and exchange-rate concepts →
  `Macroeconomics::Applied::Monetary.Economics`.
- Statistics and regression, even in an econometrics course → `Exact.Sciences::Quantitative::Statistics`.
- A company as the object → its company sheet plus the sector; as an example only → the sector.
- Economic history goes under Humanities (plus a macro or economic-thought tag), never under Economics alone.

## Re-tagging existing cards

Use `propose_update_note(note_id, tags=[...])` card by card, or in a batch after showing 4–6 examples of
`front → old tags → new tags` and asking once. Only tags change; the server re-reads each note before writing
and refuses if it changed since the preview.
