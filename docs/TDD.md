# Technical Design Document (TDD)

**Product:** TutorInn  
**Document:** Technical Design Document  
**Version:** 1.0  
**Status:** Proposed target architecture  
**Related issue:** #1  
**Related documents:** `PRD.md`, `SRS.md`

> **Implementation-status note:** This is the target technical design, not a description of completed implementation. The repository currently contains a FastAPI + React/Vite template. `backend/main.py` currently exposes only `/api/health` and `/api/hello`, while the frontend package uses React, React DOM, TypeScript, and Vite. Database, authentication, RBAC, TutorInn domain models, and TutorInn API routes are proposed in this document.

## 1. Technical Objectives

The design should:

1. Separate presentation, API/business logic, and persistence concerns.
2. Enforce authentication and RBAC on the server.
3. Keep TutorInn domain logic testable independently of the UI.
4. Provide stable REST APIs between React and FastAPI.
5. Support incremental implementation from the current template without claiming unimplemented features are complete.
6. Provide a clear path to secure production deployment.

## 2. Verified Repository Baseline

The following facts were verified from the current repository:

- The README identifies the project as a FastAPI + React template with a Vite/React/TypeScript frontend.
- The backend uses FastAPI and currently defines `GET /api/health` and `GET /api/hello`.
- The frontend package currently declares React `^19.3.0`, React DOM `^19.3.0`, TypeScript `^7.0.2`, and Vite `^8.3.2`.
- The repository currently documents a class exercise for sending an ID, name, and email from React to FastAPI.

These are baseline facts only. The architecture below describes the proposed TutorInn system.

## 3. Architecture Overview

TutorInn will use a layered web architecture:

```text
+-----------------------------+
|        Web Browser          |
| React + TypeScript + Vite   |
+--------------+--------------+
               |
             HTTPS
               |
+--------------v--------------+
|        FastAPI API          |
| Routers / Auth / Validation |
+--------------+--------------+
               |
+--------------v--------------+
|      Application Layer      |
| Tutor / Request / User use  |
| cases and business rules    |
+--------------+--------------+
               |
+--------------v--------------+
|       Persistence Layer     |
| ORM / repositories / schema |
+--------------+--------------+
               |
+--------------v--------------+
|     Relational Database     |
+-----------------------------+
```

### 3.1 Request Flow

1. React sends an HTTPS request to a FastAPI endpoint.
2. FastAPI authenticates the request where required.
3. Authorization/RBAC verifies that the current role may perform the operation.
4. The router validates input and delegates to an application service/use case.
5. The service applies business rules and calls persistence/repositories.
6. The repository reads/writes the database.
7. The service returns a domain result.
8. The API serializes the result into the documented JSON response.
9. React updates the UI and displays success/error state.

## 4. Technology Stack

| Layer | Technology | Status |
|---|---|---|
| Frontend | React + TypeScript | Verified current repository; used by target design |
| Frontend tooling | Vite | Verified current repository |
| Backend | FastAPI + Python | Verified current repository |
| API format | REST + JSON | Proposed target |
| Persistence | Relational DB + ORM/repository layer | Proposed |
| Authentication | Secure token/session mechanism | Proposed; provider is open decision |
| Authorization | Application-level RBAC | Proposed |
| Testing | Pytest for backend; frontend test framework to be selected | Proposed |
| Deployment | Vercel-compatible frontend/API deployment or equivalent production hosting | Current README documents Vercel; exact production architecture remains an open decision |

## 5. Component Design

### 5.1 Frontend Components

Proposed feature-oriented structure:

```text
frontend/src/
  app/
    router/
    providers/
  features/
    auth/
    tutors/
    requests/
    profile/
    availability/
    admin/
  components/
    ui/
    forms/
  services/
    api.ts
  types/
```

Responsibilities:

- **auth:** login/session state and protected navigation.
- **tutors:** tutor search, filters, cards, and profile views.
- **requests:** request creation and request status views.
- **profile:** tutor profile and subject editing.
- **availability:** tutor schedule management.
- **admin:** administrative user-management UI.
- **services/api:** centralized HTTP client and API error handling.

### 5.2 Backend Components

Proposed structure:

```text
backend/app/
  main.py
  api/
    routes/
      auth.py
      tutors.py
      requests.py
      admin.py
  core/
    config.py
    security.py
    errors.py
  models/
  schemas/
  services/
    auth_service.py
    tutor_service.py
    request_service.py
    admin_service.py
  repositories/
  db/
    session.py
```

Responsibilities:

- **routes:** HTTP transport, request/response schemas, dependency wiring.
- **services:** business rules and use cases.
- **repositories:** database access and persistence abstraction.
- **models:** persistence entities.
- **schemas:** API input/output validation.
- **core/security:** authentication, password/token handling, RBAC dependencies.
- **core/errors:** consistent application exceptions and HTTP mapping.

