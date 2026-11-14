# TutorInn Agent Instructions

These instructions apply to every contributor and coding agent working in this repository. Read this file before implementing a feature, refactoring code, changing the database, or modifying project structure. These are persistent project rules: follow them regardless of chat history or which agent is working.

## 1. Project identity and established technology

TutorInn is a tutoring platform that retains its original MVP workflows while adding authenticated Student, Tutor, and Admin capabilities.

- Frontend: React and TypeScript, built with Vite.
- Backend: Python and FastAPI.
- Persistence: PostgreSQL through SQLAlchemy; the deployed application uses the existing Supabase PostgreSQL project.
- Validation: Pydantic request/response schemas on the backend and TypeScript contracts on the frontend.
- Authentication: TutorInn-managed accounts, signed JWT access tokens, and server-side refresh sessions. This is distinct from Supabase Auth.
- Deployment: Vercel for the deployed application/API configuration.

Do not introduce a replacement framework, database, authentication provider, or paid infrastructure dependency without an explicitly approved architectural decision. Prefer the existing free-tier-compatible deployment and services.

## 2. Milestone 0 architecture foundation

Milestone 0 established the repository's architectural boundaries and target organization. These folders and responsibilities are intentional, not decorative. New code must extend the existing architecture rather than recreate a parallel structure.

### 2.1 Frontend organization

The implemented frontend is under `frontend/src/`:

- `pages/`: route/page-level screens. Keep distinct screens in separate page files; Home, About, Task Details, and other unrelated pages must not be collapsed into one page.
- `components/`: reusable UI components shared by pages or features.
- `layouts/`: application-wide page shells and layout composition.
- `context/`: cross-application React context, including authenticated account and theme state.
- `hooks/`: reusable React hooks for shared stateful behavior.
- `services/`: feature-oriented API functions and browser/session helpers.
- `services/api.ts`: shared HTTP transport/client. Feature services must use this shared layer rather than duplicating fetch/axios configuration.
- `types/`: canonical shared TypeScript domain contracts and form types.
- `App.tsx`: application composition and route/page selection only; do not put whole feature implementations here.
- `main.tsx`: application bootstrap and provider mounting.
- `index.css`: global styles and design tokens.

Current feature service modules include `auth.ts`, `dashboard.ts`, `admin.ts`, `posts.ts`, `profiles.ts`, `subjects.ts`, and `session.ts`. Reuse the focused module that owns the behavior. The shared `types/domain.ts` contracts are authoritative; compatibility barrels such as `types/index.ts` and `shared.tsx` may remain for existing imports, but new code should import from the focused owner module.

Frontend rules:

1. Pages compose layouts and reusable components; keep business/data behavior out of presentation components.
2. UI components and pages must not implement their own HTTP transport. Call feature functions in `services/`, which delegate to `services/api.ts`.
3. Keep shared interfaces and domain types in `types/`, not copied across components.
4. Keep authenticated account state in the established context/provider; do not treat local storage or editable frontend state as proof of identity or permission.
5. Browser local storage key `tutorinn-profile-id` and `tutorinn-profile-type` belong to the legacy demo-profile workflow only. A selected demo profile is not secure authentication or proof of ownership.
6. Keep responsive, loading, empty, validation, and error states in mind when changing user-facing flows.

### 2.2 Backend organization

The implemented backend is under `backend/`:

- `main.py`: create/configure the FastAPI application and register routers; keep it focused.
- `routers/`: focused API endpoint groups, implemented with FastAPI `APIRouter`.
- `dependencies.py`: reusable request dependencies and authorization/context resolution.
- `schemas.py`: Pydantic request validation and public response contracts.
- `models.py`: SQLAlchemy persistence models and model-level helpers.
- `crud.py`: existing MVP business workflows and database read/write operations.
- `database.py`: engine/session configuration and current database initialization/compatibility behavior.
- `auth.py`: TutorInn authentication/token and role-related helpers.
- `tests/`: backend automated tests.

Current routers are domain-focused and include system, authentication, account, Beta requests, students, tutors, posts, profiles, and Admin functionality. Inspect the actual branch before assuming a route/module name or adding a new one.

Backend rules:

