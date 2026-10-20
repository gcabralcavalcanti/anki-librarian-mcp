"""Settings, read from a TOML file (see anki-librarian.example.toml). Every default is the safe one."""

from __future__ import annotations

import fnmatch
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Taxonomy:
    roots: list[str] = field(default_factory=list)  # empty = no taxonomy check
    operational: list[str] = field(default_factory=list)  # extra allowed roots (e.g. TEMP, Radar)
    segment_pattern: str = r"^[A-Z0-9][A-Za-z0-9.&'-]*$"
    max_depth: int = 6
    required: bool = True  # every note needs at least one taxonomy tag


@dataclass
class Settings:
    anki_url: str = "http://127.0.0.1:8765"
    timeout_s: float = 10.0
    writable_decks: list[str] = field(default_factory=list)  # glob patterns; empty = nothing is writable
    allow_delete: bool = False
    allow_reschedule: bool = False
    approval: str = "elicit"  # elicit (ask the human through the MCP client) | cli | none (tests only)
    max_notes_per_plan: int = 50
    plan_ttl_minutes: int = 15
    similar_threshold: float = 0.85  # fronts this alike (character level) are flagged as similar
    retrieval_threshold: float = 0.45  # cosine similarity in the collection index that flags a similar card
    card_rules: str = "enforce"  # enforce | warn | off: size ceilings and front checks on basic cards
    basic_model: str = "Basic"
    cloze_model: str = "Cloze"
    agent_flags: list[int] = field(default_factory=lambda: [0, 4])  # 4 = blue; 1 (red) is the human's
    state_dir: Path = Path(".anki-librarian")
    taxonomy: Taxonomy = field(default_factory=Taxonomy)

    def deck_writable(self, deck: str) -> bool:
        return any(fnmatch.fnmatchcase(deck, p) for p in self.writable_decks)


def load(path: str | os.PathLike | None = None) -> Settings:
    """Load settings from `path`, $ANKI_LIBRARIAN_CONFIG, or ./anki-librarian.toml; defaults if none exists."""
    path = Path(path or os.environ.get("ANKI_LIBRARIAN_CONFIG") or "anki-librarian.toml")
    if not path.exists():
        return Settings()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    tax = Taxonomy(**raw.pop("taxonomy", {}))
    s = Settings(**{k: v for k, v in raw.items() if k in Settings.__dataclass_fields__}, taxonomy=tax)
    s.state_dir = Path(s.state_dir)
    if not s.state_dir.is_absolute():
        s.state_dir = path.parent / s.state_dir
    if s.card_rules not in ("enforce", "warn", "off"):
        raise ValueError(f"card_rules must be enforce, warn or off, not {s.card_rules!r}")
    if s.approval not in ("elicit", "cli", "none"):
        raise ValueError(f"approval must be elicit, cli or none, not {s.approval!r}")
    return s
