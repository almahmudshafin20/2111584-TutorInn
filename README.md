# TutorInn

TutorInn is a tutoring platform built with **React + TypeScript**, **FastAPI**, and **SQLAlchemy**. It retains the original demo-profile MVP workflows and adds Beta account authentication, private Student/Tutor profiles, and role-specific dashboards.

## Core features

- Student and Tutor profile CRUD directly from their respective directories.
- Legacy selected demo profile remains stored in browser local storage as `tutorinn-profile-id` and `tutorinn-profile-type` for the original MVP workflows; it is no longer exposed in the normal public/Beta navigation.
- Multiple subjects on Student profiles, Tutor profiles, and tutoring posts. Subjects are stored as structured lists and rendered separately.
- Tutoring posts are associated with the specific selected author profile.
- Interested and Not Interested responses are stored separately for every post/profile pair.
- Interested responses enter an individual Admin review queue; Not Interested responses do not require approval and hide the post only from that profile's active feed.
- Profile response history, including the ability to change a response.
- Admin review endpoints protected by a backend `ADMIN_API_KEY`.
- Separate Home, About, Tutoring Hub, My Responses, Admin Review, Student Profiles, and Tutor Profiles pages.
- Shared Student/Tutor/Admin account authentication using Argon2id password hashes with a server-side HMAC-SHA256 pepper, short-lived signed JWT access tokens, opaque rotating refresh sessions, CSRF checks, and server-side role enforcement.
- Private account profile editing, password changes, device-session listing/revocation, and security-event recording.
- Student and Tutor dashboards, tutor discovery filters, Student tutoring-request CRUD, and Tutor responses.
- FastAPI Swagger UI at `/api/docs`.

> **Legacy demo workflow:** The selected profile ID/type remains a demo-only identity mechanism and is not proof of identity. It is disabled by default on Vercel/production (unless explicitly overridden, which is not recommended). Beta account endpoints use signed access tokens and server-side account/profile ownership. The legacy Admin API-key review screen is not the authenticated Admin dashboard; it is disabled with demo mode in production.

## Project architecture and code organization

> **Architecture status:** The **Implemented structure** section describes the existing MVP plus the Beta authentication/dashboard modules now implemented on this branch. The **Target Beta repository structure** and later roadmap sections still describe future work beyond Beta Parts 1–3.

### Milestone 0 architectural foundation

Milestone 0 defines the architectural boundaries that all later MVP and Beta work must follow. This section documents the shared foundation for contributors; it complements the agent-specific workflow in `AGENTS.md` without replacing the setup, configuration, API, or deployment guidance elsewhere in this README.

#### Architecture principles

TutorInn follows a layered frontend-to-backend architecture:

```text
Frontend page and components
  -> feature-oriented frontend API module
  -> shared frontend HTTP client (api/api.ts)
  -> FastAPI domain router
  -> request dependencies and server-side authorization
  -> Pydantic request validation
  -> CRUD/business workflow (or a justified domain service)
  -> SQLAlchemy model and database session
  -> PostgreSQL / SQLite
  -> Pydantic response schema
  -> frontend service and UI state
```

Each layer has a distinct responsibility. Pages and components present information; frontend services coordinate feature API calls; the shared API client owns HTTP transport; routers own HTTP concerns; dependencies resolve trusted request context and permissions; schemas validate external data; business workflows enforce domain rules; models and database constraints protect persisted data.

#### Frontend responsibilities

The implemented frontend organization under `frontend/src/` is:

| Area | Responsibility |
|---|---|
| `pages/` | Route-level screens and page composition. Keep Home, About, Task Details, and other distinct pages separate. |
| `components/` | Reusable UI, shared or feature-specific as appropriate. |
| `layouts/` | Shared page shells and layout composition. |
| `api/` | Feature API functions and browser/session helpers. |
| `api/api.ts` | Shared HTTP transport, credentials, bearer-token handling, and common API error handling. |
| `context/` | Cross-application state such as authenticated account and theme. |
| `hooks/` | Reusable React behavior. |
| `types/` | Canonical TypeScript domain contracts and form types. |
| `App.tsx` / `main.tsx` | Application composition/routing and bootstrap/provider mounting. |

Pages and UI components must not duplicate HTTP transport or contain database/business rules. Feature services should use the shared API client. Keep shared data contracts in `types/`; do not scatter duplicate interfaces across components. The existing compatibility modules may remain while imports are migrated, but new code should use the focused module that owns the behavior.

#### Backend responsibilities

The implemented backend organization under `backend/` is:

