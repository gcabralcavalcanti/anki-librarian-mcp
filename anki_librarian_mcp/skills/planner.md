---
name: planner
description: Plan a deck before writing cards. PLAN mode for new material; RECONCILE mode searches the collection and separates what is missing from what you already have.
---
# Planner

Never writes cards. Two modes:
- **PLAN** (new material): builds the deck plan; does not read the collection.
- **RECONCILE** (a harvest, or "what do I already have on this?"): searches the collection first, then plans
  only the gaps.

## The plan

**Register** (always a blend, in percentages):
TP theoretical-deep (full model, derivations) · TO theoretical-objective (what matters and what it is for) ·
DP decision-practical (who does it, cost, deadline, risk, what to avoid, what changes the decision) ·
CH critical-historical (what an author or event did in the world) · MN mnemonic (facts to automate).

**Subject type** decides the card form: quantitative → when and why a method, which assumption carries each
step, what breaks without it · history → time anchors and causal chains · comparative → discrimination
between rival positions · procedural → trigger → action, where to find it · languages → form ↔ meaning.

**Layers per nucleus:** map (how the parts relate), macro (mechanism or argument), atoms (one link or one fact).
Mnemonic material often needs only atoms; theory needs all three.

Default blends: quantitative exam TP 60 · MN 25 · TO 15 · understand a method TO 55 · TP 30 · MN 15 · meeting
about a sector DP 45 · TO 30 · MN 25 · investment or project DP 40 · TO 35 · TP 25 · software skill
DP 55 · MN 30 · TO 15.

```
## Deck plan: <topic>
Register: <blend> · Subject type: <...> · Objective: <...> · Coverage: <~X% of the chosen angle; left out: ...>
### Skeleton        (half a page, arrows)
### Nuclei and layers
### Target count    (by layer; must match the blend)
### Essential core  (the cards that alone give the skeleton)
### Order           (deep-study: general → specific; quick-prep: most likely to be asked first)
```

## Reconcile: search before planning

1. **Collect candidates.** Only concepts with real engagement become candidates: a doubt, a marker, or a
   correction or decision in the source. A mere mention goes to OUT OF SCOPE (shown, never silently dropped).
2. **Search the collection, both routes, always:**
   - by tag: `find_notes("tag:Economics::Macroeconomics*")`;
   - by keyword, with synonyms and the spelled-out acronym: `find_notes("\"policy rate\" OR \"interest rate\"")`.
   The server also runs its own similarity search over the whole collection when you propose cards.
3. **Judge each concept:** is there a card whose recall target is this concept, at the depth needed?
   Yes → ALREADY HAVE (with its note id). No → GAP. A shallow card when depth is needed → GAP for the missing
   layer only; the old card stays.
4. **Checkpoint (the only stop):** show GAP / ALREADY HAVE / OUT OF SCOPE and let the user move items.

Doubts are a protected flow: each doubt becomes a direct card (doubt = front, resolution = back), kept
verbatim, unless an existing card should just be adjusted (`propose_update_note`). Count them: every doubt
in the input must end as a card, an adjustment, ALREADY HAVE or OUT OF SCOPE.

For an exam within a week, size the batch by load, not by count: useful hours × 20 cognitive-weight points.
