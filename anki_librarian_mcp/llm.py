"""Small Claude API client used only by the demo pipeline (the server itself never calls a model).

Answers must match a JSON Schema and an optional rule check; a failing answer is retried once with the
complaints. Accepted answers are recorded, so the demo replays without a key and an identical request is never
paid twice. The key comes from ANTHROPIC_API_KEY and is never logged.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

MODEL = os.environ.get("ANKI_DEMO_MODEL", "claude-haiku-5-5")
PRICE_PER_MTOK = {"claude-haiku-5-5": (0.10, 0.50)}  # USD (input, output)
MAX_CALLS = 20


class NoRecording(RuntimeError):
    pass


def _key() -> str | None:
    if "ANTHROPIC_API_KEY" in os.environ:  # set, even empty, wins: empty means demo mode, no other lookup
        return os.environ["ANTHROPIC_API_KEY"] or None
    if os.name == "nt":  # set with setx after this terminal was opened
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                return winreg.QueryValueEx(k, "ANTHROPIC_API_KEY")[0] or None
        except OSError:
            return None
    return None


class LLM:
    def __init__(self, recordings: Path, live: bool = False, max_calls: int = MAX_CALLS):
        self.recordings = Path(recordings)
        self.recordings.mkdir(parents=True, exist_ok=True)
        key = _key() if live else None
        if live and not key:
            raise RuntimeError("--live needs ANTHROPIC_API_KEY")
        self.client = None
        if key:
            import anthropic

            self.client = anthropic.Anthropic(api_key=key, timeout=120.0, max_retries=3)
        self.max_calls = max_calls
        self.calls = self.replayed = self.tokens_in = self.tokens_out = 0
        self.recorded_cost = 0.0

    def ask(
        self, task: str, system: str, prompt: str, schema: dict, check: Callable | None = None, max_tokens: int = 16000
    ) -> dict:
        request = {"model": MODEL, "system": system, "prompt": prompt, "schema": schema, "max_tokens": max_tokens}
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        path = self.recordings / f"{task}-{key}.json"
        if path.exists():
            rec = json.loads(path.read_text(encoding="utf-8"))
            self.replayed += 1
            self.recorded_cost += self.cost(rec["usage"]["input_tokens"], rec["usage"]["output_tokens"])
            return rec["answer"]
        if self.client is None:
            raise NoRecording(f"no recorded answer for {task}; run with --live and ANTHROPIC_API_KEY set")
        user, used = prompt, [0, 0]
        for _ in range(3):
            if self.calls >= self.max_calls:
                raise RuntimeError(f"call cap reached ({self.max_calls})")
            self.calls += 1
            r = self.client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                thinking={"type": "adaptive"},
                output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
            )
            used = [used[0] + r.usage.input_tokens, used[1] + r.usage.output_tokens]
            self.tokens_in, self.tokens_out = (
                self.tokens_in + r.usage.input_tokens,
                self.tokens_out + r.usage.output_tokens,
            )
            text = next((b.text for b in r.content if b.type == "text"), "")
            try:
                answer = json.loads(text)
                jsonschema.validate(answer, schema)
                problems = check(answer) if check else []
            except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                answer, problems = {}, [f"invalid answer: {str(e)[:200]}"]
            if not problems:
                path.write_text(
                    json.dumps(
                        {
                            "task": task,
                            "model": MODEL,
                            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
                            "usage": {"input_tokens": used[0], "output_tokens": used[1]},
                            "answer": answer,
                        },
                        ensure_ascii=False,
                        indent=1,
                    ),
                    encoding="utf-8",
                )
                self.recorded_cost += self.cost(*used)
                return answer
            user = f"{prompt}\n\nYour previous answer was rejected:\n- " + "\n- ".join(problems) + "\nFix these points."
        raise ValueError(f"{task}: answer still failing checks: {problems}")

    @staticmethod
    def cost(tin: int, tout: int) -> float:
        p_in, p_out = PRICE_PER_MTOK.get(MODEL, (0.0, 0.0))
        return (tin * p_in + tout * p_out) / 1e6
