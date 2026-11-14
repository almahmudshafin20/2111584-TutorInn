# TutorInn

TutorInn is a tutoring platform built with **React + TypeScript**, **FastAPI**, and **SQLAlchemy**. It retains the original demo-profile MVP workflows and adds Beta account authentication, private Student/Tutor profiles, and role-specific dashboards.

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
- Shared Student/Tutor/Admin account authentication using Argon2 password hashes, short-lived signed JWT access tokens, opaque rotating refresh sessions, CSRF checks, and server-side role enforcement.
- Private account profile editing, password changes, device-session listing/revocation, and security-event recording.
- Student and Tutor dashboards, tutor discovery filters, Student tutoring-request CRUD, and Tutor responses.
- FastAPI Swagger UI at `/api/docs`.

> **Legacy demo workflow:** The selected profile ID/type remains a demo-only identity mechanism and is not proof of identity. It is disabled by default on Vercel/production (unless explicitly overridden, which is not recommended). Beta account endpoints use signed access tokens and server-side account/profile ownership. The legacy Admin API-key review screen is not the authenticated Admin dashboard; it is disabled with demo mode in production.

## Project architecture and code organization

> **Architecture status:** The **Implemented structure** section describes the existing MVP plus the Beta authentication/dashboard modules now implemented on this branch. The **Target Beta repository structure** and later roadmap sections still describe future work beyond Beta Parts 1–3.

### Implemented structure on this refactor branch

The following organization is implemented in this refactor branch while retaining the existing MVP routes and demo-profile workflow. It is separate from the larger Beta target shown below.

```text
backend/
├── main.py                    # FastAPI app setup and router registration
├── database.py                # SQLAlchemy engine, session dependency and MVP schema initialization
├── dependencies.py            # Legacy demo-profile and Admin API-key dependencies
├── auth.py                    # JWT, Argon2, current-account and role dependencies
├── models.py                  # SQLAlchemy database models and subject helpers
├── schemas.py                 # Pydantic request/response validation
├── crud.py                    # MVP business rules and database operations
├── routers/
│   ├── auth.py                # Registration, login, refresh, sessions and Admin bootstrap
│   ├── account.py             # Authenticated profile and password workflows
│   ├── beta_requests.py       # Authenticated dashboards and tutoring requests
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
│   ├── AuthContext.tsx         # Restored authenticated account and access-token state
│   └── ThemeContext.tsx
├── hooks/
│   └── useSelectedProfile.ts
├── layouts/
│   └── AppLayout.tsx
├── pages/                      # Includes Login, Register, Dashboard and My Profile pages
├── services/
│   ├── auth.ts                 # Login, registration, refresh and session APIs
│   ├── dashboard.ts            # Dashboard, tutor discovery and tutoring-request APIs
│   ├── api.ts                  # Shared HTTP client and Admin header helper
│   ├── admin.ts                # Admin review queue and decisions
│   ├── posts.ts                # Post CRUD, responses and pagination helpers
│   ├── profiles.ts             # Student/Tutor profile and approved-match requests
│   ├── subjects.ts             # Subject catalogue requests
│   └── session.ts              # Demo-profile browser storage
├── types/
│   ├── domain.ts               # Authoritative Student, Tutor, Post and Response contracts
│   ├── forms.ts                # Form field metadata based on domain types
│   └── index.ts                # Backward-compatible type re-exports
├── shared.tsx                  # Backward-compatible exports; new code should import focused modules
├── App.tsx                     # Route/page selection
├── main.tsx
└── index.css
```

#### Frontend request and component flow

