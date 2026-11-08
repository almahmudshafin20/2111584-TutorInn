from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.database import initialize_database
from backend.routers import posts, students, system, tutors

app = FastAPI(
    title="TutorInn API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)

# Initialize tables and keep the compatibility migration for existing records.
initialize_database()

app.include_router(system.router)
app.include_router(students.router)
app.include_router(tutors.router)
app.include_router(posts.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
