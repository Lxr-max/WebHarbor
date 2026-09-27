import pytest
import _support

@pytest.fixture(scope="session", autouse=True)
def portable_reviewed_fixtures():
    _support.prepare_fixtures()
