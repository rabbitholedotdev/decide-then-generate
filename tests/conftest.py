from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.catalog import default_catalog
from app.decider.mock import MockDecider
from app.generate.writer import TemplateWriter
from app.main import create_app
from app.orchestrator import Assistant
from app.rag.fixtures import FixtureRetriever
from app.sessions import MemorySessionStore


@pytest.fixture
def catalog():
    return default_catalog()


@pytest.fixture
def assistant(catalog):
    return Assistant(
        decider=MockDecider(catalog),
        writer=TemplateWriter(catalog),
        retriever=FixtureRetriever(),
        catalog=catalog,
        sessions=MemorySessionStore(),
    )


@pytest.fixture
def client(assistant):
    return TestClient(create_app(assistant=assistant))
