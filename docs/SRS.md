# Software Requirements Specification (SRS)

**Product:** TutorInn  
**Document:** Software Requirements Specification  
**Version:** 1.0  
**Status:** Proposed / planning baseline  
**Related issue:** #1  
**Related documents:** `PRD.md`, `TDD.md`

> **Implementation-status note:** This SRS specifies the intended TutorInn system. The current repository is still a FastAPI + React template. The verified backend currently exposes `GET /api/health` and `GET /api/hello`; TutorInn authentication, database entities, tutor search, requests, and RBAC are not yet evidenced in the current code. Requirements below therefore describe the target system rather than completed implementation.

## 1. Introduction

### 1.1 Purpose

This document defines the functional and non-functional requirements for TutorInn. It provides a testable baseline for implementation and acceptance and acts as the bridge between product requirements and technical design.

### 1.2 Scope

TutorInn will provide a web platform for students to discover tutors and submit tutoring requests, tutors to manage profiles, subjects, availability, and requests, and administrators to manage users. The system will use authenticated access and RBAC for protected operations.

### 1.3 Definitions and Acronyms

| Term | Meaning |
|---|---|
| RBAC | Role-Based Access Control. |
| Student | User who searches for tutors and submits tutoring requests. |
| Tutor | User who provides tutoring and manages tutoring information. |
| Administrator | User with platform-level user-management permissions. |
| Request | A student's request for tutoring support from a selected tutor. |
| API | Application Programming Interface. |
| MVP | Minimum Viable Product. |

## 2. Overall Description

### 2.1 Product Perspective

TutorInn is planned as a browser-based client/server application. The frontend will provide user interfaces and communicate with a FastAPI backend over HTTP. A persistent relational database is planned for user, tutor, availability, and request data.

The repository currently contains React/Vite/TypeScript frontend tooling and a FastAPI backend template. These technologies are verified repository facts; the TutorInn architecture and data model in this SRS are proposed target design.

### 2.2 User Classes

1. **Student:** may search/view tutors and create/manage their own tutoring requests.
2. **Tutor:** may manage their own tutor profile, subjects, availability, and incoming requests.
3. **Administrator:** may perform approved user-management operations and platform administration.

### 2.3 Operating Environment

- Modern web browser for end users.
- React + TypeScript frontend.
- FastAPI backend running on Python.
- Relational database for persistent TutorInn data (proposed).
- HTTPS in production (required for deployment).

### 2.4 Constraints

- The solution must maintain clear separation between frontend, backend, and persistence responsibilities.
- Protected API operations must enforce authentication and authorization server-side.
- User passwords, tokens, and other secrets must not be exposed in client-side logs or source code.
- API contracts should use stable resource names and structured JSON responses.

### 2.5 Assumptions and Dependencies

- Users have internet access and a supported browser.
- Authentication infrastructure will be selected during implementation.
- A database will be added before persistent TutorInn workflows are implemented.
- Email, payment, video, and external identity services are not required for the MVP.

## 3. Use Cases

The following use cases describe the main interactions between TutorInn users and the planned system. They are part of the target design and are not claims that these workflows are already implemented.

| ID | Actor | Use Case | Release |
|---|---|---|---|
| UC-01 | Student | Log in and access the student area. | MVP |
| UC-02 | Student | Search and filter tutors by subject, level, experience, or availability. | MVP |
| UC-03 | Student | View a tutor profile. | MVP |
| UC-04 | Student | Send a tutoring request to a tutor. | MVP |
| UC-05 | Tutor | Manage tutor profile and subjects. | MVP |
| UC-06 | Tutor | Manage availability and view incoming requests. | Beta |
| UC-07 | Tutor | Accept or decline a tutoring request. | MVP |
| UC-08 | Administrator | Manage users and account status. | Beta |

### 3.1 Student Searches for a Tutor

1. The student logs in.
2. The student enters a subject or selects filters.
3. The system validates the search criteria.
4. The system returns matching tutor profiles.
5. The student selects a tutor to view the profile.

Result: The student can identify a suitable tutor from the available results.

