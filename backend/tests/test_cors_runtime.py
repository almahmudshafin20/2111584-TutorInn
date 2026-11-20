"""Runtime CORS: only configured frontend origins receive CORS headers. Runs in a subprocess because the
middleware is attached when the app module is imported, and the origin list comes from the environment."""
import json, os, subprocess, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TRUSTED = "https://tutorinn.example.test"
UNTRUSTED = "https://evil.example.test"

PROBE = r'''
import json
from fastapi.testclient import TestClient
from app import main
client = TestClient(main.app)
def origin_headers(origin, path, method):
    if method == "OPTIONS":
        return client.options(path, headers={"Origin": origin, "Access-Control-Request-Method": "POST"}).headers
    return client.get(path, headers={"Origin": origin}).headers
print(json.dumps({
    "trusted_get": origin_headers("%(trusted)s", "/api/docs", "GET").get("access-control-allow-origin"),
    "untrusted_get": origin_headers("%(untrusted)s", "/api/docs", "GET").get("access-control-allow-origin"),
    "untrusted_preflight": origin_headers("%(untrusted)s", "/api/auth/login", "OPTIONS").get("access-control-allow-origin"),
    "trusted_preflight": origin_headers("%(trusted)s", "/api/auth/login", "OPTIONS").get("access-control-allow-origin"),
}))
''' % {"trusted": TRUSTED, "untrusted": UNTRUSTED}


def test_only_configured_origins_receive_cors_headers():
    env = dict(os.environ)
    env["TRUSTED_ORIGINS"] = TRUSTED
    env.setdefault("DATABASE_URL", f"sqlite:///{BACKEND / 'tests' / 'cors-runtime-test.db'}")
    env.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
    env.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
    result = subprocess.run([sys.executable, "-c", PROBE], cwd=BACKEND, env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout.strip().splitlines()[-1])
    assert observed["trusted_get"] == TRUSTED
    assert observed["trusted_preflight"] == TRUSTED
    assert observed["untrusted_get"] is None
    assert observed["untrusted_preflight"] is None
