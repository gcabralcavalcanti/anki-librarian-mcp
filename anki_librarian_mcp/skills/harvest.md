---
name: harvest
description: Debrief study material, a finished project or a conversation into "what I learned and what I asked", grouped by theme, before any card is planned.
---
# Harvest

Turns material into a debrief. Does not write cards and does not touch Anki. Run it only when asked.

## 1. Classify before extracting

Decide what the material is, because that decides what is worth keeping. A direct instruction in the request
("only theory", "for the interview") wins over the classification.

| Style | Signal | Story cards | Theory | Tools and commands |
|---|---|---|---|---|
| A · code or AI project | a folder with code or agents | main output | only what explains the architecture | only what you reuse elsewhere |
| B · client or business case | a deliverable for someone | the case as a story | concepts, rules, anchor numbers | never |
| C · quantitative coursework | analysis code, a graded assignment | only if it becomes a CV line | main output | reusable library or command |
| D · theoretical study | reading, course, lecture notes | never | only output | never |
| E · interview or selection process | a date and a company | likely question → your answer | only what the test covers | never |
| F · practical life | paperwork, repairs, a procedure | never | only if broadly useful | step by step |

**Objective** (written in the header; it sets the order downstream):
`quick-prep` (meeting, exam soon: most important first, mark the survival kit) ·
`deep-study` (default: foundation → mechanism → detail) · `reference` (thematic order).

**Lens:** one dominant, at most one secondary: technical-quantitative · decision/business · meeting/argument ·
procedural/tools · legal-institutional. Cut what the dominant lens does not use.

## 2. Extract

- From a conversation: explicit questions, the places where you asked for a correction or rephrased, "aha"
  moments, new terms, tools used, errors and how they were solved, decisions and why.
- From documents and code: argument structure, terms, numbers and dates that carry the piece, the reasons
  behind choices.
- One concept per bullet, anchor first. Keep the logic of use, not arbitrary identifiers. Note where each item
  came from. Never invent a learning or a resolution.
- Two packages never mixed: **personal** (your own story, numbers and dates) and **repertoire** (knowledge
  that holds outside the project). They go to different decks.

Markers, only where they help: `[REVERSE]` two-way item (command ↔ what it does) · `[APPLIED]` learn the
logic, not the identifier · `[VERIFY]` may already be in the collection.

## 3. Output

```markdown
# Harvest: <material>
> Source: <...> · Style: <A–F> · Objective: <quick-prep | deep-study | reference> · Lens: <...>
> Outputs: stories <n> · theory <n> · tools <n>

## <Theme inferred from the material> · theory
- **<anchor>**: short development. [marker]  (context: where it appeared)

## Doubts I raised (and how they were resolved)
- **<doubt>** → <resolution in 1–2 lines>

## Doubts still open
- <doubt with no clear answer>
```

The two doubt sections are always present: the planner treats every doubt as a card candidate. Close by
stating the classification in one line so it can be corrected with one word, then continue to the planner
in reconcile mode unless asked to stop.
