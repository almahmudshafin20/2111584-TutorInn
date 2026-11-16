from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import initialize_database
from .routers import account, admin, auth, beta_requests, posts, profiles, students, system, tasks, tutors


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

app.include_router(auth.router)
app.include_router(account.router)
app.include_router(beta_requests.router)
app.include_router(system.router)
app.include_router(students.router)
app.include_router(tutors.router)
app.include_router(posts.router)
app.include_router(profiles.router)
app.include_router(admin.router)
app.include_router(tasks.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
