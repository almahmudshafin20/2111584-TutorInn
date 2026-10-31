# TutorInn

TutorInn is a small tutoring platform MVP built with **React + TypeScript**, **FastAPI**, and **SQLAlchemy**. Students can manage student profiles, and tutors can manage tutor profiles and be discovered by name or subject.

## Core features

- Student CRUD: create, list/search, view one profile, update, and delete.
- Tutor CRUD: create, list/search/filter, view one profile, update, and delete.
- Separate Home, About, Tutoring Hub, and Task Details pages.
- Tutor and student listing workflow with compact cards, a dedicated Read Details view, and Interested / Not interested actions.
- Admin-only approve/reject endpoints protected by a backend `ADMIN_API_KEY` shared secret.
- REST API documentation through FastAPI's Swagger UI.
- SQLite for local development and PostgreSQL/Supabase through `DATABASE_URL` for persistent hosting.

> This MVP still has no user login or per-user ownership authorization. The Student/Tutor/Admin selector is for demonstration only, not identity verification. Admin approval/rejection is separately protected by the backend `ADMIN_API_KEY` environment variable; do not expose that secret in frontend environment variables or commit it to GitHub. For production, add real authentication, ownership checks, and per-user interest records. Configure a persistent PostgreSQL/Supabase database; serverless local SQLite storage is not durable.

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
| POST | `/api/posts` | Create tutor offer or student request |
| GET | `/api/posts` | List tutoring posts |
| GET | `/api/posts/{id}` | Read one tutoring post |
| PUT | `/api/posts/{id}` | Update tutoring post |
| DELETE | `/api/posts/{id}` | Delete tutoring post |
| POST | `/api/posts/{id}/confirm` | Record interest; does not approve the post |
| POST | `/api/posts/{id}/not-interested` | Withdraw interest |
| POST | `/api/posts/{id}/approve` | Admin-only approval; requires `X-Admin-Key` |
| POST | `/api/posts/{id}/reject` | Admin-only rejection; requires `X-Admin-Key` |
| POST | `/api/posts/{id}/withdraw` | Withdraw a post |

A duplicate email within the same profile type returns HTTP 409; an unknown ID returns HTTP 404; invalid input returns HTTP 422.

## Admin approval setup

Set `ADMIN_API_KEY` as a secret environment variable on the backend service. Keep the value private and do not prefix it with `VITE_` or expose it to browser code. In the MVP, select Admin in the role selector and enter the same key when prompted to approve/reject a request. If the backend variable is missing, approval/rejection intentionally returns HTTP 503; an invalid key returns HTTP 403. This shared-key flow is temporary and must be replaced with authenticated Admin accounts before production.

## Frontend pages

- `/` — Home
- `/about` — About
- `/posts` — Tutoring Hub (browse, create, read, edit, delete)
- `/task-details` — Interest tracking and Admin review queue
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
