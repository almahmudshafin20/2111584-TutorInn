# Product Requirements Document (PRD)

**Product:** TutorInn  
**Document:** Product Requirements Document  
**Version:** 1.0  
**Status:** Proposed / planning baseline  
**Related issue:** #1  
**Target branch:** `feature/1-tutorinn-docs`

> **Implementation-status note:** This PRD describes the intended TutorInn product. Repository inspection shows that the current codebase is still the FastAPI + React class template: the backend currently exposes `/api/health` and `/api/hello`, and the README describes a class exercise. Therefore, product capabilities described below are requirements/proposed scope, not claims that they are already implemented.

## 1. Product Overview

TutorInn is a secure tutoring platform that helps students discover suitable tutors and request tutoring support. Tutors maintain profiles, subjects, availability, and tutoring requests. Administrators manage users and platform-level controls.

## 2. Problem Statement

Students often need to search through fragmented information to find a tutor whose subject expertise, teaching level, experience, and availability match their needs. Tutors also need a structured way to present their qualifications and manage incoming tutoring requests.

## 3. Product Goals

1. Make tutor discovery fast and structured.
2. Help students evaluate tutors using relevant profile information.
3. Give tutors a simple way to maintain their profiles and availability.
4. Provide a controlled tutoring-request workflow.
5. Protect user data through authentication, authorization, and role-based access control (RBAC).
6. Provide administrators with appropriate user-management capabilities.

## 4. Stakeholders

| Stakeholder | Interest / Responsibility |
|---|---|
| Students | Find tutors, view profiles, and send tutoring requests. |
| Tutors | Publish expertise and availability and manage requests. |
| Administrators | Manage users and platform-level administration. |
| Project team | Design, implement, test, document, and maintain TutorInn. |
| Course/instructor | Evaluate the project against course standards and requirements. |

## 5. User Personas

### 5.1 Student

A learner who needs tutoring and wants to filter tutors by subject, academic level, experience, and availability before making a request.

### 5.2 Tutor

A subject-matter instructor who wants to advertise relevant qualifications, maintain availability, and accept or manage tutoring requests.

### 5.3 Administrator

A trusted platform operator responsible for managing users and enforcing platform-level controls.

## 6. Scope

### 6.1 In Scope

- User authentication and role-aware access.
- Student tutor discovery.
- Tutor filtering by subject, level, experience, and availability.
- Tutor profile viewing.
- Tutor profile and subject management.
- Tutor availability/schedule management.
- Student tutoring requests.
- Tutor request management.
- Administrative user management.
- RBAC and basic security controls.

### 6.2 Out of Scope for the Initial Release

- Integrated video conferencing.
- Integrated payment processing.
- Automated tutor ranking using machine learning.
- Background checks or identity verification services.
- Native mobile applications.
- Advanced recommendation algorithms.

These may be considered in later releases after the core workflow is stable.

## 7. User Stories

- **US-01:** As a student, I want to search for tutors by subject so that I can find relevant tutors.
- **US-02:** As a student, I want to filter tutors by academic level so that I can find an appropriate tutor.
- **US-03:** As a student, I want to filter tutors by experience and availability so that I can find a practical match.
- **US-04:** As a student, I want to view a tutor profile so that I can evaluate the tutor before requesting help.
- **US-05:** As a student, I want to send a tutoring request so that I can ask a tutor for support.
- **US-06:** As a tutor, I want to manage my profile and subjects so that students see accurate information.
- **US-07:** As a tutor, I want to manage my schedule so that students can discover when I am available.
- **US-08:** As a tutor, I want to view and manage tutoring requests so that I can respond to students.
- **US-09:** As an administrator, I want to manage users so that the platform remains controlled and safe.

## 8. Product Requirements