## 6. API Design

### 6.1 Conventions

- Base path: `/api`.
- JSON request and response bodies.
- HTTP methods follow REST semantics.
- Resource IDs are opaque to clients where practical.
- Authentication is carried using a secure mechanism selected during implementation.
- Protected routes require authentication and role checks.
- Validation errors use a consistent structure.

### 6.2 Target Endpoints

| Method | Endpoint | Purpose | Role |
|---|---|---|---|
| POST | `/api/auth/login` | Authenticate | Public |
| GET | `/api/tutors` | Search/filter tutors | Student |
| GET | `/api/tutors/{id}` | Read tutor profile | Authenticated |
| PUT | `/api/tutors/me` | Update own tutor profile | Tutor |
| PUT | `/api/tutors/me/subjects` | Manage subjects | Tutor |
| PUT | `/api/tutors/me/availability` | Manage availability | Tutor |
| POST | `/api/requests` | Create tutoring request | Student |
| GET | `/api/requests` | List permitted requests | Student/Tutor |
| PATCH | `/api/requests/{id}` | Update request state | Authorized user |
| GET | `/api/admin/users` | List users | Administrator |
| PATCH | `/api/admin/users/{id}` | Manage user state | Administrator |

These endpoints are proposed and must be implemented according to the SRS before being considered operational.

### 6.3 Request/Response Example

Create request:

```json
POST /api/requests
{
  "tutor_id": 42,
  "subject_id": 7,
  "requested_start": "2026-11-01T14:00:00Z",
  "message": "I need help preparing for the midterm."
}
```

Target response:

```json
{
  "id": 1001,
  "tutor_id": 42,
  "subject_id": 7,
  "status": "pending",
  "message": "I need help preparing for the midterm."
}
```

## 7. Data Model

### 7.1 Logical Relationships

```text
User 1 -------- 0..1 TutorProfile
User (Student) 1 -------- * TutoringRequest * -------- 1 User (Tutor)
TutorProfile 1 -------- * Availability
TutorProfile * -------- * Subject
TutoringRequest * -------- 1 Subject
User 1 -------- * AuditEvent
```

### 7.2 Proposed Tables

**users**
- `id` PK
- `name`
- `email` UNIQUE
- `password_hash` or external auth reference
- `role`
- `status`
- `created_at`
- `updated_at`

**tutor_profiles**
- `user_id` PK/FK → users.id
- `bio`
- `experience_years`
- `qualification`
- `created_at`
- `updated_at`

**subjects**
- `id` PK
- `name`
- `level`

**tutor_subjects**
- `tutor_id` FK
- `subject_id` FK
- composite uniqueness constraint on `(tutor_id, subject_id)`

**availability**
- `id` PK
- `tutor_id` FK
- `start_at`
- `end_at`
- `status`

**tutoring_requests**
- `id` PK
- `student_id` FK → users.id
- `tutor_id` FK → users.id
- `subject_id` FK → subjects.id
- `message`
- `requested_start`
- `status`
- `created_at`
- `updated_at`

**audit_events**
- `id` PK
- `actor_id` FK
- `action`
- `target_type`
- `target_id`
- `metadata`
- `created_at`

## 8. Business Rules

1. Only authenticated students can create tutoring requests.
2. A tutor can modify only their own tutor profile, subjects, and availability through normal tutor operations.
3. A student can view only requests they created; a tutor can view only requests addressed to them.
4. Request state transitions must be explicitly defined, for example `pending → accepted`, `pending → declined`, and `accepted → cancelled` where business policy permits.
5. A request must reference a valid tutor and subject.
6. Availability cannot contain an invalid interval where the end precedes the start.
7. Administrators can manage users only through explicit administrative endpoints.
8. Backend authorization is authoritative; frontend role checks are only a usability layer.

## 9. Authentication and RBAC Design

### 9.1 Authentication

The authentication implementation should use a well-maintained mechanism rather than custom cryptography. If passwords are application-managed, they must be hashed with a modern password-hashing algorithm. If an external identity provider is selected, the backend must validate the provider's signed identity/token according to its documented protocol.

### 9.2 Authorization

Use reusable FastAPI dependencies/middleware to obtain the current user and enforce required roles. For example, a tutor-only route should verify both authentication and `role == tutor` before entering the service layer.

Object-level authorization must also be enforced. A tutor role alone does not grant access to another tutor's profile or requests.

## 10. Security Design

