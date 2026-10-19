"""Plans (dry runs waiting for a human) and the audit log, both kept as plain files in the state folder."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path


def now() -> datetime:
    return datetime.now(timezone.utc)


class Audit:
    """Append-only JSON lines: every proposal, approval, rejection, block, application and failure."""

    def __init__(self, state_dir: Path):
        self.path = Path(state_dir) / "audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **data) -> None:
        line = {"ts": now().isoformat(timespec="seconds"), "event": event, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    def tail(self, n: int = 20) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines()[-n:]]


class PlanStore:
    """status: pending -> approved -> applied, or rejected / expired / invalid (has errors, cannot be approved)."""

    def __init__(self, state_dir: Path, ttl_minutes: int = 15):
        self.path = Path(state_dir) / "plans.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(minutes=ttl_minutes)

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def _save(self, plans: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(plans, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def create(self, kind: str, steps: list[dict], preview: dict, errors: list[str]) -> dict:
        plans = self._load()
        pid = "p-" + secrets.token_hex(3)
        plan = {"id": pid, "kind": kind, "created": now().isoformat(timespec="seconds"),
                "expires": (now() + self.ttl).isoformat(timespec="seconds"),
                "status": "invalid" if errors else "pending", "errors": errors,
                "preview": preview, "steps": steps}
        plans[pid] = plan
        self._save(plans)
        return plan

    def get(self, pid: str) -> dict | None:
        plans = self._load()
        plan = plans.get(pid)
        if plan and plan["status"] in ("pending", "approved") and now() > datetime.fromisoformat(plan["expires"]):
            plan["status"] = "expired"
            self._save(plans)
        return plan

    def set_status(self, pid: str, status: str, **extra) -> dict:
        plans = self._load()
        plans[pid].update(status=status, **extra)
        self._save(plans)
        return plans[pid]

    def list(self, status: str | None = None) -> list[dict]:
        out = [self.get(pid) for pid in self._load()]
        return [p for p in out if p and (status is None or p["status"] == status)]
