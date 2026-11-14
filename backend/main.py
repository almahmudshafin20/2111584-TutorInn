from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

try:
    from backend.database import initialize_database
    from backend.routers import admin, auth, beta_requests, posts, profiles, students, system, tutors
except ModuleNotFoundError:
    from database import initialize_database
    from routers import admin, auth, beta_requests, posts, profiles, students, system, tutors

app = FastAPI(
    title="TutorInn API",
    version="2.2.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)

initialize_database()

app.include_router(auth.router)
app.include_router(beta_requests.router)
app.include_router(system.router)
app.include_router(students.router)
app.include_router(tutors.router)
app.include_router(posts.router)
app.include_router(profiles.router)
app.include_router(admin.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
