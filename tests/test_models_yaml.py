from __future__ import annotations

from app.models_loader import load_tasks, task_model


def test_three_task_routes_and_no_langchain_import():
    tasks = load_tasks()
    assert set(tasks) == {"decide", "generate", "judge"}
    assert task_model("generate").provider == "openai"
    assert task_model("decide").temperature == 0.0
    import sys

    assert "langchain" not in sys.modules