1. Routers own HTTP concerns: paths, methods, dependencies, status codes, and response models.
2. Validate and normalize request data using Pydantic schemas. Frontend validation is for usability, never a security boundary.
3. Route handlers should delegate business rules and persistence work to `crud.py` or a focused service/repository module when justified.
4. Keep SQLAlchemy models separate from Pydantic schemas and route definitions.
5. Reuse the existing database session/dependency and authentication/authorization helpers.
6. Keep `main.py` focused on application setup and router registration.
7. Do not add empty abstraction layers. Split CRUD/service/repository responsibilities when the feature scope genuinely benefits from it and do so consistently.
8. Enforce authentication, role permissions, account status, and record ownership on the server for every protected operation.

### 2.3 End-to-end request lifecycle

The normal frontend-to-backend flow is:

```text
Browser page/component
  -> focused frontend feature service
  -> shared frontend services/api.ts HTTP client
  -> FastAPI router
  -> FastAPI dependencies and authorization
  -> Pydantic request validation
  -> CRUD/business workflow (or justified domain service)
  -> SQLAlchemy model and database session
  -> Pydantic response model
  -> shared frontend API client
  -> page/component state and UI
```

Keep each boundary clear. Do not bypass the shared API client, router/dependency authorization, server-side validation, or database access layer for convenience.

### 2.4 Responsibilities and validation boundaries

- Frontend controls and TypeScript types provide immediate feedback and describe expected shapes. They do not authorize users or guarantee trusted data.
- FastAPI/Pydantic schemas validate request fields, normalize supported values, and define response shapes.
- CRUD/domain workflows enforce business rules, ownership, allowed state transitions, and cross-record constraints.
- SQLAlchemy models and database constraints protect persisted structure, relationships, uniqueness, and integrity.
- Database constraints are the final persistence-level safeguard, not a substitute for clear API errors and business validation.
- Public Student/Tutor response schemas must not expose private contact or account-security data.
- Never trust a user ID, role, profile ID, account status, or ownership claim merely because the browser supplied it.

### 2.5 Database and Supabase access model

Use the existing Supabase PostgreSQL project and its existing data. Do not create a replacement Supabase project or database for routine development, preview, or deployment.

- The frontend does not connect directly to Supabase. It communicates with FastAPI.
- FastAPI accesses PostgreSQL through SQLAlchemy using the configured server-side database connection (`DATABASE_URL`, with `POSTGRES_URL` as the supported fallback where configured).
- TutorInn uses its own JWT/account identity model. Supabase Auth identities and `auth.uid()` are not the application's current identity source.
- The public tables `students`, `tutors`, `learning_posts`, `interest_responses`, `user_accounts`, `refresh_sessions`, and `security_events` have Row Level Security enabled.
- Direct table, sequence, and schema privileges are revoked from Supabase Data API roles `anon` and `authenticated` (and PostgreSQL `PUBLIC`) under the current deny-by-default architecture. Server-side privileged database access is retained for FastAPI.
- These tables intentionally have no browser-facing RLS policies. The absence of policies is deliberate: browser roles should be denied direct access. Do not add permissive policies such as `USING (true)`, or grant browser roles direct table access, to make a feature work.
- RLS is an additional database/API boundary, not a replacement for FastAPI authentication, authorization, and ownership checks.
- The applied access-control migration is `supabase/migrations/20261114133407_secure_public_schema_rls_and_api_privileges.sql`. Preserve it as versioned project history.
- Default privileges currently restrict Data API access for future tables/sequences created by the configured database owner. Every future public table still requires explicit RLS/grant review.
- If direct Supabase client access is ever proposed, stop and design a trusted identity mapping and narrow policies first. Do not assume TutorInn JWTs are valid Supabase Auth JWTs.

Never put database URLs, service-role keys, JWT secrets, bootstrap tokens, passwords, or other credentials in source code, logs, documentation examples, commits, screenshots, or chat. Use environment variables and deployment secret storage. Examples must contain placeholders only.

### 2.6 Data integrity and legacy MVP compatibility

The refactor and Beta architecture must preserve the existing MVP unless an explicitly approved requirement says otherwise.

Preserve, where present:

- Student and Tutor profile CRUD and existing profile fields.
- Multiple subjects on Student profiles, Tutor profiles, and tutoring posts.
- Existing tutoring-post creation, listing, editing, deletion, and pagination.
- Post-to-author-profile relationships.
- Separate Interested and Not Interested responses for each post/profile pair.
- Admin review behavior for responses that require approval.
- Existing public response privacy, endpoint paths, HTTP methods, status codes, and documented API contracts.
- Existing records, IDs, relationships, and historical data.

