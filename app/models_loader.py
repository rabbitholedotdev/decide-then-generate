from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.settings import ROOT


@dataclass(frozen=True)
class TaskModel:
    name: str
    provider: str
    model: str
    temperature: float
    max_tokens: int


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def load_tasks(path: str | None = None) -> dict[str, TaskModel]:
    yaml_path = Path(path) if path else ROOT / "models.yaml"
    raw = _load_yaml(yaml_path)
    tasks: dict[str, TaskModel] = {}
    for name, spec in (raw.get("tasks") or {}).items():
        tasks[name] = TaskModel(
            name=name,
            provider=spec.get("provider", "openai"),
            model=spec["model"],
            temperature=float(spec.get("temperature", 0.0)),
            max_tokens=int(spec.get("max_tokens", 400)),
        )
    return tasks


def task_model(name: str) -> TaskModel:
    tasks = load_tasks()
    if name not in tasks:
        raise KeyError(f"unknown task {name!r}; known={sorted(tasks)}")
    return tasks[name]
