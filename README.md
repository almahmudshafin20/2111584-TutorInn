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

## Project architecture and code organization

> **Architecture status:** The sections below describe the planned Beta target architecture. They are documentation and design guidance, not a statement that the folders, modules, authentication, or features already exist. The current MVP implementation and its run instructions are documented below and remain the source of truth until the refactor is completed.

### Implemented structure on this refactor branch

The following organization is implemented in this refactor branch while retaining the existing MVP routes and demo-profile workflow. It is separate from the larger Beta target shown below.

```text
backend/
├── main.py                    # FastAPI app setup and router registration
├── database.py                # SQLAlchemy engine, session dependency and MVP schema initialization
├── dependencies.py            # Demo-profile and Admin API-key dependencies
├── models.py                  # SQLAlchemy database models and subject helpers
├── schemas.py                 # Pydantic request/response validation
├── crud.py                    # Existing MVP business rules and database operations
├── routers/
│   ├── system.py              # Health, subjects and hello endpoints
│   ├── students.py            # Student profile endpoints
│   ├── tutors.py              # Tutor profile endpoints
│   ├── posts.py               # Tutoring posts and profile responses
│   ├── profiles.py            # Approved-match profile endpoint
│   └── admin.py               # Admin review queue and approve/reject endpoints
└── tests/

frontend/src/
├── components/
│   ├── CurrentRoleSelector.tsx
│   ├── Layout.tsx              # Compatibility re-export
│   ├── SiteHeader.tsx
│   ├── SiteFooter.tsx
│   └── SubjectPicker.tsx
├── context/
│   └── ThemeContext.tsx
├── hooks/
│   └── useSelectedProfile.ts
├── layouts/
│   └── AppLayout.tsx
├── pages/                      # One page module per current route/screen
├── services/
│   ├── api.ts                  # Shared HTTP client and Admin header helper
│   ├── session.ts              # Demo-profile browser storage
│   └── posts.ts                # Post pagination and display-number helpers
├── types/
│   ├── domain.ts               # Current Student, Tutor, Post and Response types
│   ├── forms.ts
│   └── index.ts                # Existing shared types retained for compatibility
├── shared.tsx                  # Backward-compatible exports; new code should import focused modules
├── App.tsx                     # Route/page selection
├── main.tsx
└── index.css
```

#### Frontend request and component flow

- `App.tsx` selects the page for the current URL and uses the dedicated `layouts/AppLayout.tsx` for the not-found screen.
- A page composes focused UI components and the shared `AppLayout`.
- Page components call feature functions from `services/` or the shared `services/api.ts` HTTP client.
- `api.ts` adds the selected demo-profile headers when present, sends the request, parses API errors, and returns typed response data.
- `session.ts` reads/writes the selected demo profile in browser local storage. This is a demo identity mechanism, not secure authentication.
- Shared TypeScript domain contracts live in `types/domain.ts`. Backend validation remains authoritative.

The old `shared.tsx` module is retained as a compatibility barrel so existing imports can continue working during incremental migration. New page/component code should import from the focused module that owns the behavior.

#### Backend request, validation and data flow

```text
HTTP request
  -> FastAPI router (backend/routers/)
  -> FastAPI dependencies (backend/dependencies.py)
  -> Pydantic input validation (backend/schemas.py)
  -> CRUD/business workflow (backend/crud.py)
  -> SQLAlchemy model + database session
  -> Pydantic response model
  -> HTTP response
```

- `main.py` creates the FastAPI application and registers the focused routers.
- `routers/` defines endpoint paths, HTTP methods, dependencies, status codes and response models. Route handlers delegate business/data work to `crud.py`.
- `schemas.py` validates and normalizes incoming payloads and defines public response shapes. Public Student/Tutor response schemas intentionally omit contact details.
- `crud.py` currently owns the MVP business rules and SQLAlchemy reads/writes, including profile CRUD, post ownership, responses and Admin match review. This is an intentional existing boundary permitted by `AGENTS.md`; separate service/repository modules should be introduced when the next feature scope justifies the split, not as empty layers.
- `models.py` defines persisted SQLAlchemy entities and subject normalization helpers.
- `database.py` configures the engine/session and currently performs MVP schema initialization/compatibility additions.
- `dependencies.py` validates selected demo-profile headers and the Admin API key. These are not JWT authentication or production-grade account authorization.

#### Current API route groups

