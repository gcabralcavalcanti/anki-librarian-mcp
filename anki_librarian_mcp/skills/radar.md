---
name: radar
description: Weekly scan of current events by track; the user picks from a menu what becomes a card. Short-lived items expire on their own.
---
# Radar

A process, not a subject: there is no "Radar" deck tree. Each week covers one track; what is worth keeping goes
to an existing subject deck, and what only matters for a few weeks goes to a single buffer deck and expires.

## Three kinds of result

| Kind | Example | Where it goes | Tag |
|---|---|---|---|
| Short-lived | "the central bank cut the rate by 0.25 points" | buffer deck at the root | `TEMP::Expires::<YYYY-MM>` (two months ahead) |
| Update | an existing card whose number aged | stays where it is; the back is updated | `Update::Monthly` (or Yearly, On.Event) |
| Addition | a new lasting fact in a subject you already study | that subject's deck | none |

Mechanism cards (how something works) do not come from the radar; they do not age.

## The session (about two hours)

1. **Clean up:** list the buffer cards whose expiry month has passed; the user deletes them in Anki (the
   server never deletes by default).
2. **Update:** `find_notes("tag:Update::Monthly")`; for each, has the value changed? Show
   `note · front · current value · new value · dated source`; update with `propose_update_note`. A value
   without a source is "not confirmed", never estimated.
3. **Scan → menu:** read the track's sources and return a menu, one line per candidate: number · kind · the
   claim in one sentence · dated source · destination deck. Search the collection first (`find_notes`) and mark
   what already exists. About 1.5× the track's target, never three times. **No card is written in this step.**
4. **Generate:** only what the user ticked, through the generator, then `propose_add_notes` and approval.

## Tracks (one per week, in rotation)

| Track | Cards per round | Test |
|---|---|---|
| Finance, companies and macro | 6–8 | what the market is pricing |
| AI and technology | 4–6 | already usable, not a demo; who makes money |
| Science | 4 (cap 5) | can you say the finding aloud in one sentence without jargon? |
| Geopolitics and trade | 5–7 | what does it do to commodities or exchange rates? |
| Real estate and agribusiness | 6–8 | prices, credit, harvest |
| Sports, culture and popular talk | 2–3, mostly short-lived | would it come up in conversation this week? |

People cards only if all three hold: they decide or built something with their name on it; the name survives
the news (two independent sources in a year); the name works alone in a conversation. At most two per round.

Every claim carries a dated source. No source, no card.
