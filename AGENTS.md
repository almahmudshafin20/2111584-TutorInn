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
- `api/`: feature-oriented API functions and browser/session helpers.
- `api/api.ts`: shared HTTP transport/client. Feature services must use this shared layer rather than duplicating fetch/axios configuration.
- `types/`: canonical shared TypeScript domain contracts and form types.
- `App.tsx`: application composition and route/page selection only; do not put whole feature implementations here.
- `main.tsx`: application bootstrap and provider mounting.
- `index.css`: global styles and design tokens.

Current feature API module modules include `auth.ts`, `dashboard.ts`, `admin.ts`, `posts.ts`, `profiles.ts`, `subjects.ts`, and `session.ts`. Reuse the focused module that owns the behavior. The shared `types/domain.ts` contracts are authoritative; compatibility barrels such as `types/index.ts` and `shared.tsx` may remain for existing imports, but new code should import from the focused owner module.

Frontend rules:

1. Pages compose layouts and reusable components; keep business/data behavior out of presentation components.
2. UI components and pages must not implement their own HTTP transport. Call feature functions in `api/`, which delegate to `api/api.ts`.
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

Current routers include system, authentication, account, Beta requests, students, tutors, posts, profiles, Admin, moderation, personal tasks, and groups. Some newer routers currently contain their own persistence/business logic; inspect the actual implementation before assuming every route delegates through a separate CRUD/service layer.

Backend rules:

1. Routers own HTTP concerns: paths, methods, dependencies, status codes, and response models.
2. Validate and normalize request data using Pydantic schemas. Frontend validation is for usability, never a security boundary.
3. Route handlers should delegate business rules and persistence work to `crud.py` or a focused service/repository module when justified. **Current audited exception:** the newer Admin, Groups, and Personal Tasks routers still contain substantial query/business logic directly in route handlers; avoid expanding this pattern and treat consistent extraction into focused services as outstanding refactoring, not as already complete.
4. Keep SQLAlchemy models separate from Pydantic schemas and route definitions.
5. Reuse the existing database session/dependency and authentication/authorization helpers.
6. Keep `main.py` focused on application setup and router registration.
7. Do not add empty abstraction layers. Split CRUD/service/repository responsibilities when the feature scope genuinely benefits from it and do so consistently.
8. Enforce authentication, role permissions, account status, and record ownership on the server for every protected operation.

### 2.3 End-to-end request lifecycle

The normal frontend-to-backend flow is:

```text
Browser page/component
  -> focused frontend feature API module
  -> shared frontend api/api.ts HTTP client
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
- As verified against the live Supabase project on 20 Nov 2026 (`pg_class` and `information_schema` queries), all 23 public tables have Row Level Security enabled and no table grants to `anon` or `authenticated`. Supabase's security advisor reports only the INFO-level "RLS enabled, no policy" notice for these tables, which is intentional under the deny-by-default model.
- Direct table, sequence, and schema privileges are revoked from Supabase Data API roles `anon` and `authenticated` (and PostgreSQL `PUBLIC`) under the current deny-by-default architecture. Server-side privileged database access is retained for FastAPI.
- These tables intentionally have no browser-facing RLS policies. The absence of policies is deliberate: browser roles should be denied direct access. Do not add permissive policies such as `USING (true)`, or grant browser roles direct table access, to make a feature work.
- RLS is an additional database/API boundary, not a replacement for FastAPI authentication, authorization, and ownership checks.
- Preserve the complete applied Supabase SQL migration history. The initial deny-by-default access migration is `20261114133407_secure_public_schema_rls_and_api_privileges.sql`; later RLS migrations include `20261117144546_secure_tutor_verification_admin_table.sql`, `20261117144548_reports_and_subject_catalogue.sql`, and `20261117144551_enable_rls_on_private_learning_tables.sql`. Never rewrite historical applied migrations.
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

Do not duplicate an existing feature or create parallel tables/workflows without first inspecting the current implementation. Do not infer account ownership from matching email addresses alone. Existing legacy profiles are not automatically linked to new accounts; new registrations create new profile records, and existing records must remain untouched. Never destructively reset or seed a deployed/shared database.

### 2.7 API organization and documentation

- Group endpoints by domain under `backend/app/routers/`.
- Keep OpenAPI/Swagger documentation at `/api/docs` when enabled by the deployment configuration.
- Document authentication requirements, role permissions, request/response schemas, status codes, and pagination/filter parameters when adding or changing endpoints.
- Preserve existing MVP endpoint behavior wherever practical. If a breaking change is required, document it and add tests.
- Keep frontend feature API modules aligned with backend API contracts and shared TypeScript types.

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
- Keep private profile fields, credentials, refresh tokens, and security-event data out of public responses.
- Password storage is salt + pepper + hash: Argon2id generates a random salt for every password and stores it inside the hash; the server-side `PASSWORD_PEPPER` is applied with HMAC-SHA256 before hashing. Do not add a separate salt column or a manually generated salt, and do not reuse a salt across passwords.
- Use Argon2id password hashing with the server-side `PASSWORD_PEPPER` secret. Apply the pepper through HMAC-SHA256 before Argon2id; require a separate random secret of at least 32 characters from environment/deployment secret storage. Never commit, log, expose, rotate casually, or store the pepper in the database. Keep the versioned hash prefix intact so verification can select the correct scheme.
- Preserve backward compatibility for pre-pepper Argon2 hashes: verify the legacy hash only on login, then upgrade it to the peppered format after successful verification and before issuing a session. Never bulk-reset or invalidate existing passwords during migration.
- Use the established token/session lifecycle. Never store plaintext passwords or raw refresh-token values in the database.
- Cookie-authenticated state-changing requests must retain the configured CSRF protections; production cookies must use Secure, HttpOnly, and an appropriate SameSite policy.
- Do not log secrets or raw tokens. Security events should record useful context without exposing credentials.
- Do not treat opening browser Developer Tools as an attack or automatically log users out for doing so.
- Do not weaken RLS, grants, authentication, or ownership checks to work around a frontend/API defect.

### 2.10 UI design, shared layout, and responsive navigation

The implemented frontend uses the existing React page/layout/component structure. Preserve these boundaries when changing the visual experience:

- Keep Home and About as separate public pages. Keep Login and Register as separate authentication pages.
- `components/SiteHeader.tsx` owns the public header and authenticated role-aware desktop navigation. Public navigation stays focused on the brand, About, Log in, and Create account. Do not reintroduce the legacy demo-profile selector or theme switch into the normal public header.
- `layouts/AppLayout.tsx` owns the shared page shell and authenticated mobile bottom navigation. Keep Student, Tutor, and Admin navigation role-aware and link only to implemented routes/sections; do not imply a future milestone is already implemented.
- Keep dashboard business logic and API access in the existing page/service boundaries. UI navigation must not become an authorization mechanism; every protected operation remains enforced by FastAPI.
- `index.css` is the current shared design-token and component-style entry point. Reuse its tokens and shared control styles rather than adding conflicting one-off palettes or control treatments.
- Support both light and dark themes through `ThemeContext`. Respect the saved `tutorinn-theme` preference, apply the selected `data-theme` and `color-scheme`, and keep both modes readable and keyboard accessible. Do not remove the user-facing theme toggle or force a theme on every page load.
- Inputs, selects, textareas, buttons, checkboxes, radio controls, and other interactive elements must have deliberate, consistent styling. Select controls must not look like unfinished browser-default widgets; retain native keyboard and accessibility behavior while styling their appearance.
- Interactive controls need visible focus, hover, selected, disabled, and validation states where applicable. Use semantic labels, accessible names, sufficient contrast, and keyboard operation.
- Use responsive desktop/tablet/mobile layouts. Auth pages should remain split-screen where space permits and become form-first on narrow screens. Authenticated mobile pages must leave enough content space for the fixed bottom navigation and respect safe-area insets.
- Use restrained surface depth, borders, shadows, and motion. Respect `prefers-reduced-motion`; do not add decorative effects that reduce clarity or performance.
- Inter is the preferred first entry in the current system sans-serif font stack; do not add an external font dependency without checking the existing bundle and project requirements.

## 3. The six architecture recommendations

Every new feature and refactor must preserve all six recommendations:

1. **Frontend pages/components:** split UI into dedicated files under `frontend/src/pages/` and `frontend/src/components/`.
2. **API service layer:** centralize API calls in `frontend/src/api/api.ts` (or a focused feature API module that uses the shared API layer).
3. **TypeScript types:** keep shared types in `frontend/src/types/`, not scattered through components.
4. **Backend routers:** organize endpoints into modules under `backend/app/routers/`, not all in `main.py`.
5. **Models and schemas:** separate database models and request/response schemas from route definitions and from each other.
6. **Business/data logic:** place database operations and business logic in CRUD/service/repository modules, not directly in route handlers.

## 4. The three highest-priority frontend recommendations

Check these on every frontend feature:

1. New pages and UI pieces belong in `frontend/src/pages/` or `frontend/src/components/`.
2. API calls must go through `frontend/src/api/api.ts` via a focused API module; do not issue HTTP requests directly inside UI components.
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
9. When the implemented architecture changes, update **both `README.md` and `AGENTS.md` in the same approved change**: README explains the verified architecture to developers; AGENTS gives future AI agents concrete rules for extending it. Also update setup/API documentation when those contracts change.
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

**Reusable review template, not a repository-wide milestone-status list:** these boxes intentionally start unchecked. For each concrete PR, verify only applicable requirements and record evidence in that PR/Issue. Do not tick this permanent template merely because a folder or feature exists.

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

## 10. Source of truth and documentation synchronization

Use the repository artifacts for their distinct purposes:

- **Actual code and versioned migrations** are the evidence of what is implemented.
- **`README.md`** explains the verified product, architecture, setup, API, database, testing, and deployment behavior to human contributors.
- **`AGENTS.md`** tells future AI coding agents and contributors how to work safely within that architecture: where code belongs, which boundaries to preserve, what to inspect, and what to test.

### Mandatory architecture synchronization rule

Whenever an implemented architectural boundary, folder responsibility, request/data flow, authentication or authorization model, database access model, or major persistence design changes:

1. Update `README.md` to explain **what the new architecture is**, why the boundary exists, and which parts are implemented.
2. Update `AGENTS.md` to explain **how an AI agent must work with the new architecture**, including placement rules, required reuse, security constraints, and verification steps.
3. Make both documentation updates in the same approved change/PR as the architecture change whenever practical. Do not leave one document describing an obsolete design.
4. Keep the wording complementary, not duplicated: README is explanatory project documentation; AGENTS is actionable operating guidance.
5. Label planned or partially implemented architecture as **target/planned**. Do not describe it as implemented until code and tests verify it.
6. If implementation changes but the documentation cannot yet be updated accurately, call out the mismatch explicitly in the PR and resolve it before treating the architecture work as complete.

For setup, API, or deployment changes that do not alter architecture, update the relevant README sections. For agent workflow or coding-rule changes that do not alter architecture, update AGENTS. Do not change either file merely to make them word-for-word identical.

If a chat summary or informal instruction conflicts with the checked-out code, inspect the code and versioned migrations and follow the verified repository state unless the project owner explicitly approves an architectural change. Preserve the distinction between implemented behavior and future roadmap work.

## Current repository layer boundaries (mandatory)

- Frontend API communication belongs in `frontend/src/api/`. Keep the shared transport in `api/api.ts` and feature request modules beside it. Pages/components must call these modules and must not issue direct HTTP requests.
- Route-level screens belong in `frontend/src/pages/`; reusable UI belongs in `frontend/src/components/`; shared shells belong in `frontend/src/layouts/`; shared TypeScript contracts belong in `frontend/src/types/`.
- Backend application code belongs in `backend/app/`. Put FastAPI endpoint modules in `app/routers/`; keep `app/main.py` focused on application creation and router registration.
- Keep SQLAlchemy models in `app/models.py`, Pydantic contracts in `app/schemas.py`, database/session setup in `app/database.py`, authentication helpers in `app/auth.py`, request dependencies in `app/dependencies.py`, and existing business/data workflows in `app/crud.py`.
- Do not recreate the former backend-root module layout or introduce a second implementation of the same module. Update imports to use the `app` package.
- Alembic configuration is `backend/alembic.ini`; environment is `backend/alembic/env.py`; numbered revisions belong in `backend/alembic/versions/`. Alembic metadata comes from `app.models.Base.metadata`.
- Preserve the existing `supabase/migrations/` SQL history. The Alembic baseline is a no-op marker and does not create the existing schema. Do not stamp an existing database until schema equivalence has been checked, and do not apply the same schema change through both migration systems.
- Never run or apply database migrations to a shared/production database without explicit project-owner approval and a reviewed backup/recovery plan.
- Runtime entrypoint is `app.main:app` from the `backend/` service root. CI runs backend tests from `backend/`.


## 11. Verified package imports, startup, and Alembic workflow

### Backend package and runtime

- Treat `backend/` as the Python service root and `backend/app/` as the application package. CI tests run with the working directory set to `backend/`; Vercel's FastAPI entrypoint is `app.main:app`.
- Use package imports rooted at `app`, such as `from app.database import get_db`, `from app.models import Student`, and `from app.routers import auth`. Do not add a second copy of application modules at the backend root.
- Keep `app/main.py` limited to FastAPI construction, router registration, startup integration, and static frontend mounting where configured.
- `app/database.py` owns engine/session/Base setup and the current compatibility initializer. The initializer may create missing SQLAlchemy tables and narrowly scoped compatibility columns/indexes for existing MVP deployments; it must not recreate retired profile-claim columns or become a substitute for reviewed migrations.
- Application startup must not automatically execute Alembic upgrades. Do not introduce production schema changes as an import-time side effect.

### Alembic and existing Supabase SQL history

- Configuration: `backend/alembic.ini`; environment: `backend/alembic/env.py`; revisions: `backend/alembic/versions/*.py`.
- The Alembic environment imports `Base.metadata` from `app.models` and obtains the same server-side database URL configuration as the application.
- Run `alembic current`, `alembic history`, `alembic revision --autogenerate -m "description"`, and `alembic upgrade head` from the `backend/` directory.
- Review autogenerated migrations manually; do not trust autogeneration to detect data migrations, all constraints, RLS policies, grants, or every database-specific operation.
- The current Alembic baseline revision is intentionally empty/no-op. It records a baseline point; it does not create the existing TutorInn schema. Only stamp a database after schema equivalence has been reviewed and the project owner approves.
- Preserve all applied `supabase/migrations/` files as historical source records. Do not edit or delete them, and do not apply the same change through both Supabase SQL and Alembic.
- Do not run migration upgrades or stamp operations against shared/production databases without explicit owner approval, a verified backup/recovery plan, and a reviewed upgrade path.

### Frontend API imports

- Every feature request module and shared HTTP transport belongs in `frontend/src/api/`.
- Import feature functions from `../api/<feature>` or `./api/<feature>`, never from the retired `services/` path.
- `api/api.ts` is the single shared transport boundary. Pages, contexts and components must not duplicate raw HTTP configuration.
- Keep pages, components, layouts, hooks, contexts, and shared types in their respective folders. Do not combine unrelated screens into one page or move API calls back into UI components.
- When moving a module, update every import and compatibility re-export in the same change, then search the full frontend tree for stale `services/` imports before committing.

### Required verification for architecture/import changes

From the repository root:

```bash
cd backend
python -m compileall -q app tests
pytest -q
cd ../frontend
npm ci
npm test
npm run build
```

Also verify that Vercel's backend entrypoint remains `app.main:app`, inspect the Alembic revision graph, and check that no stale `services/` frontend imports or invalid backend import syntax remain. Update this file and `README.md` together whenever the implemented folder layout or migration workflow changes.


## 12. Current verified architecture and migration operating rules

These rules describe the implemented branch layout and take precedence over older illustrative/target folder trees elsewhere in this file:

### Frontend placement

- Put all browser-to-FastAPI request functions and shared HTTP transport in `frontend/src/api/`. Use the shared `api/api.ts` transport from feature modules; never add raw `fetch`/Axios calls to pages, components, or contexts.
- Put route-level screens in `frontend/src/pages/`, reusable UI in `frontend/src/components/`, shared shells in `frontend/src/layouts/`, cross-app state in `frontend/src/context/`, reusable behavior in `frontend/src/hooks/`, and canonical TypeScript contracts in `frontend/src/types/`.
- Keep distinct screens (including Home, About, and Task Details) as separate page files. Do not create parallel `services/` modules or reintroduce imports from the retired frontend services path.

### Backend placement and startup

- Treat `backend/` as the Python service root and `backend/app/` as the sole application package. The FastAPI import target is `app.main:app`.
- Put domain HTTP endpoints in `backend/app/routers/`; SQLAlchemy models in `app/models.py`; Pydantic contracts in `app/schemas.py`; engine/session/Base and current compatibility initialization in `app/database.py`; authentication helpers in `app/auth.py`; request dependencies in `app/dependencies.py`; existing business/data workflows in `app/crud.py`.
- Keep `app/main.py` focused on FastAPI construction, router registration, lifespan integration, and configured static frontend mounting. Database compatibility initialization runs through FastAPI lifespan, not as an import-time side effect.
- Do not duplicate modules at the `backend/` root, invent empty service/repository packages, or relocate Alembic files into `backend/app/` just to match an older proposed tree.

### Alembic and database safety

- Keep configuration at `backend/alembic.ini`, Alembic environment and revision scripts under `backend/alembic/`, and numbered revisions under `backend/alembic/versions/`. The environment must use the same SQLAlchemy metadata and server-side database URL resolution as the application.
- The current baseline revision `20261116_0001` is deliberately a no-op marker. It does not create TutorInn's existing tables. Never describe it as a fresh-database schema bootstrap.
- Read `backend/alembic/README.md` before generating, stamping, or applying a revision. Inspect autogenerated operations and explicitly review data preservation, foreign keys, indexes, constraints, PostgreSQL compatibility, and downgrade behavior.
- Preserve applied `supabase/migrations/` SQL files as historical records. Do not apply one schema change independently through both Supabase SQL and Alembic; agree on and document one migration path per change.
- FastAPI startup must not run `alembic upgrade`. The existing `initialize_database()` compatibility behavior is separate and must not be expanded casually or used as a substitute for reviewed migrations.
- Never run upgrade/stamp operations against a shared or production database without explicit project-owner approval, a verified backup/recovery plan, and a reviewed migration path. Do not expose database credentials in logs or documentation.

### Required verification for architecture/documentation changes

From the repository root, run the relevant checks (backend commands from `backend/`, frontend commands from `frontend/`):

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

- Confirm the Vercel backend entrypoint remains `app.main:app` and CI runs backend tests from `backend/`.
- Search for stale frontend `services/` imports and duplicate backend-root modules after moves.
- Keep `README.md` and this file synchronized in the same architecture change: README explains the verified design to human contributors; AGENTS gives concrete placement, safety, and verification rules to coding agents.
- Report exactly which checks passed, failed, or were not run. A successful CI run verifies only the commit and checks shown by that run; do not claim manual browser/device or production-database testing unless it was actually performed.

## Current source-audit note

- The frontend uses feature API modules (frontend/src/api/*.ts) that delegate HTTP transport, credentials, refresh handling and error parsing to frontend/src/api/api.ts. Shared domain/auth contracts live under frontend/src/types/.
- backend/app/main.py is focused on FastAPI setup, middleware and router registration. Pydantic schemas and SQLAlchemy models are separate modules.
- The legacy MVP CRUD workflows remain in backend/app/crud.py. Newer Admin, Groups and Personal Tasks routers currently contain substantial SQLAlchemy queries and business operations directly in route handlers. This is a known architecture consistency gap; do not claim that all backend business logic has already been extracted into CRUD/services. Refactor incrementally with tests rather than introducing empty abstraction layers.
- Live Supabase review on 17 Nov 2026 found 15 public tables with RLS enabled and no direct SELECT privilege for anon or authenticated; service_role has SELECT. This does not by itself prove which PostgreSQL role the deployed FastAPI runtime uses.
- Automated checks (backend tests, frontend tests and build, dependency audit, migration chain) run in CI for every code change and must pass before a change is described as verified.

## Source-level audit follow-up

The latest source audit confirmed the frontend feature API modules use the shared `frontend/src/api/api.ts` transport, FastAPI startup and router registration remain focused in `backend/app/main.py`, and SQLAlchemy models are separate from Pydantic schemas. The existing MVP workflows use `backend/app/crud.py`. The Admin, Groups and Personal Tasks routers still contain substantial database queries and business rules directly in route handlers; this is a known incremental refactoring gap. Do not claim a uniform backend CRUD/service boundary or add empty abstraction layers.

Two issues found in the Admin source review have been corrected:
- Admin URL synchronization now lists every state value it serializes, including `createdFrom`, `createdTo` and `ownerAccountId`, in the React effect dependency array. Keep the dependency list and its regression assertion aligned whenever URL-persisted filters change.
- Removed the later legacy duplicate `GET /api/admin/groups` registration. Keep one paginated/filterable endpoint and add a regression assertion that the route is registered once.

The regression assertions were added to `frontend/tests/admin.test.mjs`. Re-run CI after any change to these areas before describing it as verified.

## Account deletion safety requirements

- Student/Tutor deletion is request-and-approval only. Never add a direct self-service DELETE endpoint for user accounts. Legacy demo profile DELETE routes must also reject account-linked Student/Tutor profiles.
- A request must verify the current password, mark the account `deletion_pending`, and revoke every active refresh session before returning success.
- Only an authenticated Admin may approve or reject a pending request. Rejection restores the account; approval must delete account-owned content transactionally and retain a non-identifying decision record.
- Permanent deletion must account for profile posts/responses/reports, personal tasks, group memberships, assignments, groups owned by the Tutor, and group tasks authored by the account. Remove dependent rows before deleting the account; do not damage other users' accounts or shared records.
- After approval, clear direct account/email identifiers and the user-provided deletion reason from the retained request record. Security events may retain a pseudonymous internal account reference alongside IP, timestamp, event type and user-agent so repeated registrations remain countable after deletion; do not retain email, profile content, passwords, tokens or unnecessary free-text personal data.
- Treat shared IP addresses as investigation signals, never conclusive proof that multiple accounts belong to one person.
- Do not apply the Supabase migration to a shared/Production database without explicit approval and a reviewed backup/recovery plan. Keep migration SQL and SQLAlchemy model definitions aligned.


## Account deletion method choice update — 17 Nov 2026

- The Student/Tutor deletion request must include a requested method: `anonymize` or `complete`.
- Admin review must explicitly select the final method; if the Admin does not override, use the user's requested method. Persist both values on the non-identifying deletion receipt.
- `complete` removes account-owned content wherever possible. `anonymize` deletes the account/profile, changes authored learning posts to a generic deleted-user author with profile links cleared, and retains eligible shared posts. Tutor-owned groups are removed because the group owner FK cannot point to a deleted account.
- Keep security-event IP/time/type/user-agent evidence for abuse investigations, but clear direct email/account links and free-text content. IP sharing is not proof of common identity.
- The backend has an optional SMTP notification sender for the Admin's final deletion method. Configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM and SMTP_USE_TLS in the deployment environment. Check notification_status: `sent`, `not_configured` or `failed`; never claim an email was sent unless status is `sent`.
- The database changes are in migrations `20261117160000_admin_approved_account_deletion.sql`, `20261117163000_account_deletion_method_choices.sql` and `20261117164500_account_deletion_email_notification_status.sql`. CI and live migration verification are required before deployment.


## Group-task video link rules

- Store only the user's Google Drive share URL; TutorInn does not upload, proxy, or host the video file.
- Validate every link on the backend. Accept HTTPS URLs hosted exactly at `drive.google.com` and supported Drive file-ID forms only. Never render arbitrary user-provided iframe URLs.
- Display the validated Drive share URL as a normal external link; do not embed or stream the video in TutorInn.
- Explain that Google Drive sharing permissions are controlled by the file owner. A link configured as "Anyone with the link" can be viewed by anyone who obtains it; users must not share sensitive videos publicly.
- Keep the video link scoped to the task's existing group visibility and permissions. Deleting a task or its group removes the link with the task.
- Keep the database migration and backend schema-validation/frontend regression tests with the feature. Do not claim Drive access works until tested with a real file and intended viewer permissions.


## First Admin ownership transfer and activity retention rules — 19 Nov 2026

- Only the current First Admin may start an ownership transfer. Require password re-entry and the recipient's exact email entered twice. Never allow the initiator to name themself or a Student, Tutor, Moderator or suspended account as recipient.
- Keep at most one pending transfer (enforced by the database partial unique index). Expire pending transfers after 24 hours, and re-check the initiator and recipient eligibility at acceptance time.
- The acceptance switch must stay atomic: change `is_first_admin` for both accounts in one transaction, revoke refresh sessions for both, and roll back unless exactly one First Admin exists afterwards. The former First Admin keeps the `admin` role but loses First-Admin-only powers.
- The transfer migration is `20261119120714_first_admin_ownership_transfer.sql`. Keep its filename identical to the production migration ledger. Do not rename it again. Enable RLS and revoke direct table privileges from PUBLIC, anon and authenticated.
- Automatic retention deletes only `auth_attempt_%` rate-limit counters. Never extend automatic or manual purge to login history, incidents, password or session events, or admin audit records without an explicit decision recorded in the Issue.
- The manual purge endpoint is First-Admin-only, requires a reason and `confirm: true`, and must write an audit record containing that reason.
- Do not add a public or mutating API route for security or audit records. The immutability test enforces this.
- Environment variables for these features are `ACTIVITY_RETENTION_DAYS`, `CRON_SECRET`, `FIRST_ADMIN_TRANSFER_MAX_ATTEMPTS` and `FIRST_ADMIN_TRANSFER_WINDOW_SECONDS`. Document them with placeholders only.