Do not duplicate an existing feature or create parallel tables/workflows without first inspecting the current implementation. Do not infer account ownership from matching email addresses alone. Legacy profile linking must use the approved secure claim/verification workflow, preserve the existing profile row and related data, and be transactional and single-use. Never destructively reset or seed a deployed/shared database.

### 2.7 API organization and documentation

- Group endpoints by domain under `backend/routers/`.
- Keep OpenAPI/Swagger documentation at `/api/docs` when enabled by the deployment configuration.
- Document authentication requirements, role permissions, request/response schemas, status codes, and pagination/filter parameters when adding or changing endpoints.
- Preserve existing MVP endpoint behavior wherever practical. If a breaking change is required, document it and add tests.
- Keep frontend feature services aligned with backend API contracts and shared TypeScript types.

### 2.8 Migrations and schema changes

- Inspect current models, migrations, and deployed schema before changing persistence.
- Use reviewed, version-controlled migrations for schema changes; do not rely on ad hoc production startup table alterations as the long-term migration strategy.
- Test migration upgrade paths against representative existing data before applying to a deployed/shared database.
- Migrations must be safe, repeatable where appropriate, and preserve existing records and relationships.
- Never drop, truncate, rewrite, or bulk-transform production/shared data without explicit authorization, a verified backup/recovery plan, and a documented reason.
- Keep migration SQL in the repository and ensure deployed changes have corresponding versioned migration history.
- Review RLS, grants, indexes, constraints, and ownership implications for every new table or sensitive column.

### 2.9 Security architecture principles

- Keep the roles `student`, `tutor`, and `admin` distinct.
- Authentication and authorization are backend responsibilities. Frontend route guards are only a user-experience layer.
- Resolve account status and role from trusted server-side state. Never authorize based only on local storage, session storage, editable frontend state, cookie names, or an unverified token payload.
- Every protected endpoint must enforce the required role and resource ownership.
- Return 401 for missing/invalid authentication and 403 for a valid identity lacking permission, as appropriate.
- Keep private profile fields, credentials, refresh tokens, claim tokens, and security-event data out of public responses.
- Use secure password hashing and the established token/session lifecycle. Never store plaintext passwords or raw refresh-token values in the database.
- Cookie-authenticated state-changing requests must retain the configured CSRF protections; production cookies must use Secure, HttpOnly, and an appropriate SameSite policy.
- Do not log secrets or raw tokens. Security events should record useful context without exposing credentials.
- Do not treat opening browser Developer Tools as an attack or automatically log users out for doing so.
- Do not weaken RLS, grants, authentication, or ownership checks to work around a frontend/API defect.

## 3. The six architecture recommendations

Every new feature and refactor must preserve all six recommendations:

1. **Frontend pages/components:** split UI into dedicated files under `frontend/src/pages/` and `frontend/src/components/`.
2. **API service layer:** centralize API calls in `frontend/src/services/api.ts` (or a focused feature service that uses the shared API layer).
3. **TypeScript types:** keep shared types in `frontend/src/types/`, not scattered through components.
4. **Backend routers:** organize endpoints into modules under `backend/routers/`, not all in `main.py`.
5. **Models and schemas:** separate database models and request/response schemas from route definitions and from each other.
6. **Business/data logic:** place database operations and business logic in CRUD/service/repository modules, not directly in route handlers.

## 4. The three highest-priority frontend recommendations

Check these on every frontend feature:

1. New pages and UI pieces belong in `frontend/src/pages/` or `frontend/src/components/`.
2. API calls must go through `frontend/src/services/api.ts` via a focused service module; do not issue HTTP requests directly inside UI components.
3. Shared TypeScript types belong in `frontend/src/types/`.

## 5. Workflow for every feature or refactor

