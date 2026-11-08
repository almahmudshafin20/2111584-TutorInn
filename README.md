# TutorInn

TutorInn is a tutoring platform MVP built with **React + TypeScript**, **FastAPI**, and **SQLAlchemy**. Students can discover tutors, tutors can present multiple teaching subjects, and both sides can publish tutoring opportunities and respond independently.

## Core features

- Student and Tutor profile CRUD directly from their respective directories.
- Selected demo profile stored in browser local storage as `tutorinn-profile-id` and `tutorinn-profile-type`; a profile switcher is available in the navigation.
- Multiple subjects on Student profiles, Tutor profiles, and tutoring posts. Subjects are stored as structured lists and rendered separately.
- Tutoring posts are associated with the specific selected author profile.
- Interested and Not Interested responses are stored separately for every post/profile pair.
- Interested responses enter an individual Admin review queue; Not Interested responses do not require approval and hide the post only from that profile's active feed.
- Profile response history, including the ability to change a response.
- Admin review endpoints protected by a backend `ADMIN_API_KEY`.
- Separate Home, About, Tutoring Hub, My Responses, Admin Review, Student Profiles, and Tutor Profiles pages.
- FastAPI Swagger UI at `/api/docs`.

> **Demo identity limitation:** TutorInn does not currently have user authentication. The selected profile ID/type is supplied by the browser and is not proof of identity. API ownership checks prevent accidental cross-profile actions in the demo workflow, but they are not production-grade security. Add real authentication and server-verified ownership before public production use. The Admin review queue is separately protected by `ADMIN_API_KEY`; never expose this secret in frontend environment variables or commit it to GitHub.

## Requirements

- Python 3.10+
- Node.js 22+

## Run locally

### Backend

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

The API runs at http://localhost:8000. Open http://localhost:8000/api/docs to inspect endpoints. Local development creates `backend/tutorinn.db` automatically.

### Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally http://localhost:5173). Vite forwards API requests to FastAPI.

## Database configuration and migration

Set `DATABASE_URL` to a PostgreSQL connection URL for persistent hosting. SQLite is used for local development. Example format:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

The backend normalizes PostgreSQL URLs for Psycopg. Tables are created at startup, and additive startup migrations add the new subject and post-owner columns to existing databases.

- Existing single-subject profile/post text is retained and exposed as a one-item subject list when it is not already structured.
- Existing posts are deliberately left with a null author profile because the original creator profile cannot be inferred safely.
- Existing legacy interest summary fields remain for compatibility; new responses are stored in `interest_responses`.
- Deleting a profile also deletes its authored posts and related responses, after the user confirms in the UI.

Keep database credentials private. Configure a persistent PostgreSQL database for deployments; serverless local SQLite storage is not durable.

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/subjects` | List subjects currently in use |
| GET / POST | `/api/students` | List or create Student profiles |
| GET / PUT / DELETE | `/api/students/{id}` | Read, update, or delete a Student profile |
| GET / POST | `/api/tutors` | List or create Tutor profiles; supports subject and level filters |
| GET / PUT / DELETE | `/api/tutors/{id}` | Read, update, or delete a Tutor profile |
| GET / POST | `/api/posts` | List or create tutoring posts |
| GET / PUT / DELETE | `/api/posts/{id}` | Read, update, or delete a tutoring post |
| POST | `/api/posts/{id}/response` | Set or change the selected profile's Interested / Not Interested response |
| GET | `/api/responses` | List responses belonging to the selected profile |
| GET | `/api/admin/responses` | Admin list of Interested responses by review status |
| POST | `/api/responses/{id}/approve` | Approve one Interested response |
| POST | `/api/responses/{id}/reject` | Reject one Interested response |

Profile CRUD does not depend on the currently selected profile, so profiles can be edited or deleted directly from their directory pages. Creating posts, changing responses, and managing an authored post requires the selected profile headers:

- `X-TutorInn-Profile-ID`
- `X-TutorInn-Profile-Type` (`student` or `tutor`)

The two headers represent demo selection only and are not authentication.

## Admin review setup

Set `ADMIN_API_KEY` as a secret environment variable on the backend. In the Admin Review page, enter the same key when prompted. If it is missing, Admin endpoints return HTTP 503; an invalid key returns HTTP 403. Do not expose the secret through a `VITE_` variable.

## Frontend routes

- `/` — Home
- `/about` — About
- `/posts` — Tutoring Hub
- `/task-details` — Selected profile's response history
- `/task-details?id={id}` — Tutoring post details and response actions
- `/admin` — Individual Interested response review
- `/tutors` — Tutor directory and management
- `/tutors/{id}` — Tutor details
- `/students` — Student directory and management
- `/students/{id}` — Student details

## Verification

The repository CI workflow builds the TypeScript frontend and runs backend API workflow tests for profile ownership, independent responses, admin review, multiple subjects, and safe deletion behavior.

## Vercel

The existing `vercel.json` routes `/api/*` to the FastAPI backend and other paths to the Vite frontend. Add `DATABASE_URL` and `ADMIN_API_KEY` to backend environment variables before deploying. Verify actual deployment status and logs in Vercel; repository configuration alone does not prove a deployment is working.
