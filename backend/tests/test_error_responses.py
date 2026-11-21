"""Error responses must be consistent and must never expose internal details."""
import asyncio
import json
import os
import sys
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('error-response-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from starlette.requests import Request
from app import main
from app.database import initialize_database
initialize_database()
client = TestClient(main.app)


def test_unhandled_exception_returns_generic_500_without_internal_details():
    scope = {"type": "http", "method": "GET", "path": "/api/example", "headers": []}
    response = asyncio.run(main.unhandled_exception_handler(
        Request(scope), RuntimeError("database password=hunter2 at /srv/private/trace.py"),
    ))
    assert response.status_code == 500
    body = json.loads(response.body)
    assert body == {"detail": "Internal server error"}
    text = response.body.decode()
    assert "hunter2" not in text
    assert "trace" not in text
    assert "Traceback" not in text


def test_validation_errors_keep_the_standard_detail_shape():
    response = client.post("/api/auth/login", json={})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_http_errors_keep_the_standard_detail_shape_without_stack_traces():
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"detail"}
    assert "Traceback" not in response.text
