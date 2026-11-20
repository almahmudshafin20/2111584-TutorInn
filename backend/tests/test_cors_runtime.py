"""Runtime CORS behaviour: only configured frontend origins receive CORS headers.

The CORS middleware is only mounted when TRUSTED_ORIGINS is set at import time, so the check runs in a
fresh interpreter with its own environment and does not depend on other test modules.
"""
import json, os, subprocess, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TRUSTED = "https://app.example.test"
UNTRUSTED = "https://evil.example.test"

PROBE = r'''
import json
from fastapi.testclient import TestClient
from app import main
client = TestClient(main.app)
def headers_for(origin):
    response = client.get("/api/docs", headers={"Origin": origin})
    return response.status_code, response.headers.get("access-control-allow-origin")
def preflight(origin):
    response = client.options("/api/auth/login", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    return response.status_code, response.headers.get("access-control-allow-origin")
print(json.dumps({
    "trusted": headers_for(TRUSTED), "untrusted": headers_for(UNTRUSTED),
    "preflight_trusted": preflight(TRUSTED), "preflight_untrusted": preflight(UNTRUSTED),
}))
'''


def test_only_configured_origins_receive_cors_headers(tmp_path):
    env = {
        **os.environ,
        "TRUSTED_ORIGINS": TRUSTED,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'cors-runtime.db'}",
        "JWT_SECRET": "test-only-jwt-secret-with-at-least-thirty-two-characters",
        "PASSWORD_PEPPER": "test-only-password-pepper-with-at-least-32-characters",
    }
    env.pop("VERCEL", None)
    script = f"TRUSTED = {TRUSTED!r}\nUNTRUSTED = {UNTRUSTED!r}\n" + PROBE
    completed = subprocess.run([sys.executable, "-c", script], cwd=BACKEND, env=env,
                               capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result["trusted"] == [200, TRUSTED]
    assert result["untrusted"][0] == 200 and result["untrusted"][1] is None
    assert result["preflight_trusted"][1] == TRUSTED
    assert result["preflight_untrusted"][1] is None