| Area | Responsibility |
|---|---|
| `main.py` | FastAPI application setup and router registration. |
| `routers/` | Domain endpoint paths, methods, dependencies, status codes, and response models. |
| `dependencies.py` / `auth.py` | Request context, authentication, and reusable authorization dependencies/helpers. |
| `schemas.py` | Pydantic input validation, normalization, and public response contracts. |
| `models.py` | SQLAlchemy persistence models and model-level helpers. |
| `crud.py` | Existing MVP business workflows and database reads/writes; extract focused api/repositories when a real feature justifies the boundary. |
| `database.py` | Database engine/session configuration and current initialization/compatibility behavior. |
| `tests/` | API, business-rule, ownership, security, and regression tests. |

Keep route handlers focused on HTTP concerns and delegate business/data work. Do not create empty service or repository layers solely to match a target folder tree. The larger target Beta structure documented below is an intended direction, not a claim that every target module already exists.

#### Validation, authorization, and trust boundaries

- Frontend validation and TypeScript types improve usability and describe expected shapes; they are not security controls.
- FastAPI dependencies and backend authorization enforce authentication, role permissions, account status, and record ownership for every protected operation.
- Pydantic schemas validate and normalize incoming request data and define safe response shapes.
- CRUD/domain workflows enforce business rules, cross-field constraints, ownership, and permitted state transitions.
- SQLAlchemy models and database constraints protect persisted relationships, uniqueness, and integrity.
- Public Student/Tutor responses must not expose private contact details, credentials, refresh tokens, or security-only data.
- Never trust a role, account ID, profile ID, ownership claim, or account status supplied by browser storage or editable client state.

#### Database, identity, and data integrity

- The browser communicates with FastAPI; it does not connect directly to Supabase.
- FastAPI uses SQLAlchemy and the configured server-side PostgreSQL connection. TutorInn's own JWT/account identity model is authoritative; Supabase Auth and `auth.uid()` are not the current application identity source.
- The existing Supabase PostgreSQL project and existing data are retained. The current public tables have RLS enabled and direct Data API table/schema/sequence privileges revoked for `anon` and `authenticated`. The absence of browser-facing RLS policies is intentional deny-by-default protection, not a missing configuration.
- RLS and database grants complement, but do not replace, FastAPI authentication, authorization, and ownership checks. Do not add permissive policies or browser grants to bypass an API issue.
- Preserve existing MVP profile/post CRUD, response workflows, API contracts, records, IDs, and relationships unless an explicitly approved requirement changes them. Existing legacy profiles are not automatically linked to new accounts; registration creates a new profile, and existing records remain untouched.
- Review schema changes for constraints, indexes, relationships, RLS, and grants. Keep migrations version-controlled, test upgrade paths against representative existing data, and never destructively reset shared/deployed data.

The current implementation details and applied Supabase migration are documented in the sections below. The intended longer-term service/repository/Alembic structure remains a target until implemented and verified.

#### Six architectural recommendations

These six recommendations summarize the foundation and apply to new features and refactors:

1. **Dedicated frontend pages and components:** organize page-level screens under `frontend/src/pages/` and reusable UI under `frontend/src/components/`.
2. **Centralized API communication:** use focused frontend feature API modules backed by `frontend/src/api/api.ts`; do not put direct HTTP transport in UI components.
3. **Shared TypeScript contracts:** keep canonical shared types under `frontend/src/types/`.
4. **Domain-focused backend routers:** organize FastAPI endpoints under `backend/app/routers/`, not as a collection of handlers in `main.py`.
5. **Separate persistence models and API schemas:** keep SQLAlchemy models, Pydantic schemas, and router definitions as distinct responsibilities.
6. **Separated business and data operations:** keep business rules and database operations out of route handlers, using the existing CRUD boundary and introducing service/repository modules when justified.

For frontend work, the three highest-priority checks are: put pages/components in their designated folders, route all API communication through the shared service layer, and keep shared TypeScript types in `types/`.

#### Keeping architecture documentation aligned

When the implemented architecture changes, update **both `README.md` and `AGENTS.md` in the same approved change whenever practical**. They have complementary responsibilities:

- **This README explains what the architecture is**: the verified folder structure, layer responsibilities, request/data flow, security boundaries, and which parts are implemented versus planned.
- **AGENTS.md explains how AI coding agents must work within it**: where new code belongs, which existing services and patterns to reuse, which boundaries must not be bypassed, and what tests/checks are required.

Keep the documents aligned in meaning, not copied word for word. Update README with the architectural explanation and AGENTS with actionable implementation rules. If a design is only proposed or partially implemented, label it as a target rather than presenting it as current behavior. Architecture changes are not fully documented until both files accurately describe their respective sides.

### Implemented structure on this refactor branch

The following organization is implemented in this branch while retaining the existing MVP routes and demo-profile workflow. The later sections describe the current Beta capabilities, security boundaries, migration workflow and remaining verification gaps.