| Router | Current endpoints |
|---|---|
| System | `GET /api/health`, `GET /api/subjects`, `GET /api/hello` |
| Students | `POST/GET /api/students`, `GET/PUT/DELETE /api/students/{student_id}` |
| Tutors | `POST/GET /api/tutors`, `GET/PUT/DELETE /api/tutors/{tutor_id}` |
| Posts | `POST/GET /api/posts`, `GET/PUT/DELETE /api/posts/{post_id}`, post response and legacy response actions, `GET /api/responses` |
| Profiles | `GET /api/profiles/approved-matches` |
| Admin | `GET /api/admin/matches`, `GET /api/admin/responses`, `POST /api/responses/{response_id}/approve`, `POST /api/responses/{response_id}/reject` |

All existing endpoint paths and methods are retained by this refactor. Swagger/OpenAPI remains available at `/api/docs`.

#### Data validation responsibilities

- Frontend input controls provide immediate user feedback and TypeScript types describe expected data shapes; neither is a security boundary.
- FastAPI/Pydantic schemas in `backend/schemas.py` enforce server-side field constraints, normalize email/subject values, and validate request payloads.
- CRUD workflows in `backend/crud.py` enforce cross-field and business rules such as duplicate profile emails, required tutor/listing subjects, post ownership, valid response direction, and review-state transitions.
- SQLAlchemy models in `backend/models.py` define database columns, uniqueness constraints and persisted relationships/identity fields.
- Database constraints remain the final persistence-level protection for uniqueness and integrity.

#### MVP behavior preserved by the refactor

- Existing Student and Tutor CRUD and public profile response shapes.
- Existing tutoring-post creation, listing, editing, deletion and pagination.
- Existing selected-profile demo workflow and browser storage keys.
- Existing independent Interested/Not Interested responses and Admin review process.
- Existing API paths, HTTP methods, status codes, request/response schemas and `/api/docs`.
- Existing database tables and records; this refactor does not introduce a schema migration.

> **Not implemented by this structural refactor:** JWT login/refresh, real Student/Tutor/Admin accounts, production RBAC, security-event monitoring, session revocation, account banning, tutor verification, or the full Beta Admin dashboard. Those remain Beta roadmap requirements. The selected-profile headers and Admin API key must not be described as equivalent to real user authentication.

### Target Beta repository structure

The following is the intended direction. The exact module boundaries may be adjusted after inspecting the current source files and moving existing functionality safely.

```text
TutorInn/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                 # Configuration, security, permissions, dependencies
│   │   ├── database/             # Database connection and declarative base
│   │   ├── models/               # SQLAlchemy database models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── routers/              # FastAPI endpoint definitions
│   │   ├── services/             # Business rules and use cases
│   │   └── repositories/         # Database query and persistence operations
│   ├── alembic/                  # Versioned database migrations
│   ├── tests/
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── common/
│       │   ├── auth/
│       │   ├── admin/
│       │   ├── student/
│       │   ├── tutor/
│       │   ├── requests/
│       │   └── layout/
│       ├── pages/
│       │   ├── HomePage/
│       │   ├── AboutPage/
│       │   ├── LoginPage/
│       │   ├── SignupPage/
│       │   ├── StudentDashboard/
│       │   ├── TutorDashboard/
│       │   ├── AdminDashboard/
│       │   ├── StudentProfilePage/
│       │   ├── TutorProfilePage/
│       │   ├── TutorDiscoveryPage/
│       │   ├── TutoringRequestPage/
│       │   ├── MyRequestsPage/
│       │   ├── SecurityPage/
│       │   └── NotFoundPage/
│       ├── services/             # Centralized API and feature service modules
│       ├── context/              # Shared React context, including authentication state
│       ├── hooks/                # Reusable React hooks
│       ├── layouts/              # Public, Student, Tutor and Admin layouts
│       ├── types/                # Shared TypeScript domain types
│       ├── App.tsx
│       └── main.tsx
│
└── README.md
```

### Frontend organization conventions

- Give each major route/page its own directory and page component. Keep page-specific components and styles close to the page when they are not reused elsewhere.
- Put genuinely reusable UI in `components/common/`; keep role- or feature-specific components in their corresponding component directories.
- Keep API communication in `services/`, not directly inside page or presentational components. Use a shared API client for base URL, credentials, and common error handling.
- Use `context/` for shared application state such as the authenticated account, and `hooks/` for reusable behavior such as authentication and permission helpers.
- Keep route/layout concerns separate from page content. Frontend route guards improve navigation and user experience but are not a security boundary; the backend must enforce authorization.
- Keep shared TypeScript interfaces and domain types in `types/`. Avoid duplicating API data shapes across components.

