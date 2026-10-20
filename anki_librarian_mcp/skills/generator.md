---
name: generator
description: Write Anki cards from a plan (or directly from material) in three layers, within size limits, with questions that do not give away their answers.
---
# Generator

Few strong cards. Density comes from more atoms, never from bigger cards. Follow the plan's order: it becomes
the order in which new cards appear.

## Three layers

| Layer | Front starts with | What it holds | Weight ≤ | Back ≤ |
|---|---|---|---|---|
| Map | `[Map] Theme <br><br> question` | how the parts relate: cause, sequence, opposition, decision tree | 14 | 1750 chars |
| Macro | `[Macro] Theme <br><br> question` | one mechanism or argument; a concept macro = definition + 2 examples from different contexts | 10 | 1100 chars |
| Reconstruction atom | `Theme <br><br> question` | one causal link or distinction, 1–3 short sentences | 5 | 500 chars |
| Mnemonic atom | `Theme <br><br> question` | one fact; a date is never alone (say what happened) | 3 | 300 chars |

**Cognitive weight** = blocks (separated by `<br><br>`) + arrows (`→`) + distinct dates + numbers with a unit +
new proper names. The server computes it and refuses a card over its ceiling: split by sub-theme, or demote a
macro that holds several parallel ideas to a map.

Per strong block: 1–3 reconstruction atoms and 1–3 mnemonic atoms. Never mix a causal chain and several named
facts in one atom. A question asking for a list of 5 or more parallel items becomes several atoms. Material with
rival positions gets at least one discrimination card per contrast ("In X vs Y, what decides Z?").

## The front: never give the answer away

Read the front as if you did not know the answer: what should memory retrieve, and is it already written?
- No verdict in the question ("Why was the system so fragile?" → "How did low bank coverage affect the
  system's response to seasonal demand?").
- No count of the items ("Which three circumstances…" → "Which circumstances…"), unless the number is part of a
  name (Newton's three laws).
- History: no year or decade in the theme or the question; name the period, the date goes on the back.
- A map question does not list the structure of its own answer.
- Theme = `Subject: topic`, the same on every card of a slice, never listing the targets.
- Self-contained: no "and at 6%?", no "this bond", no reference to another card. Spell out acronyms. Authors go
  on the back ("For Keynes, …"), unless the author is the object.

## The back

- `<br><br>` between ideas; one paragraph per idea; sentences of 25 words or fewer.
- Every arrow states the mechanism ("the centre raises rates → capital leaves the periphery for the higher
  return").
- Bold (`<b>`, never `**`) only on the retrieval anchor: block titles in maps, the lead term of every item in a
  list, or 1–2 spans in prose.
- Rounded numbers in concept cards (~38k, about a third); exact values only when the number is the target.
- Use the material's own terms and notation. Never "according to the text".

**Math:** every formula inside `\(` `\)`, coupled to a sentence that says what it means. Inside math use `\lt`
and `\gt`, never a bare `<` or `>`. A reconstruction atom holds at most 2 derivation steps; a macro at most 4
(starting point → key step → decisive assumption → result).

## Before sending to the server

Each card passes five checks: focused (one thing), precise, consistent (same right answer every time),
tractable, effortful (not answerable from a cue or a yes/no guess). A card is worth making only if knowing it is
worth about ten minutes of future review.

Then call `propose_add_notes(deck, cards)` with `{front, back, tags}` per card (add `image: {url, credit}` to
attach a picture found with `search_images`). Show the preview: skipped duplicates, similar cards already in
the collection (with their text), weight per card, any refusal. The user approves; then `apply_plan`.

## Examples

```
[Map] Statistics: hypothesis testing <br><br> How does the logic of a hypothesis test fit together?
→ <b>Hypotheses:</b> a null (no effect) and an alternative. <br><br> <b>Test statistic:</b> a quantity with a
known distribution under the null. <br><br> <b>Decision:</b> reject when it falls in a region of probability
\(\alpha\) under the null. <br><br> <b>Reading:</b> a small p-value → the data are unlikely under the null, not
proof of the alternative.

[Macro] Econometrics: OLS <br><br> How does the residual-minimisation problem lead to the OLS estimator?
→ Start from the sum of squared residuals \(S(\beta) = (y - X\beta)'(y - X\beta)\). <br><br> → <b>first-order
condition:</b> the normal equations \(X'X\hat{\beta} = X'y\). <br><br> → with full column rank,
\(\hat{\beta} = (X'X)^{-1}X'y\).

Econometrics: OLS <br><br> Why is exogeneity decisive for reading \(\hat{\beta}\) as unbiased?
→ <b>Exogeneity</b> means \(E[u \mid X] = 0\). <br><br> With it the error drops out in expectation →
\(E[\hat{\beta}] = \beta\).

Biochemistry: citric acid cycle <br><br> Where in a eukaryotic cell does the citric acid cycle take place?
→ In the mitochondrial matrix.
```