```text
backend/
├── app/                     # FastAPI application package
│   ├── routers/             # Domain-specific HTTP endpoints
│   ├── main.py              # FastAPI app setup and router registration
│   ├── auth.py              # JWT, password and session helpers
│   ├── dependencies.py      # Request dependencies and demo guards
│   ├── database.py          # SQLAlchemy engine, Base and session dependency
│   ├── models.py            # SQLAlchemy persistence models
│   ├── schemas.py           # Pydantic request/response contracts
│   └── crud.py              # Existing business and database workflows
├── alembic/
│   ├── env.py               # Alembic metadata and DB connection setup
│   └── versions/            # Ordered, versioned schema revisions
├── tests/                   # Backend automated tests
├── alembic.ini
└── requirements*.txt

frontend/src/
├── api/                     # Shared HTTP client and feature API modules
├── components/              # Reusable UI components
├── pages/                   # Route-level pages
├── layouts/                 # Shared page layouts
├── context/                 # Authentication and theme state
├── hooks/                   # Reusable React hooks
├── types/                   # Shared TypeScript contracts
├── App.tsx
└── main.tsx

supabase/migrations/          # Existing Supabase SQL migration history
```

#### Frontend request and component flow

- `App.tsx` selects the page for the current URL and uses the dedicated `layouts/AppLayout.tsx` for the not-found screen.
- A page composes focused UI components and the shared `AppLayout`.
- Pages and reusable components call focused feature functions from `api/profiles.ts`, `api/posts.ts`, `api/subjects.ts`, and `api/admin.ts`; they do not issue HTTP requests directly.
- Each feature API module delegates transport to the shared `api/api.ts` HTTP client.
- `api.ts` adds the selected demo-profile headers only for legacy demo routes, attaches the in-memory bearer token for authenticated routes, sends requests with same-origin credentials, parses API errors, and returns typed response data.
- `main.tsx` mounts `AuthProvider` around the application. The provider restores sessions through a CSRF-protected refresh call and exposes the current account to the header and protected pages. Refresh restoration is single-flight so React Strict Mode's development effect replay cannot rotate the same refresh token twice.
- Login, registration, profile and session pages call the focused functions in `api/auth.ts`; Student/Tutor dashboard pages use `api/dashboard.ts` for dashboard data, tutor discovery, request CRUD and responses. Both services delegate HTTP transport to `api/api.ts`.
- `session.ts` reads/writes the selected demo profile in browser local storage. This is a demo identity mechanism, not secure authentication.
- Shared TypeScript domain contracts live in `types/domain.ts`, the single source of truth. `types/index.ts` only re-exports those contracts for compatibility; form metadata imports the canonical `Field` type. Backend validation remains authoritative.

#### Beta UI architecture and responsive experience

The Part 3 interface foundation is implemented through the existing page/layout/component boundaries:

- `components/SiteHeader.tsx` renders a minimal public header and role-aware desktop navigation for authenticated accounts. The legacy demo-profile selector and theme switch are not part of the normal public navigation.
- `layouts/AppLayout.tsx` owns the shared page shell and renders role-specific fixed bottom navigation on mobile for Student, Tutor, and Admin accounts. Navigation links target existing routes and relevant dashboard sections.
- `pages/LoginPage.tsx` and `pages/RegisterPage.tsx` remain separate pages and use a shared split-screen visual pattern: an informational panel and a focused form on larger screens, with a compact information panel and form-first layout on smaller screens.
- `pages/HomePage.tsx` and `pages/AboutPage.tsx` remain distinct public pages. The public navigation is intentionally limited to the brand, About, Log in, and Create account; legacy MVP directories and tools remain available through their existing routes rather than crowding the public header.
- `index.css` owns the shared light-theme design tokens, typography stack, component surfaces, form-control treatment, responsive breakpoints, and reduced-motion preferences. Inter is the preferred first font in the system sans-serif stack; no externally hosted font is required for the app to render.
- Form controls use consistent custom CSS treatment for inputs, selects, textareas, focus states, validation states, and disabled states. Native select behavior is retained for keyboard and assistive-technology compatibility while the visual control is styled consistently.
- Student/Tutor dashboard content and existing API/service behavior remain in their dedicated pages and service modules. The layout/navigation changes do not change account authorization or data ownership.

TutorInn supports user-selectable light and dark themes. The selected preference is persisted locally through `ThemeContext`; both themes must preserve accessible contrast, visible focus, responsive layouts, and reduced-motion support. Do not hardcode a color palette or decorative style into architectural rules. Preserve semantic HTML, keyboard operation, visible focus, responsive layouts, and reduced-motion support when extending the UI.

The old `shared.tsx` module is retained as a compatibility barrel so existing imports can continue working during incremental migration. New page/component code should import from the focused module that owns the behavior.

#### Backend request, validation and data flow

