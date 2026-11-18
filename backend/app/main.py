from contextlib import asynccontextmanager
import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import initialize_database
from .routers import account, admin, auth, beta_requests, posts, profiles, students, system, tasks, groups, tutors, moderation, email_verification


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize the database when the API process starts."""
    initialize_database()
    yield


app = FastAPI(
    title="TutorInn API",
    version="2.3.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# Cross-origin browser access is limited to explicitly configured trusted origins.
# Same-origin deployments do not need CORS configuration.
def parse_trusted_origins(raw: str) -> list[str]:
    origins = []
    for value in raw.split(","):
        origin = value.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError("Each trusted origin must be an exact http(s) origin without a path, query or fragment.")
        if "*" in origin:
            raise RuntimeError("Trusted origins must not contain wildcards when credentials are enabled.")
        if origin not in origins:
            origins.append(origin)
    return origins


trusted_origins = parse_trusted_origins(
    os.getenv("TRUSTED_ORIGINS", os.getenv("FRONTEND_ORIGIN", ""))
)
if trusted_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=trusted_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        max_age=600,
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    connect_sources = " ".join(["'self'", *trusted_origins])
    # FastAPI's built-in Swagger UI and ReDoc pages load their bundles from
    # jsDelivr and include a small inline initialization script. Keep the
    # broader API policy strict; relax only these documentation HTML routes.
    is_api_docs_page = request.url.path in {"/api/docs", "/api/redoc"}
    script_sources = "'self'"
    style_sources = "'self' 'unsafe-inline'"
    if is_api_docs_page:
        script_sources += " https://cdn.jsdelivr.net 'unsafe-inline'"
        style_sources += " https://cdn.jsdelivr.net"
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        f"form-action 'self'; img-src 'self' data: https:; style-src {style_sources}; "
        f"script-src {script_sources}; connect-src {connect_sources}; font-src 'self' data: https:",
    )
    if os.getenv("ENVIRONMENT", "").lower() == "production" or os.getenv("VERCEL") == "1":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

app.include_router(auth.router)
app.include_router(email_verification.router)
app.include_router(password_resets.router)
app.include_router(account.router)
app.include_router(beta_requests.router)
app.include_router(system.router)
app.include_router(students.router)
app.include_router(tutors.router)
app.include_router(posts.router)
app.include_router(profiles.router)
app.include_router(admin.router)
app.include_router(moderation.router)
app.include_router(tasks.router)
app.include_router(groups.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