Example page directory:

```text
AdminDashboard/
├── AdminDashboard.tsx
├── AdminOverview.tsx
├── AdminUsers.tsx
├── AdminTutors.tsx
├── AdminRequests.tsx
├── AdminActivity.tsx
└── AdminDashboard.css
```

This is an illustrative decomposition. Components should be split when doing so improves reuse, readability, or testability; avoid creating files solely to satisfy a naming pattern.

### Backend organization conventions

- `routers/` define HTTP endpoints, parse inputs, apply dependencies, call services, and shape HTTP responses. Keep complex business rules out of route handlers.
- `services/` implement application workflows and business rules.
- `repositories/` encapsulate database reads and writes where that separation is useful.
- `models/` define SQLAlchemy persistence models; `schemas/` define Pydantic input/output contracts. Do not treat them as interchangeable.
- `core/` contains shared configuration, security primitives, permission checks, and dependencies.
- `database/` owns database connection/session setup and shared metadata.
- `tests/` should cover routes, services, authorization, ownership, and important security cases.
- Use Alembic migrations for versioned schema changes. Do not rely on ad hoc production startup table changes as the long-term migration strategy.

Target backend request flow:

```text
HTTP request
  -> Router (HTTP concerns and dependencies)
  -> Service (business rules)
  -> Repository (persistence operations)
  -> Database
```

A repository layer should be used consistently where it adds value; simple projects should avoid unnecessary abstraction.

### Authentication and authorization architecture (Beta target)

TutorInn's target role model is `student`, `tutor`, and `admin`. These are distinct roles in one authentication system, not three separate login systems.

- Authenticate credentials on the backend and enforce permissions on every protected API endpoint.
- Issue short-lived signed JWT access tokens. Validate the signature and permitted algorithm, expiry, issuer/audience where configured, and required claims.
- Use cryptographically random refresh tokens in an HttpOnly cookie. Store only a secure hash of each refresh token server-side.
- Rotate refresh tokens on successful refresh. Reject expired, revoked, or previously rotated tokens; detect reuse and revoke the affected token family/session.
- Configure production cookies with Secure, HttpOnly, and an appropriate SameSite policy. Add CSRF protection for cookie-authenticated state-changing requests.
- Resolve current account status and role from trusted server-side data (or a safely invalidated cache). Never authorize based only on editable browser storage, cookie names, frontend state, or an unverified JWT payload.
- A Student or Tutor changing a token role claim to `admin` must not gain privileges. A modified JWT signature must fail verification.
- Return HTTP 401 for missing, invalid, expired, or tampered authentication; return HTTP 403 when a valid authenticated account lacks permission.
- On invalid/revoked authentication, the frontend should clear the invalid session and require login again. Opening Developer Tools by itself is not evidence of an attack and must not trigger logout.
- Keep frontend role-based route guards as a user-experience feature only. Backend authorization is authoritative.

### Session management and security monitoring (Beta target)

- Maintain server-side session/refresh-token records per login or device, including creation and last-used timestamps and available IP/user-agent metadata.
- Let users revoke their current session and other active sessions. Logout revokes the current refresh session.
- Record security events such as failed/successful login, lockout, rejected token, refresh-token reuse, denied privileged access, session revocation, password change, and account suspension/reactivation.
- Never log passwords, raw access tokens, raw refresh tokens, or other secrets.
- Provide an Admin-only security view with searchable/paginated event history and summaries by account and IP, including event counts, attempted account identifiers where supplied, browser/user-agent, and last-seen time where available.
- Treat IP/device signals as investigation context, not proof of a person's identity. Do not automatically ban every account that shares an IP address.
- Rate-limit authentication endpoints and apply configurable temporary lockout/backoff after repeated failed login attempts.

### Admin dashboard and moderation (Beta target)

The planned Admin dashboard is organized around TutorInn's tutoring domain rather than copying task/group-specific features from another project.