```text
HTTP request
  -> FastAPI router (backend/app/routers/)
  -> FastAPI dependencies (backend/app/dependencies.py)
  -> Pydantic input validation (backend/app/schemas.py)
  -> CRUD/business workflow (backend/app/crud.py)
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
- FastAPI/Pydantic schemas in `backend/app/schemas.py` enforce server-side field constraints, normalize email/subject values, and validate request payloads.
- CRUD workflows in `backend/app/crud.py` enforce cross-field and business rules such as duplicate profile emails, required tutor/listing subjects, post ownership, valid response direction, and review-state transitions.
- SQLAlchemy models in `backend/app/models.py` define database columns, uniqueness constraints and persisted relationships/identity fields.
- Database constraints remain the final persistence-level protection for uniqueness and integrity.

#### MVP behavior preserved alongside Beta additions

- Existing Student and Tutor CRUD and public profile response shapes.
- Existing tutoring-post creation, listing, editing, deletion and pagination.
- Existing selected-profile demo workflow and browser storage keys.
- Existing independent Interested/Not Interested responses and Admin review process.
- Existing API paths, HTTP methods, status codes, request/response schemas and `/api/docs`.
- Existing MVP records and legacy fields are retained. PR #43 adds `user_accounts`, `refresh_sessions`, and `security_events`, nullable `account_id` links to Student/Tutor profiles, and unique indexes for linked profile ownership. New Student/Tutor registrations create new profile records. Existing legacy profiles are not automatically linked to new accounts, and their original records remain preserved.

> **Beta status on this branch (17 Nov 2026):** The repository now includes authenticated Student/Tutor/Admin accounts, profile ownership and session controls, Student/Tutor dashboards and request workflows, personal learning tasks, group learning and assignments, the Admin management workspace, tutor verification, moderation/reporting, subject catalogue management, activity/security investigation, additional security hardening, and environment/migration compatibility work. Milestones 0–6 are implemented on the stacked PR branches; Milestone 7 code and CI requirements are implemented, but deployed Beta workflow verification remains open; Milestone 8 is partially verified, with local secret setup recorded and migration/runtime-role plus production-startup verification still outstanding. See Issue #41 and the PR descriptions for exact acceptance and verification state. The selected-profile headers and legacy Admin API key remain demo-only and are not equivalent to account authentication.

### Earlier target Beta repository structure (roadmap reference)

The following is a historical architectural proposal, not the current folder tree. The verified implementation is documented in **Implemented structure on this refactor branch** and **Current refactor status and contributor quick reference** below. Do not create these proposed nested `core/`, `database/`, `models/`, `schemas/`, `api/`, or `repositories/` packages unless a separately approved refactor establishes that need.

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
│   │   ├── api/             # Business rules and use cases
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
│       ├── api/             # Centralized API and feature service modules
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
- Keep API communication in `api/`, not directly inside page or presentational components. Use a shared API client for base URL, credentials, and common error handling.
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

### Backend organization conventions (current implementation)

- `backend/app/routers/` contains domain-specific FastAPI routers.
- `backend/app/main.py` creates the FastAPI application, registers routers, and configures lifespan startup; it is not a place for endpoint or business logic.
- `backend/app/models.py` contains SQLAlchemy models; `backend/app/schemas.py` contains Pydantic API contracts.
- `backend/app/database.py` owns SQLAlchemy engine/session/Base setup and the current MVP compatibility initializer.
- `backend/app/auth.py` and `backend/app/dependencies.py` contain authentication helpers and request dependencies; `backend/app/crud.py` retains existing business/data workflows.
- `backend/tests/` covers routes, business rules, authorization, ownership, startup behavior, and Alembic configuration.
- Alembic files are kept separately in `backend/alembic/`; they are not application modules. See `backend/alembic/README.md` for safe migration procedures.

Target backend request flow:

```text
HTTP request
  -> Router (HTTP concerns and dependencies)
  -> Service (business rules)
  -> Repository (persistence operations)
  -> Database