### 8.1 Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| PRD-FR-01 | The system shall support authenticated user accounts with student, tutor, and administrator roles. | Must |
| PRD-FR-02 | Students shall be able to search and filter tutors by subject, level, experience, and availability. | Must |
| PRD-FR-03 | Students shall be able to view tutor profiles. | Must |
| PRD-FR-04 | Students shall be able to submit tutoring requests to tutors. | Must |
| PRD-FR-05 | Tutors shall be able to create and update their profiles and subjects. | Must |
| PRD-FR-06 | Tutors shall be able to manage their availability/schedule. | Must |
| PRD-FR-07 | Tutors shall be able to view and manage incoming tutoring requests. | Must |
| PRD-FR-08 | Administrators shall be able to manage users according to administrative permissions. | Must |
| PRD-FR-09 | The system shall enforce role-based access to protected operations. | Must |
| PRD-FR-10 | The system should provide clear validation and error feedback for invalid requests. | Should |

### 8.2 Non-Functional Product Requirements

| ID | Requirement | Priority |
|---|---|---|
| PRD-NFR-01 | The platform should protect credentials and sensitive user data using appropriate security practices. | Must |
| PRD-NFR-02 | Common tutor searches should return results quickly under normal load. | Should |
| PRD-NFR-03 | The UI should be usable on common desktop and mobile screen sizes. | Should |
| PRD-NFR-04 | Backend APIs should return predictable HTTP status codes and structured errors. | Should |
| PRD-NFR-05 | The system should be maintainable through modular frontend and backend components. | Should |

## 9. MVP Acceptance Criteria

The MVP is considered product-ready for the defined scope when:

1. A student can authenticate, find tutors using the required filters, open a tutor profile, and submit a tutoring request.
2. A tutor can authenticate, maintain profile/subject information, maintain availability, and manage incoming requests.
3. An administrator can perform the approved user-management operations.
4. Users cannot perform operations outside their assigned role.
5. Invalid or unauthorized requests produce clear, safe error responses.
6. Core workflows are covered by automated tests before release.

## 10. Success Metrics

Initial measurable targets for a pilot release:

- **Search success:** at least 90% of valid tutor searches return a usable result set when matching tutors exist.
- **Request completion:** at least 95% of valid tutoring-request submissions are processed without server errors.
- **Authorization:** 100% of protected endpoints enforce the intended role/permission checks in security tests.
- **Availability:** target 99% service availability during the pilot period, excluding planned maintenance.
- **Usability:** at least 80% of pilot users can complete the core search-to-request flow without assistance.

These are proposed product targets and should be validated with real usage data.

## 11. Assumptions

- Users have access to a modern web browser and an internet connection.
- Tutors provide accurate profile, subject, experience, and availability information.
- Authentication is required for protected student, tutor, and administrator operations.
- A backend database will be introduced as part of implementation because the current repository does not yet contain the TutorInn data model.
- The exact authentication provider and production hosting configuration remain implementation decisions.

## 12. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Incorrect or outdated tutor availability | High | Let tutors update schedules and validate request timing. |
| Unauthorized access to another role's data/actions | High | Centralized RBAC and endpoint-level authorization tests. |
| Poor tutor search results | Medium | Use normalized subject/level fields and test representative search cases. |
| Spam or abusive tutoring requests | Medium | Authentication, validation, rate limiting, and future moderation controls. |
| Scope expansion during development | Medium | Treat the MVP requirements above as the baseline and track new work separately. |
| Current template code differs from intended product | High | Keep implementation-status notes in documentation and implement incrementally through tracked issues. |

## 13. Release Priorities

**Release 1 (MVP):** authentication/RBAC, tutor profiles, search/filtering, availability, tutoring requests, tutor request management, and basic administration.

**Release 2:** notifications, richer profile discovery, moderation tools, improved analytics, and usability improvements.

**Future:** payments, video sessions, recommendations, and native mobile clients.

## 14. Traceability

The PRD is the product-level source for the detailed software requirements in `SRS.md` and the technical decisions in `TDD.md`. Requirement IDs use the `PRD-*` prefix here; corresponding SRS requirements use `SRS-*` IDs and explicitly map back to product requirements.