- HTTPS for production traffic.
- Secure cookies or short-lived access tokens with an appropriate refresh strategy, depending on the final authentication decision.
- Password hashing rather than plaintext storage.
- Server-side authorization on every protected endpoint.
- Input validation using typed request schemas.
- Parameterized/ORM database queries.
- CORS restricted to trusted frontend origins in production.
- Security headers where supported by the deployment stack.
- Rate limiting for login and abuse-sensitive operations.
- Secrets stored in environment/secret-management systems, never in Git.
- Sensitive information excluded from logs.
- Audit events for important administrative/account-state changes.

## 11. Error Handling

The backend should map expected application errors to stable HTTP responses:

| Condition | HTTP status | Example code |
|---|---:|---|
| Invalid input | 400 / 422 | `VALIDATION_ERROR` |
| Missing/invalid authentication | 401 | `UNAUTHENTICATED` |
| Insufficient role/permission | 403 | `FORBIDDEN` |
| Resource does not exist | 404 | `NOT_FOUND` |
| Business-rule conflict | 409 | `CONFLICT` |
| Unexpected server failure | 500 | `INTERNAL_ERROR` |

Unexpected errors should be logged server-side with correlation/request information but should return a safe generic message to clients.

## 12. Deployment Design

### 12.1 Development

- Run FastAPI locally for the backend.
- Run Vite development server for the frontend.
- Use environment variables for API URLs and secrets.
- Use a development database separate from production data.

### 12.2 Production

The current repository README documents a Vercel deployment model where `/api/*` routes to the backend and other paths serve the frontend. The final TutorInn deployment should preserve this or move to an equivalent architecture after verifying FastAPI runtime, database connectivity, secret management, logging, and scaling requirements.

Minimum production controls:

- HTTPS.
- Production database with backups.
- Environment-based secrets.
- Restricted CORS.
- Monitoring/logging.
- Health endpoint.
- Automated deployment from the protected main branch after checks pass.

## 13. Testing Strategy

### 13.1 Unit Tests

Test services and business rules independently:

- Tutor filtering logic.
- Availability validation.
- Request status transitions.
- RBAC policy decisions.
- Input validation.

### 13.2 API/Integration Tests

Use a test database and FastAPI test client to verify:

- Authentication.
- Tutor search/filtering.
- Profile and availability CRUD.
- Request creation and status transitions.
- Object-level authorization.
- Administrator-only endpoints.
- Error response contracts.

### 13.3 Frontend Tests

Test:

- Search/filter interactions.
- Protected route behavior.
- Forms and validation.
- Request submission states.
- Tutor and administrator workflows.

### 13.4 End-to-End Tests

At minimum, automate:

1. Student login → tutor search → profile → request.
2. Tutor login → profile/availability → request management.
3. Administrator login → user management.
4. Unauthorized role attempts against protected operations.

### 13.5 Quality Gates

A pull request implementing TutorInn features should pass formatting/linting, type checking, unit tests, API tests, and relevant frontend/end-to-end tests before merge.

## 14. Observability and Operations

- `/api/health` should remain a lightweight health check and may be expanded to include dependency health in production.
- Application logs should include timestamp, severity, request/correlation ID, route, status, and duration without sensitive data.
- Monitor API error rate, latency, authentication failures, and database availability.
- Alert on sustained 5xx errors and database/connectivity failures.

## 15. Repository and Development Workflow

For feature work:

1. Create a GitHub Issue describing the change.
2. Create a feature branch named using the issue number, e.g. `feature/<issue-number>-<short-description>`.
3. Make focused commits with descriptive conventional-style messages.
4. Run relevant tests/checks.
5. Open a PR against `main` and reference the issue using `Closes #<issue-number>`.
6. Review the PR before merge.

For this documentation task, the branch is `feature/1-tutorinn-docs` and the PR must contain `Closes #1`.

## 16. Open Technical Decisions

| Decision | Current proposal | Final decision needed |
|---|---|---|
| Database engine | Relational database | Select PostgreSQL or course-approved alternative. |
| ORM/data access | Repository/ORM layer | Select SQLAlchemy or another approved ORM. |
| Authentication | Secure application auth or external provider | Choose based on course scope and deployment. |
| Token/session strategy | Secure cookie/session or access/refresh tokens | Finalize with frontend architecture. |
| Frontend test framework | Not yet selected | Choose course/project standard. |
| Production hosting | Vercel-compatible or equivalent | Verify FastAPI + DB runtime requirements. |
| Notifications | Future/optional | Define after MVP request workflow. |

## 17. Traceability

The TDD implements the design needed to satisfy the SRS and PRD:

- **PRD:** defines product goals, scope, users, and success criteria.
- **SRS:** defines testable functional/non-functional requirements and interfaces.
- **TDD:** defines the proposed architecture, components, data model, security, deployment, testing, and operational approach.

Any technical decision that changes a Must-level SRS requirement should update the affected design sections and be reviewed through the project's issue/PR workflow.