```

A repository layer should be used consistently where it adds value; simple projects should avoid unnecessary abstraction.

### Supabase database access and Row Level Security

- The frontend communicates with the backend through the centralized FastAPI HTTP client; it does not connect directly to Supabase.
- FastAPI uses SQLAlchemy with the server-side PostgreSQL connection (`DATABASE_URL`, falling back to `POSTGRES_URL`) and enforces TutorInn's own JWT, role, account-status, and ownership checks. Supabase Auth user IDs are not used as TutorInn identities, so policies based on `auth.uid()` would not enforce the application's actual ownership model.
- As verified against the live Supabase project on 17 Nov 2026, all 15 public tables (`content_reports`, `group_learning_tasks`, `group_task_assignments`, `interest_responses`, `learning_group_members`, `learning_groups`, `learning_posts`, `managed_subjects`, `personal_learning_tasks`, `refresh_sessions`, `security_events`, `students`, `tutor_verifications`, `tutors`, and `user_accounts`) have RLS enabled. Direct table, sequence, and schema privileges are revoked from the Supabase `anon` and `authenticated` roles (and PostgreSQL `PUBLIC`); server-side privileged database access is retained.
- These tables intentionally have no browser-facing RLS policies. This is a deny-by-default boundary for Supabase Data API roles, not a replacement for FastAPI authorization. Do not grant browser roles access or add broad `USING (true)` policies.
- The deny-by-default access migration is `supabase/migrations/20261114133407_secure_public_schema_rls_and_api_privileges.sql`; later migrations add RLS to tutor verification, reports/managed subjects, and private learning tables. Applied migration history is retained in the existing `2111584-TutorInn` Supabase project. Direct SELECT grants are absent for `anon` and `authenticated`; do not infer the FastAPI runtime role solely from the `service_role` grant.
- The historical `20261114134652_legacy_profile_claim_tokens.sql` migration is retained to preserve migration history. The follow-up `20261115130000_remove_legacy_profile_claim_tokens.sql` migration drops its unused Student/Tutor claim columns without deleting or rewriting profile records.
- Any future public table must explicitly enable RLS and be reviewed for grants before deployment. If direct Supabase client access is introduced later, design and test narrow policies against a trusted identity mapping first; do not assume TutorInn JWTs are Supabase Auth JWTs.
- Runtime verification after applying the migration confirmed the FastAPI health, subjects, tutor-listing, and learning-post endpoints remained available. These 15 RLS-protected tables intentionally have no browser-facing Data API policies under the current deny-by-default model.

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
- **Current scope note:** Admin-only Activity/Security investigation views, account moderation, tutor verification, role controls, pagination, and configured authentication rate limits are implemented. Further production/live workflow verification is tracked separately in Issue #41.
- Treat IP/device signals as investigation context, not proof of a person's identity. Do not automatically ban every account that shares an IP address.

### Implemented Admin dashboard and moderation (Milestone 6)

The implemented Admin workspace is organized around TutorInn's tutoring domain rather than copying task/group-specific features from another project.

| Area | Implemented responsibilities |
|---|---|
| Overview | Student, Tutor, tutoring-request, and account-status statistics |
| Students | Search, inspect appropriate profile details, and moderate accounts |
| Tutors | Search, inspect qualifications, and review verification status |
| Tutoring requests | Monitor request lifecycle and status while limiting access to private information |
| Subjects | Manage available subjects if this responsibility is included in the Beta scope |
| Activity | Searchable audit trail of important Student, Tutor, and Admin actions |
| Security | Failed-login monitoring, suspicious activity, token/session events, and security incidents |
| Settings | Authorized platform configuration without exposing secrets |

Implemented moderation capabilities:

- Tutor verification has distinct `pending`, `approved`, and `rejected` states, with reviewer, timestamp, and optional review note. Verification status does not change the account's role.
- Authorized Admins can suspend/ban and unban Student or Tutor accounts. Every action requires a reason and records the Admin actor, affected account, timestamp, and reason.
- Preserve the complete moderation history; unbanning must not erase the original ban record.
- Enforce suspension server-side on login, refresh, and protected API requests. Revoke active sessions when an account is suspended.
- Link security events to a known account only when attribution is reliable. For unauthenticated attempts, retain attempted identifiers and available technical metadata without claiming the real-world identity is known.

### Database and migration architecture (current workflow)

- Keep SQLAlchemy models separate from Pydantic schemas.
- Define explicit relationships and constraints for accounts, Student/Tutor profiles, tutoring requests, sessions, security events, and moderation history as the final data model requires.
- Use Alembic for reviewed, version-controlled schema migrations.
- Preserve existing MVP records and relationships during refactoring. Do not infer ownership or identity when legacy data does not contain reliable evidence.
- Test migrations against a copy of representative existing data before applying them to a deployed database.
- Keep database credentials and signing secrets in environment variables or deployment secret storage; never commit real secrets.

### API organization and documentation (current guidance)

- Group FastAPI routers by domain, such as authentication, students, tutors, tutoring requests, sessions, Admin, and security.
- Keep the OpenAPI/Swagger documentation available at `/api/docs` when enabled by the deployment configuration.
- Document authentication requirements, role permissions, request/response schemas, status codes, and pagination/filter parameters for each endpoint.
- Preserve existing MVP endpoint behavior where practical. Document and test any necessary breaking changes during the Beta transition.

### Testing and quality expectations

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
3. Put frontend API calls in feature modules under `frontend/src/api/`; pages and components must not issue HTTP requests directly.
4. Keep backend routers, business/data workflows, and persistence setup in their documented `backend/app/` modules.
5. Keep SQLAlchemy models and Pydantic schemas separate.
6. Enforce authentication, authorization, and record ownership on the backend.
7. Add or update tests when changing behavior, permissions, data models, imports, startup, or API contracts.
8. Prefer small, reviewable refactoring steps that preserve working MVP behavior.
9. When implemented architecture changes, update both `README.md` (explain the verified design) and `AGENTS.md` (give AI agents actionable rules) in the same approved change where practical. Keep planned work labeled as target until verified; update setup/API/deployment sections when those contracts change.

### Transition from MVP to Beta

The repository has since implemented the package boundaries described in the current-structure section. Treat this earlier transition plan as historical context; do not use it to recreate the superseded target tree. For further architecture work:

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
| `PASSWORD_PEPPER` | Yes | Separate random secret of at least 32 characters; used with HMAC-SHA256 before Argon2id; keep private and stable |
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

Copy `backend/.env.example` to `backend/.env` for local development and replace every placeholder. The example's `COOKIE_SECURE=false` is for local HTTP development only; never copy that value into Vercel/production. Do not commit `.env`, real secrets, or production credentials. On Vercel, add `JWT_SECRET`, `PASSWORD_PEPPER`, `ADMIN_BOOTSTRAP_TOKEN`, and `DATABASE_URL` to the backend project's environment settings, and set `COOKIE_SECURE=true` (or leave it unset so the Vercel production default enables Secure). Vercel automatically sets `VERCEL=1`; the backend rejects attempts to disable Secure cookies in production. A persistent database is required because serverless local SQLite is not durable.

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
| POST | `/api/requests/{id}/responses/{response_id}/accept` | Owning Student accepts one Interested Tutor; other pending Interested responses are declined |

The authenticated profile endpoints never accept a profile ID from the client to decide ownership. They resolve the Student/Tutor profile through the signed-in account. A valid authenticated account with the wrong role receives 403; missing/invalid authentication receives 401.

### Beta frontend routes

- `/login` — shared Student/Tutor/Admin sign-in
- `/register` — Student or Tutor registration
- `/dashboard` — role-specific Student or Tutor workspace; the authenticated Admin workspace is available to Admin accounts.
- `/profile` — own profile, password and active sessions
- `/tutors` — read-only public Tutor directory
- `/tutors/{id}` — public Tutor details
- Legacy `/posts` redirects to `/dashboard`; legacy `/students` routes redirect to Student registration.

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
# Copy the placeholders, then replace CHANGE_ME values before using account authentication.
cp .env.example .env
```

