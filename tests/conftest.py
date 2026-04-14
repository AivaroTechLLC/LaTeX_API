import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the tests have a stable API key regardless of any local .env file.
# This must match the API_KEY used in assertions in test_api.py and test_compile.py.
os.environ.setdefault("API_KEY", "replace-with-secure-key")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from latex_compile_service.app import app


@pytest.fixture(autouse=True, scope="session")
def reset_settings_cache():
    from latex_compile_service.config import clear_settings_cache

    clear_settings_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
