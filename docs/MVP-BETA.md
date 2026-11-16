# TutorInn MVP and Beta Plan

**Product:** TutorInn  
**Status:** Proposed release plan

## 1. Why MVP and Beta are separated

TutorInn is a three-month project, so the system will be developed in stages. The MVP contains the main tutoring workflow that should be built first. Beta adds the remaining features and improvements after the MVP is working.

The current repository is still the FastAPI + React starter. The features below are planned work, not completed implementation.

## 2. MVP

The MVP focuses on the basic TutorInn workflow from finding a tutor to sending and handling a tutoring request.

| Feature | MVP scope |
|---|---|
| Student account | Basic student authentication and role access |
| Tutor profile | Tutor name, subjects, experience, and basic profile information |
| Tutor search | Search tutors by subject |
| Tutor filtering | Basic level and experience filtering |
| Tutor profile view | Student can open and view a tutor profile |
| Tutoring request | Student can send a request to a selected tutor |
| Tutor requests | Tutor can view received requests |
| Request status | Tutor can accept or decline a request |

### MVP user flow

1. Student logs in.
2. Student searches for a tutor.
3. Student applies basic filters.
4. Student opens a tutor profile.
5. Student sends a tutoring request.
6. Tutor views the request.
7. Tutor accepts or declines the request.

### MVP acceptance

The MVP is successful when the main student-to-tutor request flow works and access is limited to the correct users.

## 3. Beta

Beta builds on the MVP and adds the features needed for a more complete TutorInn system.

| Feature | Beta scope |
|---|---|
| Tutor availability | Tutors can manage detailed schedules and available time slots |
| Advanced filtering | Availability and other useful tutor filters |
| Complete RBAC | More complete Student, Tutor, and Administrator permissions |
| Admin management | Administrators can manage users and account status |
| Validation | More complete input and business-rule validation |
| Security | Stronger authentication, authorization, rate limiting, and secure error handling |
| Testing | Broader backend, frontend, API, and end-to-end testing |
| Deployment | More complete production deployment and monitoring setup |
| Notifications | Request and status notifications |
| Usability | UI improvements based on testing and feedback |

## 4. Later features

These are not part of the initial MVP or Beta baseline and can be considered later if project time allows:

- Online payment
- Video tutoring
- Automated tutor recommendations
- Native mobile application
- Advanced analytics

## 5. Release priority

1. **MVP:** Build and test the core tutor discovery and tutoring-request workflow.
2. **Beta:** Add availability, complete role management, administration, stronger security, testing, deployment, and notifications.
3. **Later:** Consider additional services such as payments, video sessions, and recommendations.

## 6. Relationship with project documents

- `PRD.md` describes what TutorInn should provide.
- `SRS.md` describes the software requirements needed to build it.
- `TDD.md` describes the technical approach.
- This document shows which planned features belong to the MVP and which are planned for Beta or later.

The release plan can be updated as development progresses, while the implementation status of each feature should remain clear in the project documentation.