Generate a different secret for `JWT_SECRET` and `PASSWORD_PEPPER` in your local terminal (run the command separately for each value), then paste each result directly into your local `backend/.env` file:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep `DATABASE_URL` empty for the local SQLite fallback. For PostgreSQL, set it to the Supabase transaction-pooler URL. Start the API with the local environment file:

```bash
fastapi dev app/main.py --env-file .env
```

The API runs at http://localhost:8000. Open http://localhost:8000/api/docs to inspect endpoints. Local development creates `backend/tutorinn.db` automatically. The `.env` file is ignored by Git; commit only `.env.example` with nonfunctional placeholders. Never paste generated secrets into chat or commit them.

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

The backend normalizes PostgreSQL URLs for Psycopg. FastAPI lifespan startup calls `initialize_database()`; the current MVP initializer creates missing SQLAlchemy tables and applies narrowly scoped compatibility columns/indexes for existing Student, Tutor, and tutoring-post records. It does not execute Alembic revisions. Alembic is configured separately under `backend/alembic/`; its checked-in baseline is a no-op marker and does not create the existing schema. See [backend/alembic/README.md](backend/alembic/README.md) before creating, stamping, or applying revisions.

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
- `/posts` — redirects to the authenticated Student/Tutor dashboard; the legacy demo-profile Tutoring Hub is no longer part of the production journey
- `/task-details` — redirects to the authenticated dashboard for response history
- `/task-details?id={id}` — Tutoring post details and response actions
- `/admin` — Individual Interested response review
- `/tutors` — read-only public Tutor directory
- `/tutors/{id}` — public Tutor details
- `/students` and `/students/{id}` — redirect to Student registration; Student profile management requires an authenticated account


## Verification

GitHub Actions builds the TypeScript frontend and runs the backend test suite. Current Beta tests cover Student/Tutor registration, rejection of email collisions with either legacy profile type, peppered Argon2id password hashing, legacy Argon2 hash migration after successful login, login, JWT tampering/expiry, Admin bootstrap and role checks, refresh rotation/reuse/expiry, CSRF rejection, logout, session revocation, suspended-account rejection, password changes, profile ownership, Student request CRUD, multi-tutor response privacy, tutor discovery filters, login lockout, production cookie flags, and legacy demo-mode restrictions. A passing build does not replace browser-based manual testing of sign-in, registration, session restoration, profile editing, and both dashboards.

## Vercel

The existing `vercel.json` routes `/api/*` to the FastAPI backend and other paths to the Vite frontend. Add `DATABASE_URL`, `JWT_SECRET`, `PASSWORD_PEPPER`, and `ADMIN_BOOTSTRAP_TOKEN` to backend environment variables before deploying. Add `ADMIN_API_KEY` only if the legacy demo Admin review workflow is intentionally enabled outside production. Verify actual deployment status and logs in Vercel; repository configuration alone does not prove a deployment is working.
 