- `App.tsx` selects the page for the current URL and uses the dedicated `layouts/AppLayout.tsx` for the not-found screen.
- A page composes focused UI components and the shared `AppLayout`.
- Pages and reusable components call focused feature functions from `services/profiles.ts`, `services/posts.ts`, `services/subjects.ts`, and `services/admin.ts`; they do not issue HTTP requests directly.
- Each feature service delegates transport to the shared `services/api.ts` HTTP client.
- `api.ts` adds the selected demo-profile headers only for legacy demo routes, attaches the in-memory bearer token for authenticated routes, sends requests with same-origin credentials, parses API errors, and returns typed response data.
- `main.tsx` mounts `AuthProvider` around the application. The provider restores sessions through a CSRF-protected refresh call and exposes the current account to the header and protected pages. Refresh restoration is single-flight so React Strict Mode's development effect replay cannot rotate the same refresh token twice.
- Login, registration, profile and session pages call the focused functions in `services/auth.ts`; Student/Tutor dashboard pages use `services/dashboard.ts` for dashboard data, tutor discovery, request CRUD and responses. Both services delegate HTTP transport to `services/api.ts`.
- `session.ts` reads/writes the selected demo profile in browser local storage. This is a demo identity mechanism, not secure authentication.
- Shared TypeScript domain contracts live in `types/domain.ts`, the single source of truth. `types/index.ts` only re-exports those contracts for compatibility; form metadata imports the canonical `Field` type. Backend validation remains authoritative.

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
| Authentication | Student/Tutor registration, shared login, refresh, logout, session listing/revocation, Admin bootstrap |
| Account | Authenticated own-profile read/update and password change |
| Beta Requests | Role-specific dashboards, Student request CRUD, Tutor responses and response privacy |
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

#### MVP behavior preserved alongside Beta additions

- Existing Student and Tutor CRUD and public profile response shapes.
- Existing tutoring-post creation, listing, editing, deletion and pagination.
- Existing selected-profile demo workflow and browser storage keys.
- Existing independent Interested/Not Interested responses and Admin review process.
- Existing API paths, HTTP methods, status codes, request/response schemas and `/api/docs`.
- Existing MVP records and legacy fields are retained. PR #43 adds `user_accounts`, `refresh_sessions`, and `security_events`, adds nullable `account_id` links to Student/Tutor profiles, and creates unique indexes for linked profile ownership. Legacy profiles are not automatically linked to accounts because their identity cannot be safely inferred.

> **Beta status after PR #43:** Shared Student/Tutor/Admin credentials, Argon2 password hashing, JWT access-token validation, rotating hashed refresh sessions, CSRF checks, server-side role enforcement, self-owned Student/Tutor profiles, password/session controls, security-event recording, Student/Tutor dashboards, tutor discovery, and authenticated Student request workflows are implemented. Still planned for later milestones: the authenticated Admin dashboard, account suspension/ban and unban workflows, tutor verification, searchable Admin security-event views, general API rate limiting, and versioned Alembic migrations. The selected-profile headers and legacy Admin API key remain demo-only and are not equivalent to account authentication.

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

### Implemented authentication and authorization architecture (Parts 1–3)

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

### Implemented session controls and security-event recording (Parts 1–3)

- Maintain server-side refresh-session records with creation, last-used and expiry timestamps plus available IP/user-agent metadata. Raw refresh tokens are stored only as SHA-256 hashes.
- Users can list and revoke their own sessions; logout revokes the current refresh session, and password changes revoke all active sessions.
- Current security-event recording covers successful/failed login, temporary login lockout, expired/reused refresh tokens, inactive-account access, denied role access, logout, session revocation, password changes, and Admin bootstrap attempts.
- Never log passwords, raw access tokens, raw refresh tokens, or other secrets.
- **Remaining work:** an Admin-only searchable/paginated security-event view, audit events for future suspension/ban and verification workflows, and general API rate limiting. Login currently has configurable temporary lockout after repeated failed attempts.
- Treat IP/device signals as investigation context, not proof of a person's identity. Do not automatically ban every account that shares an IP address.

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


## Beta account setup (Parts 1–3)

The account system is separate from the legacy demo-profile workflow. Configure the following backend environment variables before enabling registration/login:

| Variable | Required | Default / guidance |
|---|---:|---|
| `JWT_SECRET` | Yes | Random secret of at least 32 characters; keep private |
| `ADMIN_BOOTSTRAP_TOKEN` | For first Admin | Random secret of at least 32 characters; use once to create the first Admin |
| `DATABASE_URL` | Deployment | Persistent PostgreSQL URL; local development defaults to SQLite |
| `JWT_ISSUER` | No | `tutorinn` |
| `JWT_AUDIENCE` | No | `tutorinn-web` |
| `ACCESS_TOKEN_MINUTES` | No | `15` (allowed 1–60) |
| `REFRESH_TOKEN_DAYS` | No | `7` (allowed 1–30) |
| `COOKIE_SECURE` | Production | Must remain enabled for production/Vercel |
| `COOKIE_SAMESITE` | No | `lax` |
| `LOGIN_MAX_ATTEMPTS` | No | `5` failed attempts |
| `LOGIN_LOCKOUT_MINUTES` | No | `15` |
| `ENABLE_DEMO_MODE` | No | Defaults off on Vercel/production and on for local MVP compatibility |

