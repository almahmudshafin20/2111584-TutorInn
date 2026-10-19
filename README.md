# TutorInn

TutorInn is a small tutoring platform MVP built with **React + TypeScript**, **FastAPI**, and **SQLAlchemy**. Students can manage student profiles, and tutors can manage tutor profiles and be discovered by name or subject.

## Core features

- Student CRUD: create, list/search, view one profile, update, and delete.
- Tutor CRUD: create, list/search/filter, view one profile, update, and delete.
- Separate Home, About, and Task Details pages.
- REST API documentation through FastAPI's Swagger UI.
- SQLite for local development and PostgreSQL/Supabase through `DATABASE_URL` for persistent hosting.

> This assessment build currently provides profile CRUD without login or ownership-based authorization. Do not treat it as production-ready until authentication and authorization are added. For deployed use, configure a persistent PostgreSQL/Supabase database; serverless local SQLite storage is not durable.

## Requirements

- Python 3.10+
- Node.js 22+

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
```

The API runs at http://localhost:8000. Open http://localhost:8000/docs to inspect and test the endpoints. Local development creates `backend/tutorinn.db` automatically.

### 2. Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite URL shown in the terminal (normally http://localhost:5173). Vite forwards `/api` requests to FastAPI on port 8000.

## PostgreSQL / Supabase setup

Create a PostgreSQL database (Supabase is suitable), then set the `DATABASE_URL` environment variable for the backend. Use the provider's connection string and keep credentials private.

Example format:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

The backend normalizes `postgresql://` to the Psycopg SQLAlchemy driver. Set this variable in your local environment and in Vercel's backend environment variables. Do not commit a real connection string or secret to GitHub. The tables are created automatically at backend startup.

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/students` | List students; optional `?q=` search |
| POST | `/api/students` | Create student |
| GET | `/api/students/{id}` | Read one student |
| PUT | `/api/students/{id}` | Update student |
| DELETE | `/api/students/{id}` | Delete student |
| GET | `/api/tutors` | List tutors; optional `q`, `subject`, and `level` filters |
| POST | `/api/tutors` | Create tutor |
| GET | `/api/tutors/{id}` | Read one tutor |
| PUT | `/api/tutors/{id}` | Update tutor |
| DELETE | `/api/tutors/{id}` | Delete tutor |

A duplicate email within the same profile type returns HTTP 409; an unknown ID returns HTTP 404; invalid input returns HTTP 422.

## Frontend pages

- `/` — Home
- `/about` — About
- `/task-details` — Assessment task details
- `/tutors` — Search and manage tutor profiles
- `/tutors/{id}` — Tutor details
- `/students` — Manage student profiles
- `/students/{id}` — Student details

## Assessment test checklist

1. Create a student and confirm it appears in the list.
2. Open the student's details, edit the record, refresh, and confirm the changes persist.
3. Delete the student and confirm it disappears.
4. Repeat all five CRUD operations for tutors.
5. Try searching tutors by name/subject and filtering by subject or level through the API.
6. In DevTools Network or Postman, demonstrate request methods, payloads, status codes, and responses.
7. Test invalid input, duplicate email (409), and a missing ID (404).
8. Verify that the deployed backend uses a configured persistent PostgreSQL/Supabase database.

## Vercel

The existing `vercel.json` routes `/api/*` to the FastAPI backend and other paths to the Vite frontend. Add `DATABASE_URL` to the backend service's environment variables before deploying. Verify the actual deployment and build logs in Vercel; configuration in the repository alone does not prove that a deployment is working.