### 3.2 Student Sends a Tutoring Request

1. The student opens a tutor profile.
2. The student enters the required request information.
3. The system validates the request.
4. The system creates the request with an initial status such as `pending`.
5. The tutor can see the request in their request list.

Result: A valid tutoring request is recorded for the selected tutor.

### 3.3 Tutor Manages a Request

1. The tutor logs in.
2. The tutor opens incoming tutoring requests.
3. The tutor selects a request.
4. The tutor accepts or declines the request if the status transition is allowed.
5. The system saves the new status.

Result: The request status reflects the tutor's response.

### 3.4 Administrator Manages Users

1. The administrator logs in.
2. The administrator opens the user-management area.
3. The system checks the administrator role.
4. The administrator performs an approved user-management action.
5. The system records the updated account state and audit information where required.

Result: User management is performed only by an authorized administrator.

## 4. System Features and Functional Requirements

### 4.1 Authentication and Accounts

| ID | Requirement | Priority |
|---|---|---|
| SRS-FR-001 | The system shall allow a user to authenticate using valid credentials. | Must |
| SRS-FR-002 | The system shall associate each authenticated user with exactly one primary application role: Student, Tutor, or Administrator. | Must |
| SRS-FR-003 | The system shall reject invalid credentials without revealing whether a specific account exists. | Must |
| SRS-FR-004 | The system shall protect authenticated sessions/tokens against unauthorized use. | Must |

### 4.2 Tutor Discovery

| ID | Requirement | Priority |
|---|---|---|
| SRS-FR-010 | A student shall be able to search tutors using subject criteria. | Must |
| SRS-FR-011 | A student shall be able to filter tutors by academic level. | Must |
| SRS-FR-012 | A student shall be able to filter tutors by experience. | Must |
| SRS-FR-013 | A student shall be able to filter tutors by availability. | Must |
| SRS-FR-014 | The system shall return tutor results matching the supplied valid filters. | Must |
| SRS-FR-015 | The system shall allow a student to open a tutor's public profile details permitted for discovery. | Must |

### 4.3 Tutor Profile and Subjects

| ID | Requirement | Priority |
|---|---|---|
| SRS-FR-020 | A tutor shall be able to create and update their permitted profile fields. | Must |
| SRS-FR-021 | A tutor shall be able to add, update, and remove their tutoring subjects. | Must |
| SRS-FR-022 | The system shall prevent one tutor from modifying another tutor's profile through normal tutor operations. | Must |
| SRS-FR-023 | The system shall validate required profile and subject fields before saving. | Must |

### 4.4 Availability and Scheduling

| ID | Requirement | Priority |
|---|---|---|
| SRS-FR-030 | A tutor shall be able to create and update availability entries. | Must |
| SRS-FR-031 | The system shall validate that availability entries contain valid date/time information. | Must |
| SRS-FR-032 | Availability data exposed to students shall represent the tutor's currently published availability. | Must |

### 4.5 Tutoring Requests

| ID | Requirement | Priority |
|---|---|---|
| SRS-FR-040 | An authenticated student shall be able to create a tutoring request for a selected tutor. | Must |
| SRS-FR-041 | A request shall contain the information required to identify the student, tutor, requested subject, and request status. | Must |
| SRS-FR-042 | The system shall assign a controlled initial status to a newly created request. | Must |
| SRS-FR-043 | A tutor shall be able to view requests addressed to that tutor. | Must |
| SRS-FR-044 | A tutor shall be able to update a request using only allowed status transitions. | Must |
| SRS-FR-045 | A student shall be able to view their own submitted requests. | Must |
| SRS-FR-046 | Users shall not be able to read or modify requests belonging to unrelated users. | Must |

### 4.6 Administration

| ID | Requirement | Priority |
|---|---|---|
| SRS-FR-050 | An administrator shall be able to list users according to permitted administrative access. | Must |
| SRS-FR-051 | An administrator shall be able to perform approved user-management actions. | Must |
| SRS-FR-052 | Non-administrators shall not be able to access administrator-only user-management operations. | Must |
| SRS-FR-053 | Administrative actions affecting account state should be auditable. | Should |

