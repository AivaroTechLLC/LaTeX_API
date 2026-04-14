import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from latex_compile_service.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
