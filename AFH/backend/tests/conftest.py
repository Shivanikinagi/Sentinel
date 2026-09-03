"""Shared test fixtures. Every test gets an isolated in-memory Store."""
from __future__ import annotations

import pytest

from app.store import Store


@pytest.fixture
def store() -> Store:
    s = Store(":memory:")
    yield s
    s.close()