### 4.7 Validation and Errors

| ID | Requirement | Priority |
|---|---|---|
| SRS-FR-060 | The API shall validate request payloads before processing them. | Must |
| SRS-FR-061 | The API shall return appropriate HTTP status codes for success, validation failure, authentication failure, authorization failure, missing resources, and server errors. | Must |
| SRS-FR-062 | Error responses shall not expose passwords, secrets, stack traces, or unnecessary internal details. | Must |

## 5. Non-Functional Requirements

| ID | Requirement | Target / Verification |
|---|---|---|
| SRS-NFR-001 | Security | Protected operations require authentication and server-side RBAC checks. Verify with positive and negative authorization tests. |
| SRS-NFR-002 | Confidentiality | Passwords and authentication secrets are never stored or logged in plaintext. Verify through configuration/code review and tests. |
| SRS-NFR-003 | Performance | Typical tutor search requests should complete within 2 seconds at the MVP target load. Verify using API performance tests. |
| SRS-NFR-004 | Availability | Pilot deployment should target 99% service availability excluding planned maintenance. Verify using deployment monitoring. |
| SRS-NFR-005 | Usability | Core student and tutor workflows should be understandable without technical knowledge. Verify with usability testing. |
| SRS-NFR-006 | Compatibility | The web UI should support current mainstream browsers. Verify with browser smoke tests. |
| SRS-NFR-007 | Maintainability | Frontend, API, authorization, and persistence concerns should remain modular. Verify through code review and architecture tests where practical. |
| SRS-NFR-008 | Observability | Production failures should generate useful server-side logs without sensitive user data. Verify through logging review. |

## 6. External Interface Requirements

### 6.1 User Interface

The frontend shall provide:

- Authentication screens.
- Student tutor-search/filter interface.
- Tutor profile view.
- Student request creation and request list views.
- Tutor profile, subject, availability, and request-management views.
- Administrator user-management view.
- Clear loading, validation, success, empty-state, and error messages.

### 6.2 API Interface

The backend shall expose a versionable JSON REST API. The following endpoints are target interfaces; they are **proposed** and are not currently implemented in the repository except for the existing template endpoints noted below.

| Method | Target endpoint | Purpose | Access |
|---|---|---|---|
| POST | `/api/auth/login` | Authenticate a user. | Public |
| GET | `/api/tutors` | Search/filter tutors. | Authenticated student |
| GET | `/api/tutors/{id}` | View tutor profile. | Authenticated student / permitted users |
| PUT | `/api/tutors/me` | Update current tutor profile. | Tutor |
| PUT | `/api/tutors/me/subjects` | Manage current tutor subjects. | Tutor |
| PUT | `/api/tutors/me/availability` | Manage current tutor availability. | Tutor |
| POST | `/api/requests` | Create tutoring request. | Student |
| GET | `/api/requests` | List requests visible to current user. | Student/Tutor |
| PATCH | `/api/requests/{id}` | Update allowed request status. | Authorized Tutor / Student operations as defined |
| GET | `/api/admin/users` | List users. | Administrator |
| PATCH | `/api/admin/users/{id}` | Perform approved user-management action. | Administrator |

**Verified current template endpoints:** `GET /api/health` and `GET /api/hello` exist in the current backend and are not TutorInn domain APIs.

### 6.3 Error Response Format