## Current layered repository structure (implemented)

The application code is grouped by responsibility. The frontend keeps transport/API modules separate from UI, while the FastAPI implementation lives inside the backend `app` package. Database migration history is kept outside application code.

```text
frontend/src/
├── api/                 # Shared HTTP client and feature API modules
├── components/          # Reusable UI components
├── pages/               # Route-level pages (Home, About, Login, Register, dashboards, etc.)
├── layouts/             # Shared page layouts
├── context/             # Authentication and theme state
├── hooks/               # Reusable React hooks
├── types/               # Shared TypeScript contracts
├── App.tsx
└── main.tsx

backend/
├── app/                 # FastAPI application package
│   ├── routers/         # Domain-specific HTTP endpoints
│   ├── main.py          # FastAPI app creation and router registration
│   ├── auth.py          # JWT/password/session authentication helpers
│   ├── dependencies.py  # Request dependencies and legacy/demo guards
│   ├── database.py      # SQLAlchemy engine, Base and session dependency
│   ├── models.py        # SQLAlchemy persistence models
│   ├── schemas.py       # Pydantic request/response schemas
│   └── crud.py          # Existing business and database workflows
├── alembic/             # Alembic environment and revision history
├── tests/               # Backend automated tests
├── alembic.ini          # Alembic configuration
└── requirements*.txt

supabase/migrations/     # Existing Supabase SQL migration history
```

### Frontend layer rules

- `pages/` owns route-level screens; `components/` owns reusable presentation and interaction pieces.
- `api/` owns all browser-to-FastAPI communication. `api/api.ts` is the shared HTTP transport; focused modules such as `api/auth.ts`, `api/dashboard.ts`, and `api/posts.ts` compose feature requests.
- Pages and components must not call `fetch` or implement HTTP transport directly. They call the appropriate module in `api/`.
- Shared contracts belong in `types/`; keep page-specific presentation state local unless it is genuinely shared.

### Backend layer rules

- `app/main.py` creates the FastAPI application and registers routers. It should not become a home for endpoint implementation or business logic.
- `app/routers/` owns HTTP paths, methods, dependencies, status codes and response models.
- `app/models.py` and `app/schemas.py` remain separate: SQLAlchemy persistence versus Pydantic API contracts.
- `app/crud.py` retains current MVP database/business workflows. Extract a focused service/repository only when a real domain boundary justifies it.
- `app/database.py` owns SQLAlchemy engine/session/Base setup. `app/auth.py` and `app/dependencies.py` own reusable authentication and request dependencies.

### Migration ownership and Alembic

- `backend/alembic/` is the Alembic migration environment; each schema revision belongs in `backend/alembic/versions/` and has a unique revision ID and parent revision.
- `backend/alembic.ini` points Alembic at that environment. The environment imports `Base.metadata` from `app.models` and uses the same server-side database URL configuration as FastAPI.
- The repository already has deployed Supabase SQL migration history in `supabase/migrations/`. Those historical SQL files are preserved and must not be rewritten or deleted as part of this code-layout refactor.
- The Alembic baseline revision is a no-op history marker, not a schema-creation script. Do not run `alembic upgrade` against a fresh database expecting it to create TutorInn's existing tables. Existing environments must first be reconciled with the Supabase migration history and stamped only after schema equivalence is verified.
- Until a deliberate migration-ownership transition is reviewed, continue using the established Supabase SQL migration workflow for Supabase-managed schema changes. Do not independently apply the same schema change through both Alembic and Supabase SQL.
- Do not run migrations against a shared or production database without explicit approval, a backup/recovery plan and a reviewed upgrade path.

### Import and runtime entry points

- Run backend tests from `backend/` as configured in CI (`pytest -q`). The import package is `app`; the FastAPI object is `app.main:app`.
- Run the API locally from `backend/` with `fastapi dev app/main.py` (or `uvicorn app.main:app --reload`).
- Vercel's backend service entrypoint is `app.main:app`. The frontend remains a separate Vite service.
- Existing Supabase migrations remain under `supabase/migrations/`; Alembic revisions are separate versioned files under `backend/alembic/versions/`.


## Architecture refactor: verified package and migration rules

The current branch layout above is authoritative. Older roadmap/target examples elsewhere in this README describe earlier milestones; where an older example shows backend modules at the `backend/` root or frontend API modules under `services/`, use the current layout in this section instead.

### Backend initialization and imports

- The FastAPI import target is `app.main:app` with the backend service root set to `backend/`. Run backend commands from that directory so Python resolves the `app` package consistently.
- Backend modules import application code through the `app` package (for example, `from app.database import get_db` and `from app.routers import auth`). Do not use malformed mixed package paths or duplicate root-level modules.
- `app.main` creates the FastAPI application, registers routers, and invokes the existing database compatibility initializer. The initializer creates missing SQLAlchemy tables and applies only the documented MVP compatibility columns/indexes (not retired profile-claim columns); it does not execute Alembic revisions.
- The compatibility initializer must not recreate retired profile-claim columns. Schema changes belong in reviewed migration files, not new ad hoc startup alterations.