| Area | Planned responsibilities |
|---|---|
| Overview | Student, Tutor, tutoring-request, and account-status statistics |
| Students | Search, inspect appropriate profile details, and moderate accounts |
| Tutors | Search, inspect qualifications, and review verification status |
| Tutoring requests | Monitor request lifecycle and status while limiting access to private information |
| Subjects | Manage available subjects if this responsibility is included in the Beta scope |
| Activity | Searchable audit trail of important Student, Tutor, and Admin actions |
| Security | Failed-login monitoring, suspicious activity, token/session events, and security incidents |
| Settings | Authorized platform configuration without exposing secrets |

Planned moderation requirements:

- Tutor verification has distinct `pending`, `approved`, and `rejected` states, with reviewer, timestamp, and optional review note. Verification status does not change the account's role.
- Authorized Admins can suspend/ban and unban Student or Tutor accounts. Every action requires a reason and records the Admin actor, affected account, timestamp, and reason.
- Preserve the complete moderation history; unbanning must not erase the original ban record.
- Enforce suspension server-side on login, refresh, and protected API requests. Revoke active sessions when an account is suspended.
- Link security events to a known account only when attribution is reliable. For unauthenticated attempts, retain attempted identifiers and available technical metadata without claiming the real-world identity is known.

### Database and migration architecture (Beta target)

- Keep SQLAlchemy models separate from Pydantic schemas.
- Define explicit relationships and constraints for accounts, Student/Tutor profiles, tutoring requests, sessions, security events, and moderation history as the final data model requires.
- Use Alembic for reviewed, version-controlled schema migrations.
- Preserve existing MVP records and relationships during refactoring. Do not infer ownership or identity when legacy data does not contain reliable evidence.
- Test migrations against a copy of representative existing data before applying them to a deployed database.
- Keep database credentials and signing secrets in environment variables or deployment secret storage; never commit real secrets.

### API organization and documentation (Beta target)

- Group FastAPI routers by domain, such as authentication, students, tutors, tutoring requests, sessions, Admin, and security.
- Keep the OpenAPI/Swagger documentation available at `/api/docs` when enabled by the deployment configuration.
- Document authentication requirements, role permissions, request/response schemas, status codes, and pagination/filter parameters for each endpoint.
- Preserve existing MVP endpoint behavior where practical. Document and test any necessary breaking changes during the Beta transition.

### Testing and quality (Beta target)

Organize tests around behavior and security boundaries, not only individual files.

- Authentication: registration, login, invalid credentials, expiry, refresh rotation, logout, lockout, and session revocation.
- Authorization: Student, Tutor, and Admin role restrictions on backend endpoints.
- Ownership: one account cannot read or modify another account's private profile, request, or other protected records.
- JWT security: modified signatures, forged Admin role claims, invalid algorithms/claims, and altered browser storage cannot grant privileges.
- Refresh-token security: revoked/expired token rejection and reuse detection.
- Moderation: ban/unban requires a reason, records the acting Admin, revokes sessions, and preserves history.
- Security monitoring: event creation, access restrictions, filtering, and safe handling of sensitive metadata.
- Frontend: production build, route behavior, loading/error states, and service-layer API handling.
- Database: migration upgrade paths and preservation of existing MVP data.

### Development conventions

1. Inspect existing code and tests before moving or replacing modules.
2. Keep each major page in its own directory and reusable components in the appropriate component directory.
3. Put frontend API calls in service modules rather than directly in page components.
4. Keep backend HTTP routing, business logic, and database access responsibilities separated.
5. Keep SQLAlchemy models and Pydantic schemas separate.
6. Enforce authentication, authorization, and record ownership on the backend.
7. Add or update tests when changing behavior, permissions, data models, or API contracts.
8. Prefer small, reviewable refactoring steps that preserve working MVP behavior.
9. Update this README when the actual architecture or supported setup changes; move items out of the target section only after implementation is verified.

### Transition from MVP to Beta

The current MVP is the foundation. The target structure above is not yet a replacement for the current setup instructions. Refactor incrementally:

1. Inspect the current frontend/backend tree and map existing modules to the target responsibilities.
2. Add the target package/module structure without deleting working MVP behavior.
3. Move one feature area at a time, updating imports, routing, tests, and deployment configuration together.
4. Verify existing MVP workflows after each refactoring step.
5. Introduce database migrations and authentication changes with explicit compatibility and data-preservation checks.
6. Update the run commands and API documentation in this README only when the actual entry points and configuration have changed.

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