1. Inspect the current implementation, repository structure, relevant tests, API contracts, and database impact before editing.
2. Check the current target branch. Do not assume an open PR's changes are present in `main`.
3. Reuse existing components, API services, types, routers, models, schemas, dependencies, and CRUD/service functions where appropriate.
4. Implement in the correct existing folders. Do not create parallel or duplicate architecture.
5. Keep changes focused and preserve existing working behavior and API compatibility unless a change is explicitly required.
6. Add or update tests for changed behavior, permissions, validation, migrations, and regression risks.
7. Run relevant backend tests/checks and the frontend type check/production build when applicable. Report exact commands and outcomes; never claim a check passed unless it was run successfully.
8. Review the complete changed-file list. Confirm files are in the correct locations and no unrelated changes or secrets are included.
9. Update README and relevant technical documentation when actual architecture, setup, API contracts, or supported workflows change.
10. Report any unverified behavior or manual testing still required. Automated checks do not prove browser-level acceptance.

## 6. Testing and quality expectations

Organize tests around behavior and security boundaries, not only individual files.

- Backend: endpoint behavior, Pydantic validation, CRUD/business rules, database constraints, and migration safety.
- Authentication: registration, login, invalid credentials, token expiry, refresh rotation, logout, lockout, and session revocation.
- Authorization: Student, Tutor, and Admin restrictions on backend endpoints.
- Ownership: one account cannot read or modify another account's private profile or protected records.
- JWT/session security: tampered signatures/claims, forged Admin role, invalid algorithms/claims, expired/revoked refresh tokens, and token reuse.
- Frontend: type checking, production build, route behavior, loading/empty/error states, and service-layer API handling.
- Database: migration upgrade paths, RLS state, grants, and preservation of existing MVP data.
- Deployment: verify health and relevant API flows without exposing secrets or using destructive tests against production data.

Before requesting review, use the checklist below.

## 7. GitHub issue, branch, and pull-request rules

- Use one focused issue, one feature branch, and one pull request for each approved task, unless the project owner explicitly requests otherwise.
- Include the PR number in the branch name, for example `feat/42-short-description` or `fix/43-short-description`.
- Create a feature branch from the latest appropriate base branch, normally `main`.
- Link the PR to its issue using GitHub's closing keyword where appropriate (for example, `Closes #42`).
- The PR description must summarize what changed, mention relevant related work where appropriate, and list verification performed.
- Do not create extra issues or PRs for the same task without explicit direction.
- **Never create, edit, merge, close, delete, or otherwise modify GitHub resources without the project owner's explicit approval for the requested action.**
- **Never merge a PR into `main` unless the project owner explicitly authorizes that merge.**
- An instruction to implement code or open a PR does not imply permission to merge it.
- When working on an already-approved PR, keep changes on its existing feature branch unless the project owner directs otherwise.
- A request to update a file does not authorize creating a new issue or PR.

## 8. Quality checklist before requesting review

- [ ] Pages and reusable UI are in the correct frontend folders.
- [ ] No direct fetch/axios request logic has been added inside UI components; API calls use the shared service layer.
- [ ] Shared TypeScript types are in `frontend/src/types/`.
- [ ] Backend endpoints are in focused router modules.
- [ ] `main.py` remains focused on app setup and router registration.
- [ ] Database models and API schemas remain separate.
- [ ] Route handlers delegate business/database work to CRUD/service/repository code.
- [ ] Authentication, role permissions, account status, and ownership are enforced server-side.
- [ ] RLS and database grants remain consistent with the deny-by-default Supabase access model.
- [ ] Migrations preserve existing MVP data and have been reviewed/tested.
- [ ] Relevant tests/checks have been run and their results are accurately reported.
- [ ] Frontend production build has been run when frontend code changes.
- [ ] Existing behavior and compatibility have been considered.
- [ ] Documentation reflects the actual implementation, not an unimplemented target design.
- [ ] PR references the correct issue and includes a clear summary.
- [ ] No secrets or credentials are included in source or logs.
- [ ] No merge or other GitHub mutation is performed without explicit approval.

## 9. When a rule appears not to fit

Do not ignore a rule silently. First inspect the current code and explain why the existing pattern is unsuitable. Prefer a small, consistent extension of the established architecture. Document any justified exception in the PR description so it can be reviewed. Do not introduce abstractions solely to satisfy folder naming.

## 10. Source of truth and keeping this file current

This file is the repository's persistent agent/development-guideline reference. The actual checked-out code, versioned migrations, and current README describe what is implemented; this file describes the boundaries and rules agents must preserve.

If a chat summary or informal instruction conflicts with the current repository architecture, inspect the code and follow the verified repository state unless the project owner explicitly approves a change to the guidelines. Distinguish implemented behavior from future roadmap work. Update this file only through an explicitly approved, reviewed repository change.
