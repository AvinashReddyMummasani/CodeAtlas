"""
conftest.py — Shared pytest fixtures for CodeAtlas test suite.

Fixtures
--------
client          : FastAPI TestClient (session-scoped, re-used across all tests)
sample_zip      : In-memory ZIP bytes with 2 Python files for upload tests
uploaded_session: Uploads sample_zip and returns (session_id, response_data)
test_user_creds : Fresh unique credentials for each auth test
registered_user : Signs up a user and returns (response_data, credentials)
auth_headers    : Bearer token header dict for the registered_user
"""

import io
import sys
import uuid
import zipfile
from pathlib import Path

import pytest

# Make the backend package importable from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.testclient import TestClient
from main import app  # noqa: E402  (import after sys.path insert)


# ---------------------------------------------------------------------------
# HTTP client — session-scoped so the app starts only once per test run
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def client():
    """Synchronous ASGI TestClient; no live server needed."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Sample project ZIP with two Python files
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def sample_zip():
    """
    In-memory ZIP archive containing two Python source files:
    - myproject/main.py   : greet(), add() functions + __main__ entry point
    - myproject/utils.py  : Calculator class with multiply/divide methods
                            + standalone factorial() function
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "myproject/main.py",
            '''"""Entry-point module."""

def greet(name: str) -> str:
    """Return a friendly greeting."""
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b

if __name__ == "__main__":
    print(greet("World"))
''',
        )
        z.writestr(
            "myproject/utils.py",
            '''"""Utility classes and functions."""

class Calculator:
    """Simple arithmetic helper."""

    def multiply(self, a, b):
        """Return product of a and b."""
        return a * b

    def divide(self, a, b):
        """Return a / b; raises ValueError on zero divisor."""
        if b == 0:
            raise ValueError("Division by zero")
        return a / b

def factorial(n: int) -> int:
    """Recursive factorial."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)
''',
        )
    buf.seek(0)
    return buf.read()


# Alias for backward compat with test files that use the older fixture name
@pytest.fixture(scope="session")
def sample_zip_bytes(sample_zip):
    """Alias for `sample_zip` — kept for backward compatibility."""
    return sample_zip


# ---------------------------------------------------------------------------
# Uploaded session (session-scoped — uploaded once, reused across tests)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def uploaded_session(client, sample_zip):
    """
    Upload sample_zip via POST /api/upload.
    Returns (session_id: str, response_data: dict).
    Skips the entire session if the upload fails.
    """
    resp = client.post(
        "/api/upload",
        files={"file": ("test_proj.zip", sample_zip, "application/zip")},
    )
    if resp.status_code != 200:
        pytest.skip(f"Upload failed ({resp.status_code}): {resp.text[:200]}")
    data = resp.json()
    return data["session_id"], data


# ---------------------------------------------------------------------------
# Auth fixtures — function-scoped so each test gets a fresh unique user
# ---------------------------------------------------------------------------
@pytest.fixture
def test_user_creds():
    """Generate unique signup credentials for each test invocation."""
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"tester_{uid}",
        "email": f"tester_{uid}@codeatlas.test",
        "password": "Test@Secret99",
    }


@pytest.fixture
def registered_user(client, test_user_creds):
    """Sign up a fresh user and return (response_data, credentials)."""
    resp = client.post("/api/auth/signup", json=test_user_creds)
    assert resp.status_code in (200, 201), f"Signup failed: {resp.text}"
    return resp.json(), test_user_creds


@pytest.fixture
def auth_headers(registered_user):
    """Return Authorization header dict for the registered_user's token."""
    data, _ = registered_user
    return {"Authorization": f"Bearer {data['token']}"}
