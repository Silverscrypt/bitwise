import asyncio

import pytest

from tests.fakes import World


@pytest.fixture
def world():
    return World()


@pytest.fixture
def run():
    """Run a coroutine to completion (avoids a pytest-asyncio dependency)."""
    return asyncio.run