### Alembic workflow and migration ownership

Run Alembic commands from `backend/`:

```bash
alembic current
alembic history
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

- Review every autogenerated revision manually. Check constraints, indexes, foreign keys, data preservation, PostgreSQL compatibility, and downgrade behavior before committing it.
- The checked-in Alembic baseline is intentionally a no-op marker because the deployed schema already has historical Supabase SQL migrations. It does not create a fresh TutorInn schema.
- Never stamp an existing database at the baseline until its schema has been compared with the expected schema and the migration owner explicitly approves the stamp.
- Existing `supabase/migrations/` files are immutable historical records. Do not rewrite, delete, or re-run already-applied Supabase migrations.
- Do not apply the same schema change independently through both Supabase SQL and Alembic. Agree on one migration owner for each change and document the applied path.
- Application startup does not run `alembic upgrade`. Do not add automatic production migrations to FastAPI startup.
- Never run Alembic upgrade/stamp or Supabase migration operations against a shared/production database without explicit approval, backup/recovery planning, and a reviewed upgrade path.


## Current refactor status and contributor quick reference

This branch's verified architecture supersedes older roadmap examples above:

- Frontend feature API modules and shared HTTP transport: `frontend/src/api/`.
- Frontend reusable UI: `frontend/src/components/`; route screens: `frontend/src/pages/`; shared layouts: `frontend/src/layouts/`; shared contracts: `frontend/src/types/`.
- Backend application package: `backend/app/`; domain routers: `backend/app/routers/`; automated tests: `backend/tests/`.
- Alembic configuration: `backend/alembic.ini`; environment and revisions: `backend/alembic/`. Keep these migration assets outside the application package.
- Existing Supabase SQL history remains in `supabase/migrations/`. Do not apply the same schema change through both migration systems.

### Local verification commands

Run from the repository root:

```bash
cd backend
python -m compileall -q app tests
pytest -q
alembic -c alembic.ini heads
cd ../frontend
npm ci
npm test
npm run build
```

For Alembic commands and the no-op baseline safety procedure, read [backend/alembic/README.md](backend/alembic/README.md). Do not stamp or upgrade a shared/production database without explicit owner approval, a verified backup/recovery plan, and a reviewed migration path. Application startup does not automatically run Alembic upgrades.

AGENTS.md contains the corresponding mandatory coding-agent rules; update both documents when the implemented architecture or migration workflow changes.

## Roadmap and verification status — 17 Nov 2026

The complete Beta roadmap is tracked in [Issue #41](https://github.com/almahmudshafin20/2111584-TutorInn/issues/41). The stacked implementation is grouped as follows:

| Milestone | Scope | Implementation PR |
|---|---|---|
| 0 | Architecture foundation | [PR #42](https://github.com/almahmudshafin20/2111584-TutorInn/pull/42) |
| 1–3 | Authentication, profiles/ownership, Student and Tutor dashboards | [PR #43](https://github.com/almahmudshafin20/2111584-TutorInn/pull/43) |
| 4–5 | Personal tasks, groups and assignments | [PR #44](https://github.com/almahmudshafin20/2111584-TutorInn/pull/44) |
| 6–8 | Admin capabilities, security hardening, environment and deployment readiness | [PR #45](https://github.com/almahmudshafin20/2111584-TutorInn/pull/45) |

Milestones 0–6 are implemented. Milestone 7's code and automated verification are complete, but authenticated deployed Beta workflows still need verification. Milestone 8 has passing SQLite/PostgreSQL migration tests and live Supabase migration-history/RLS checks, but the FastAPI runtime database role and production startup on the latest branch commit are not yet verified. The latest branch commit is 5bb503aba9df0c19102a3fdefe0419048e71217c; CI run [#44107617892](https://github.com/almahmudshafin20/2111584-TutorInn/actions/runs/44107617892) passed, and the Preview /api/health and /api/subjects endpoints returned HTTP 200. This does not mean the branch has been deployed to Production.

### Source-level architecture audit

The frontend's feature API modules use the shared frontend/src/api/api.ts transport and shared TypeScript contracts live under frontend/src/types/. FastAPI startup and router registration remain focused in backend/app/main.py; Pydantic schemas and SQLAlchemy models are separate. The older MVP operations use backend/app/crud.py, while the newer Admin, Groups and Personal Tasks routers still contain substantial database/business logic in route handlers. This is a known refactoring gap: future changes should avoid growing it, and extraction should be done incrementally with regression tests. Do not describe the entire backend as already following a uniform CRUD/service boundary.