The target API should return a consistent structure similar to:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid fields.",
    "details": {}
  }
}
```

The exact schema may be finalized during implementation but should remain consistent across API resources.

## 7. Data Requirements

The proposed minimum logical entities are:

| Entity | Key information |
|---|---|
| User | id, name, email, password/auth reference, role, status, timestamps |
| TutorProfile | user_id, bio, experience, education/qualification fields, timestamps |
| Subject | id, name, level/category metadata |
| TutorSubject | tutor_id, subject_id, proficiency/metadata |
| Availability | id, tutor_id, day/date, start_time, end_time, status |
| TutoringRequest | id, student_id, tutor_id, subject_id, message, status, requested time, timestamps |
| AuditEvent | id, actor_id, action, target, timestamp, metadata |

Data integrity rules include:

1. User email must be unique.
2. TutorProfile must reference an existing Tutor-role user.
3. TutorSubject must reference existing tutor and subject records.
4. TutoringRequest must reference an existing student, tutor, and valid subject.
5. Request status changes must follow defined business rules.
6. Deleting users must preserve required referential integrity and audit information.

## 8. RBAC Requirements

| Operation | Student | Tutor | Administrator |
|---|:---:|:---:|:---:|
| Search tutors | ✓ | ✓* | ✓* |
| View permitted tutor profile | ✓ | ✓ | ✓ |
| Edit own tutor profile | — | ✓ | ✓** |
| Manage own subjects | — | ✓ | ✓** |
| Manage own availability | — | ✓ | ✓** |
| Create tutoring request | ✓ | — | — |
| View own requests | ✓ | ✓ | ✓** |
| Manage received tutor requests | — | ✓ | ✓** |
| Manage users | — | — | ✓ |

`*` Read/search access may be enabled for other roles if product policy permits.  
`**` Administrative access should be explicit and auditable rather than silently bypassing normal business rules.

RBAC must be enforced by the backend; hiding a UI control is not sufficient authorization.

## 9. Security Requirements

- Use HTTPS in production.
- Store passwords using a strong password-hashing algorithm if passwords are managed by the application.
- Never return password hashes or authentication secrets through API responses.
- Validate and authorize every protected request server-side.
- Use secure session/token handling and appropriate expiration/revocation mechanisms.
- Apply input validation and parameterized database access to reduce injection risk.
- Add rate limiting to authentication and abuse-sensitive endpoints where appropriate.
- Avoid exposing sensitive data in logs and error messages.

## 10. Acceptance Criteria

The following acceptance tests trace the major requirements to observable behavior:

| Acceptance ID | Scenario | Expected result |
|---|---|---|
| SRS-AC-01 | Student searches by subject and level. | Matching tutors are returned. |
| SRS-AC-02 | Student filters by availability. | Only tutors satisfying the requested availability criteria are returned. |
| SRS-AC-03 | Student opens a tutor profile. | Permitted tutor information is displayed. |
| SRS-AC-04 | Student submits a valid request. | Request is stored with the correct student, tutor, subject, and initial status. |
| SRS-AC-05 | Tutor views incoming requests. | Only requests addressed to that tutor are shown. |
| SRS-AC-06 | Tutor changes a request status using an allowed transition. | Status is updated successfully. |
| SRS-AC-07 | Student attempts an administrator-only operation. | API returns `403 Forbidden`. |
| SRS-AC-08 | Unauthenticated user calls a protected endpoint. | API returns `401 Unauthorized`. |
| SRS-AC-09 | User attempts to access another user's private request. | Access is denied. |
| SRS-AC-10 | Invalid request data is submitted. | API returns validation error without creating invalid data. |

## 11. Traceability Matrix

| PRD requirement | SRS coverage |
|---|---|
| PRD-FR-01 | SRS-FR-001 to SRS-FR-004, RBAC section |
| PRD-FR-02 | SRS-FR-010 to SRS-FR-014 |
| PRD-FR-03 | SRS-FR-015 |
| PRD-FR-04 | SRS-FR-040 to SRS-FR-046 |
| PRD-FR-05 | SRS-FR-020 to SRS-FR-023 |
| PRD-FR-06 | SRS-FR-030 to SRS-FR-032 |
| PRD-FR-07 | SRS-FR-043 to SRS-FR-044 |
| PRD-FR-08 | SRS-FR-050 to SRS-FR-053 |
| PRD-FR-09 | RBAC requirements and SRS-NFR-001 |
| PRD-NFR-01 to PRD-NFR-05 | SRS-NFR-001 to SRS-NFR-008 |

## 12. Requirement Change Policy

Changes to a Must requirement should be reviewed against product scope, security impact, data impact, and implementation cost. New requirements should receive a unique `SRS-*` identifier and be traced back to a product requirement or an approved change request.
