# anki-librarian-mcp

Lets Claude turn your study material into Anki flashcards and manage your collection, without ever writing
anything you have not approved.

**[Live demo](https://gcabralcavalcanti.github.io/anki-librarian-mcp/)**: the step-by-step simulation, built from this repository on every push.

![Built with AI assistance](https://img.shields.io/badge/built%20with-AI%20assistance-6b46c1)
![Fictitious demo data](https://img.shields.io/badge/data-practice%20collection-555)

![The two examples, side by side: material, debrief, plan](docs/simulation-overview.png)

## What it shows

- **From notes to cards in one request.** Claude sums up what the material teaches, plans the cards, writes them
  and tags them, shown step by step for dense econometrics notes and for a business case.
- **No duplicates.** Before planning, it searches your whole collection and shows the card you already have.
- **Nothing is written without you.** Every change is a plan you approve first; deleting and rescheduling stay off
  unless you turn them on.

## Run it

```
pip install -r requirements.txt
python demo.py
```

Runs without an API key, replaying recorded answers. Set `ANTHROPIC_API_KEY` and add `--live` to call Claude live.
It uses a practice collection; your Anki is not touched.

## How I use it

Most of my cards come from a weekly radar of news and data by topic, prepared by a scheduled task on Thursday
night; I pick from its menu and approve the cards. The rest come from quick questions, the end of a project and
dense study material. The radar does not run by itself: you ask for it or schedule it
([how](docs/how-it-works.md#schedule-the-radar)).

## More

- [How it works](docs/how-it-works.md): how I use it, each step, the safety rules, installing it for Claude
  Desktop or Claude Code, and how to start on your own collection with a test deck.
- [Runbook](RUNBOOK.md): commands, updating, and what to do when something breaks.
- The other side of the flashcards, how much review time each deck needs in the week, is in
  [personal-ai-agents](https://github.com/gcabralcavalcanti/personal-ai-agents) (study blocks).

## Limits

- Pictures only, no audio or video.
- "Similar" means shared words and phrases; a card on the same idea in completely different words can be missed.
- Tested against a practice collection that behaves like Anki; try it on a test deck of your own first.

## How AI was used

I use Claude (Claude Code and the API) for coding, review and documentation. The questions, modelling choices,
validation and conclusions are mine.

## License

MIT, Guilherme Cabral.
