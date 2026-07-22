import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from helpers import FakeResponse, FakeSession  # noqa: E402


@pytest.fixture
def fake_session():
    """Factory for a :class:`FakeSession` over a queue of responses."""
    return FakeSession


@pytest.fixture
def fake_response():
    """Factory for a single :class:`FakeResponse`."""
    return FakeResponse