Copy `backend/.env.example` to `backend/.env` for local development and replace every placeholder. The example's `COOKIE_SECURE=false` is for local HTTP development only; never copy that value into Vercel/production. Do not commit `.env`, real secrets, or production credentials. On Vercel, add `JWT_SECRET`, `ADMIN_BOOTSTRAP_TOKEN`, and `DATABASE_URL` to the backend project's environment settings, and set `COOKIE_SECURE=true` (or leave it unset so the Vercel production default enables Secure). Vercel automatically sets `VERCEL=1`; the backend rejects attempts to disable Secure cookies in production. A persistent database is required because serverless local SQLite is not durable.

The first Admin is created through `POST /api/auth/admin/bootstrap` with the `X-Admin-Bootstrap-Token` header. This endpoint permits only the first Admin and requires the bootstrap secret. Admins then use the shared `POST /api/auth/login` endpoint. Never expose the bootstrap token to the frontend.

### Beta API routes

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register/student` | Register Student and create linked profile |
| POST | `/api/auth/register/tutor` | Register Tutor and create linked profile |
| POST | `/api/auth/login` | Shared role-aware login |
| POST | `/api/auth/refresh` | CSRF-protected refresh rotation |
| POST | `/api/auth/logout` | Revoke current refresh session |
| GET | `/api/auth/me` | Read authenticated account |
| GET / DELETE | `/api/auth/sessions`, `/api/auth/sessions/{id}` | List/revoke own sessions |
| DELETE | `/api/auth/admin/sessions/{id}` | Admin revokes a user's session |
| POST | `/api/auth/admin/bootstrap` | Bootstrap the first Admin |
| GET / PUT | `/api/me/profile`, `/api/me/profile/{student or tutor}` | Read/update own profile |
| POST | `/api/me/password` | Verify current password, update hash and revoke sessions |
| GET | `/api/dashboard` | Role-specific Student/Tutor dashboard data |
| GET / POST | `/api/requests` | List own requests or open tutor requests; create Student request |
| GET / PUT / DELETE | `/api/requests/{id}` | Read/update/delete owned Student request |
| POST | `/api/requests/{id}/responses` | Tutor responds to an open Student request |
| GET | `/api/requests/{id}/responses` | Student reads responses to own request |

The authenticated profile endpoints never accept a profile ID from the client to decide ownership. They resolve the Student/Tutor profile through the signed-in account. A valid authenticated account with the wrong role receives 403; missing/invalid authentication receives 401.

### Beta frontend routes

- `/login` — shared Student/Tutor/Admin sign-in
- `/register` — Student or Tutor registration
- `/dashboard` — role-specific Student or Tutor workspace; Admin sees an Admin placeholder until Part 6
- `/profile` — own profile, password and active sessions

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

The backend normalizes PostgreSQL URLs for Psycopg. SQLAlchemy creates new tables at startup, including account, refresh-session, and security-event tables. Additive startup migrations add missing subject, post-owner, phone, availability, and nullable account-link columns to existing databases, then add unique indexes for non-null Student/Tutor account links. These compatibility migrations are currently startup-driven; versioned Alembic migrations remain a later improvement.

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

GitHub Actions builds the TypeScript frontend and runs the backend test suite. Current Beta tests cover Student/Tutor registration, Argon2 password hashing, login, JWT tampering/expiry, Admin bootstrap and role checks, refresh rotation/reuse/expiry, CSRF rejection, logout, session revocation, suspended-account rejection, password changes, profile ownership, Student request CRUD, multi-tutor response privacy, tutor discovery filters, login lockout, production cookie flags, and legacy demo-mode restrictions. A passing build does not replace browser-based manual testing of sign-in, registration, session restoration, profile editing, and both dashboards.

## Vercel

The existing `vercel.json` routes `/api/*` to the FastAPI backend and other paths to the Vite frontend. Add `DATABASE_URL`, `JWT_SECRET`, and `ADMIN_BOOTSTRAP_TOKEN` to backend environment variables before deploying. Add `ADMIN_API_KEY` only if the legacy demo Admin review workflow is intentionally enabled outside production. Verify actual deployment status and logs in Vercel; repository configuration alone does not prove a deployment is working.
