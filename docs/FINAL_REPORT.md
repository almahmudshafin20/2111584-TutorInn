<div align="center">

<img src="../images/iub-logo.png" alt="Independent University, Bangladesh logo" width="200">

# Independent University, Bangladesh
## CSE309 Web Application & Internet

**Final Project Submission Report**

Submitted by:<br>
**Name:** Al Mahmud Shafin<br>
**Student ID:** 2111584<br>
**Section:** 06<br>
**Team Number:** Not assigned

<br>

**Project Title:** TutorInn: Secure Tutor–Student Matching and Learning Platform<br>
**Vercel URL:** https://2111584-tutorinn.vercel.app<br>
**GitHub Repository:** https://github.com/almahmudshafin20/2111584-TutorInn

<br>

**Submitted To:**<br>
**Sayef Reyadh**<br>
Adjunct Lecturer<br>
Department of Computer Science & Engineering<br>
Independent University, Bangladesh

<br>

Semester: Autumn 2026

Date of Submission: 28 November 2026

</div>

---

## Table of Contents

1. Executive Summary
2. Part A. Product Requirements (PRD) — A1 to A5
3. Part B. Software Requirements (SRS) — B1 to B7
4. Part C. Technical Design (TDD) — C1 to C11
5. Part D. Evidence: Screenshots of the Running Application — D1 to D5
6. Part E. Project Management and Conclusion — E1 to E5
7. Appendix. Test Accounts and Video Demo (PDF only)

### List of Figures and Screenshots

| No. | Caption | Section |
|---|---|---|
| Figure 1 | Use case diagram | B5 |
| Figure 2 | System architecture | C2 |
| Figure 3 | ER diagram | C4 |
| Figure 4 | JWT sequence: login, request, expiry, refresh, reuse, logout | C6 |
| Figure 5 | Authorisation flow for one request | C7 |
| Figure 6 | Admin pages and the endpoints they call | C8 |
| Figure 7 | Deployment layout on Vercel | C10 |
| S1–S6 | User side | D1 |
| S7–S9 | Security behaviour | D2 |
| S10–S17 | Admin dashboard | D3 |
| S18–S20 | Deployment | D4 |
| S21 | Automated test output | D5 |

> In the PDF version, replace this table with the word processor's automatic table of contents and list of figures (with page numbers).

---

## 1. Executive Summary

### 1.1 Project overview

TutorInn is a web platform that connects students who need tutoring with tutors who can provide it, and then supports the learning that follows. Students post tutoring requests, browse and filter tutors, and accept one interested tutor. Tutors respond to requests, run learning groups, share tasks (optionally with a Google Drive video link) and assign them to group members. Both roles keep a private list of personal learning tasks. Administrators manage accounts, verify tutors, moderate content, investigate security events and export data. Every protected action is checked on the server: the browser never decides who a user is or what they may do.

**Stack:** React 19 + TypeScript (built with Rspack) · FastAPI (Python) · SQLAlchemy 2 + Alembic · PostgreSQL on Supabase (SQLite for local runs) · PyJWT + Argon2id · one Vercel project serving the frontend and the API.

### 1.2 What was built since the mid assessment

- **JWT authentication with refresh and logout:** 15-minute signed access tokens, opaque 7-day refresh tokens in an httpOnly cookie, rotation on every refresh, reuse detection that revokes the whole session family, CSRF protection and server-side logout.
- **Session management:** users see their active devices and can revoke one session, all other sessions, or all sessions.
- **Role-based access control:** Student, Tutor, Admin (with a protected First Admin) and a Moderator capability set, enforced by one reusable dependency; ownership filters on every private record; per-member group permissions (create, edit, assign).
- **Personal learning tasks and learning groups:** task CRUD with categories, due dates, filters and summaries; tutor-owned groups with members, shared tasks, assignments and Drive video links.
- **Admin dashboard:** overview statistics, user list and detail, ban/suspend/unban with reasons, admin role grant/revoke, session revoke, bulk actions, tutor verification, content moderation, reports, subjects, activity log, security view, CSV exports, account-deletion review, password-reset queue and First Admin transfer.
- **Audit logging and brute-force protection:** every security event and admin action is written to an append-only log with secrets redacted; per-account login lockout and per-IP rate limits.
- **Deployment on Vercel:** one project with a FastAPI service and a static frontend service, a hosted Supabase PostgreSQL database and a daily retention cron job.

All of this work is merged into `main` through the milestone pull requests #42–#45, the Beta roadmap (Issue #41) is complete and closed, and the production site is deployed from `main`.

### 1.3 Live links

**Table 1: Links**

| Item | Link |
|---|---|
| GitHub repository | https://github.com/almahmudshafin20/2111584-TutorInn |
| Vercel frontend | https://2111584-tutorinn.vercel.app |
| API base | https://2111584-tutorinn.vercel.app/api |
| API documentation (Swagger UI) | https://2111584-tutorinn.vercel.app/api/docs |
| Video demo | https://youtu.be/EtYkuMW_a5Y |

Test account user IDs and passwords are given only in the Appendix of the PDF report.

---

## Part A. Product Requirements (PRD)

### A1. Problem Statement

Students who want a tutor usually depend on word of mouth, social-media groups and notice boards. The information they find is scattered and unstructured: it is hard to compare tutors by subject, level, experience and availability, and there is no record of who asked whom for what. Tutors face the reverse problem. They advertise in many places, receive requests through private messages, and have no single place to organise the students they teach or to hand out and track work.

Once tutoring starts, the coordination is just as informal. Tasks and video lessons are shared through chat threads, nobody can see clearly which student has finished which assignment, and personal study plans live in separate notes apps. Because all of this happens on general-purpose platforms, there is also no moderation: abusive posts, fake tutor profiles and compromised accounts cannot be handled by anyone responsible for the community. This matters because poor matching wastes students' money and time, and because a tutoring community involves young people's contact details and learning records, which deserve proper protection.

### A2. Users and Roles

**Table 2: Users and roles**

| Role | Who they are | Main tasks | Must never be able to |
|---|---|---|---|
| Visitor | Anyone not signed in | Read the home and about pages; browse the read-only tutor directory; register; sign in; request a password reset | Read any private profile, request, task or group; call a protected endpoint |
| Student | A learner with a Student account | Post and manage own tutoring requests; review tutor responses and accept one; manage personal tasks; view groups they belong to; complete their own assignments; report content; request account deletion | Read another student's requests, tasks or contact details; edit a group; change another member's completion; act as a tutor or admin |
| Tutor | A teacher with a Tutor account | Maintain own profile, subjects and availability; respond to students' requests; create learning groups; add and remove members; set member permissions; create, edit, assign and delete group tasks; manage personal tasks | Edit another tutor's profile or group; see private details of students outside their groups; approve their own verification; use admin functions |
| Group member | A Student added to a tutor's group | View the group and the tasks assigned to them; if the owner allows it, create, edit or assign group tasks; mark their own assignments complete | Rename the group, add or remove members, change permissions or delete tasks (owner-only); see other members' email addresses or assignment progress |
| Group owner | The Tutor who created the group | All group actions, including owner-only ones | Act on groups owned by other tutors |
| Admin | A trusted platform operator | Dashboard, user management, moderation, verification, activity and security investigation, exports, deletion and password-reset review | Ban, suspend or demote another admin; change or ban their own account; grant admin access (unless First Admin); edit content inside a group through the group endpoints |
| First Admin | The single designated Admin (`is_first_admin`) | Everything an Admin can do, plus granting admin access, manual activity cleanup and transferring the First Admin role | Be banned, suspended, demoted or deleted by anyone |
| Moderator | A capability set defined in the permission matrix | Review tutoring requests, tasks and groups; delete learning content; review password-reset requests | Manage accounts or roles, view activity/security, export data or run cleanup |

> Note: the Moderator capabilities are enforced and tested, but this release has no screen for assigning the Moderator role (see E3).

### A3. Goals and Success Measures

**Table 3: Goals and measures**

| ID | Goal | Measure (testable) |
|---|---|---|
| G-01 | Students can find a suitable tutor quickly | Tutor discovery returns only tutors matching every supplied filter (subject, level, minimum experience, availability); yes/no check in `test_student_dashboard_and_tutor_discovery_filters` |
| G-02 | A tutoring request can go from posting to an accepted tutor | A student can create a request, a tutor can respond "Interested", and the student can accept exactly one response; the request becomes `Accepted` and other interested responses become `Rejected` |
| G-03 (security) | No user can read or change another user's data | 100% of ownership tests pass: requests, personal tasks, profiles, sessions and group assignments of another account return 404 or 403 |
| G-04 (security) | Sessions are short-lived and revocable | Access tokens expire after at most 15 minutes (configurable 1–60); a revoked, banned or logged-out session is rejected on the very next request; a reused refresh token revokes the whole session family |
| G-05 (security) | Brute-force login attempts are stopped | After 5 failed attempts for one email within 15 minutes, login returns 429 even with the correct password |
| G-06 | Admins can investigate and act with a full audit trail | Every admin action (ban, role change, delete, export, session revoke) creates an activity record with actor, target and reason; checked in `test_admin_ban_role_change_delete_and_export_record_actor_affected_account_and_context` |

### A4. Scope and Non-Goals

**In scope**

- Registration, login, refresh, logout and session management for Student and Tutor accounts; Admin accounts provisioned from the command line.
- Role-based access control, ownership rules and per-member group permissions.
- Tutoring requests, tutor responses and acceptance; tutor discovery with filters; tutor verification.
- Personal learning tasks; learning groups, shared tasks, assignments and Google Drive video links.
- Admin dashboard: overview, users, tutors, requests, tasks, groups, activity, security, reports, subjects, exports, account-deletion review, password-reset review and First Admin transfer.
- Audit logging, rate limiting, login lockout, security headers and deployment on Vercel with Supabase PostgreSQL.

**Out of scope (and why)**

- Payments and invoicing — would require a paid payment provider; the project rule is not to depend on paid services.
- Built-in video calls or video hosting — videos stay in the user's Google Drive and are shown only as links, which avoids storage costs and copyright risk.
- Real-time chat between students and tutors — not needed for the request/response workflow and would add moderation load.
- Native mobile apps — the web interface is responsive instead.
- Automatic identity or background checks of tutors — replaced by manual admin verification.

**Assumptions and constraints**

- Users have a current version of Chrome, Edge, Firefox or Safari with cookies and JavaScript enabled.
- Hosting uses Vercel's free tier: the API runs as serverless functions, so there is no persistent local disk (SQLite is refused on Vercel) and only one cron job per day.
- The database is a Supabase PostgreSQL project; the browser never talks to it directly.
- Email delivery depends on SMTP settings that are not configured in production, so email-based steps currently need manual admin follow-up.
- The project was built by one student within one semester.

### A5. User Stories

**Table 4: User stories**

| ID | Role | Story |
|---|---|---|
| US-01 | Visitor | As a visitor I want to create a Student or Tutor account so that I can use the platform. |
| US-02 | Student / Tutor | As a user I want to stay signed in safely across page reloads so that I do not have to log in on every visit, but my session still ends if it is stolen and revoked. |
| US-03 | Student / Tutor | As a user I want to see and revoke my active sessions so that I can sign out a lost device. |
| US-04 | Student | As a student I want to filter tutors by subject, level, experience and availability so that I can find a practical match. |
| US-05 | Student | As a student I want to post a tutoring request and accept one interested tutor so that I can start lessons. |
| US-06 | Tutor | As a tutor I want to respond to students' requests so that I can find new students. |
| US-07 | Student / Tutor | As a user I want a private list of learning tasks with due dates so that I can plan my study or teaching. |
| US-08 | Group owner | As a tutor I want to create a learning group and add students by email so that I can teach them together. |
| US-09 | Group owner | As a group owner I want to allow selected members to create, edit or assign tasks so that trusted students can help run the group. |
| US-10 | Group member | As a group member I want to see only my own assignments and mark them complete so that my progress is tracked without exposing others. |
| US-11 | Student / Tutor | As a user I want to be told clearly when I am not allowed to do something so that I understand the limits of my role. |
| US-12 | Admin | As an admin I want to search and filter users and open a user's detail page so that I can investigate an account. |
| US-13 | Admin | As an admin I want to ban or suspend an account with a reason so that harmful users lose access immediately. |
| US-14 | Admin | As an admin I want an activity log and a security view of failed logins by IP and by account so that I can detect attacks. |
| US-15 | Admin | As an admin I want to export the filtered user, request, task or activity list as CSV so that I can report on it offline. |
| US-16 | Admin | As an admin I want to remove harmful requests, groups and tasks one at a time or in bulk so that the community stays safe. |
| US-17 | First Admin | As the First Admin I want to be the only one who can grant admin access so that privilege cannot spread without control. |

---

## Part B. Software Requirements (SRS)

### B1. Introduction

**Purpose.** This part states exactly what the delivered TutorInn system does. Every requirement has an ID and is linked in B7 to the endpoint or screen that implements it, the automated test that checks it and the screenshot that shows it.

**Intended readers.** The course instructor and examiners, future maintainers of the project, and testers checking the live deployment.

**Definitions**

| Term | Meaning in TutorInn |
|---|---|
| JWT | JSON Web Token (RFC 7519): a signed set of claims. TutorInn signs its access tokens with HMAC-SHA256 (HS256). |
| Access token | A JWT valid for 15 minutes, sent as `Authorization: Bearer <token>` and kept only in browser memory. |
| Refresh token | A random 48-byte opaque token stored in the httpOnly cookie `tutorinn_refresh`; the server keeps only its SHA-256 hash in `refresh_sessions`. Used once to obtain a new access token and a new refresh token. |
| Session family | All refresh sessions produced from one login by rotation. Reusing an old member revokes the whole family. |
| RBAC | Role-based access control: permissions depend on the account role stored in the database. |
| Role | `student`, `tutor`, `admin` or `moderator`. The First Admin is an `admin` with `is_first_admin = true`. |
| Permission | A named capability. Admin capabilities live in `ADMIN_PERMISSION_MATRIX`; group capabilities are `can_create_tasks`, `can_edit_tasks`, `can_assign_tasks`. |
| Audit log | The append-only `security_events` table, holding security events, user activity events and admin actions. |
| CSRF token | A random value in the readable cookie `tutorinn_csrf` that must be echoed in the `X-CSRF-Token` header on refresh and logout. |

**References**

- RFC 7519 JSON Web Token; RFC 6749 §10.4 refresh-token rotation guidance.
- OWASP ASVS 4.0 (V2 Authentication, V3 Session Management, V4 Access Control); OWASP Password Storage and CSRF Prevention cheat sheets.
- FastAPI, SQLAlchemy 2.0, PyJWT, argon2-cffi and Vercel documentation.
- Course template `FINAL_REPORT.md` (sayef-reyadh-labs/smarter-todo).

### B2. Functional Requirements

**Table 5: Authentication requirements (FR-AUTH)**

| ID | Requirement |
|---|---|
| FR-AUTH-01 | The system shall let a visitor register a Student or Tutor account with a unique email and a password of 12 to 128 characters, creating the linked profile in the same transaction. |
| FR-AUTH-02 | The system shall store passwords as Argon2id hashes (time cost 3, 64 MiB, parallelism 2) of an HMAC-SHA256 of the password keyed with a server-side pepper, and shall upgrade older un-peppered hashes after a successful login. |
| FR-AUTH-03 | The system shall answer a failed login with the same message, "Invalid email or password.", whether or not the email exists. |
| FR-AUTH-04 | The system shall issue an HS256 access token containing `sub`, `role`, `sid`, `iss`, `aud`, `iat`, `exp` and `jti`, valid for `ACCESS_TOKEN_MINUTES` (default 15, allowed 1–60). |
| FR-AUTH-05 | The system shall reject with 401 any access token that has a bad signature, wrong algorithm, issuer or audience, a missing claim, has expired, or whose session is revoked or expired. |
| FR-AUTH-06 | The system shall issue an opaque refresh token in an httpOnly, SameSite=Lax cookie restricted to `/api/auth` (Secure on Vercel), valid for `REFRESH_TOKEN_DAYS` (default 7), and store only its SHA-256 hash. |
| FR-AUTH-07 | The system shall rotate the refresh token on every refresh and, if an already-rotated token is presented again, revoke every session in that family and record `refresh_token_reuse`. |
| FR-AUTH-08 | The system shall require a matching CSRF token (cookie and header) for refresh and logout. |
| FR-AUTH-09 | The system shall revoke the current session and clear both cookies on logout. |
| FR-AUTH-10 | The system shall list a user's active sessions with device, IP and last-used time, mark the current one, and let the user revoke one session, all other sessions or all sessions, but never another account's session. |
| FR-AUTH-11 | The system shall return 429 for login after `LOGIN_MAX_ATTEMPTS` (default 5) failed attempts for one email within `LOGIN_LOCKOUT_MINUTES` (default 15), and shall rate-limit login, registration and refresh per IP address. |
| FR-AUTH-12 | The system shall let a signed-in user read and update only their own profile, ignoring any identity fields supplied by the client. |
| FR-AUTH-13 | The system shall change a password only after verifying the current password, and shall then revoke all of that account's sessions. |
| FR-AUTH-14 | The system shall support a password-reset request that does not reveal whether the email exists, needs a verified email and admin approval, and ends with a single-use, expiring reset token. |

**Table 6: Access-control requirements (FR-RBAC)**

| ID | Requirement |
|---|---|
| FR-RBAC-01 | The system shall assign every account exactly one role (`student`, `tutor`, `admin`, `moderator`) and shall read the role and status from the database on every request, treating the token's `role` claim as informational only. |
| FR-RBAC-02 | The system shall enforce roles on the server through the reusable `require_roles(...)` dependency, return 403 when the role is not allowed and record an `access_denied` event. |
| FR-RBAC-03 | The system shall filter private records (profiles, tutoring requests, personal tasks, sessions, assignments) by the owner's ID in the database query, returning 404 for records the user does not own. |
| FR-RBAC-04 | The system shall let only the Tutor who owns a group rename it, add or remove members, set member permissions and delete group tasks. |
| FR-RBAC-05 | The system shall let a group member create, edit or assign group tasks only when the owner has enabled the matching permission, and return 403 otherwise; each permission shall work independently. |
| FR-RBAC-06 | The system shall hide a group from non-members (404) and show each member only their own assignments, without other members' emails. |
| FR-RBAC-07 | The system shall let only the assigned Student change the completion state of their own assignment. |
| FR-RBAC-08 | The system shall prevent an admin from moderating their own account or another admin account (409), from revoking their own admin role (403), and from demoting the last active admin (409). |
| FR-RBAC-09 | The system shall protect the First Admin from suspension, banning, demotion and deletion, and shall let only the First Admin grant the admin role. |
| FR-RBAC-10 | The system shall reject a banned, suspended or deletion-pending account with 403 on its next request and revoke all of its refresh sessions when the status changes. |
| FR-RBAC-11 | The system shall limit the Moderator role to reviewing and deleting learning content and reviewing password-reset requests. |

**Table 7: Admin requirements (FR-ADM)**

| ID | Requirement |
|---|---|
| FR-ADM-01 | The system shall show admins overview statistics: account counts by status, students, tutors, tutoring requests, groups, pending tutor reviews, open and accepted requests, and 7-day trends. |
| FR-ADM-02 | The system shall list accounts with search (email or name), role, status and created-date filters and pagination (default 25, maximum 100 per page). |
| FR-ADM-03 | The system shall show a user detail view with profile, active sessions, the 30 most recent related events and related records, and shall audit each inspection. |
| FR-ADM-04 | The system shall let an admin set a Student or Tutor account to `active`, `banned` or `suspended` with a reason of 5–500 characters. |
| FR-ADM-05 | The system shall let the First Admin grant the admin role and any admin revoke it from another non-protected admin, with a reason, restoring the previous role and revoking the target's sessions. |
| FR-ADM-06 | The system shall let an admin revoke a single session of any account. |
| FR-ADM-07 | The system shall provide bulk status changes for 1–50 unique accounts, reporting success or the error for each account and the totals succeeded and failed. |
| FR-ADM-08 | The system shall let admins approve or reject tutor verification, singly or in bulk, without changing the tutor's role. |
| FR-ADM-09 | The system shall let admins and moderators list and remove tutoring requests, groups and group/personal tasks, singly or in bulk with a reason and confirmation, and review content reports and the subject catalogue. |
| FR-ADM-10 | The system shall provide an activity log filtered by event type, account, free-text search and date range, with pagination. |
| FR-ADM-11 | The system shall provide a security view for the last N hours with failure summaries by IP address and by account, registrations by IP, and a filterable event list. |
| FR-ADM-12 | The system shall export users, posts, tasks or activity as CSV using the same filters as the screen, neutralise spreadsheet formulas, cap the rows (default and maximum 10,000) and flag truncation with `X-Export-Limit-Reached`. |
| FR-ADM-13 | The system shall delete only authentication rate-limit counters older than `ACTIVITY_RETENTION_DAYS` (default 90) through a daily cron job, and allow only the First Admin to run the same cleanup manually. |
| FR-ADM-14 | The system shall let admins approve or reject account-deletion requests, choosing complete removal or anonymisation. |
| FR-ADM-15 | The system shall let admins and moderators approve or reject password-reset requests. |
| FR-ADM-16 | The system shall let the First Admin transfer the role to another active admin through a password-confirmed request that the recipient must accept within 24 hours. |

**Table 8: Domain requirements (FR-DOMAIN)**

| ID | Requirement |
|---|---|
| FR-DOMAIN-01 | The system shall let anyone search tutors by keyword, subject, level, minimum experience and availability, without exposing tutors' contact details. |
| FR-DOMAIN-02 | The system shall let a Student create, read, update and delete their own tutoring requests, each with subjects, level, availability, location, fee and description. |
| FR-DOMAIN-03 | The system shall let a Tutor respond Interested or Not Interested to a student's request, and show Tutors only their own responses. |
| FR-DOMAIN-04 | The system shall let the owning Student accept one pending or approved Interested response, mark the request `Accepted` and reject the other interested responses. |
| FR-DOMAIN-05 | The system shall provide personal learning tasks with title, description, optional category and due date, completion, search, category/status filters and a summary of open, completed, overdue and uncategorised tasks. |
| FR-DOMAIN-06 | The system shall let a Tutor create learning groups and add active Students to them by email. |
| FR-DOMAIN-07 | The system shall let permitted group users create group tasks with an optional Google Drive video link, accepting only HTTPS `drive.google.com` file links with a valid file ID. |
| FR-DOMAIN-08 | The system shall let permitted group users assign a task to all members or to selected current members only. |
| FR-DOMAIN-09 | The system shall let signed-in users report a profile, post, group or task to the admins. |
| FR-DOMAIN-10 | The system shall let a Student or Tutor request deletion of their account after confirming their password; the account becomes `deletion_pending` and its sessions are revoked. |

### B3. Non-Functional Requirements

**Table 9: Non-functional requirements**

| ID | Category | Requirement | How it is checked |
|---|---|---|---|
| NFR-SEC-01 | Security | All secrets (`JWT_SECRET`, `PASSWORD_PEPPER`, `DATABASE_URL`, `CRON_SECRET`, SMTP password) come from environment variables; the API refuses to issue tokens if `JWT_SECRET` or `PASSWORD_PEPPER` is shorter than 32 characters. | `test_password_hashing_requires_a_configured_server_side_pepper`; `.env.example` holds placeholders only |
| NFR-SEC-02 | Security | Login and password-reset errors are generic and do not reveal whether an account exists. | `test_password_reset_request_is_non_enumerating_and_requires_verified_email` |
| NFR-SEC-03 | Security | Every response carries `X-Content-Type-Options`, `X-Frame-Options: DENY`, a strict Content-Security-Policy, `Referrer-Policy` and, in production, HSTS. | `test_security_headers_are_added_to_api_responses`, `test_hsts_is_enabled_only_for_production_requests` |
| NFR-SEC-04 | Security | Unhandled errors return `{"detail": "Internal server error"}` with status 500 and no stack trace. | `test_unhandled_exception_returns_generic_500_without_internal_details` |
| NFR-SEC-05 | Security | Logged events never contain passwords, tokens, cookies or secrets; values are redacted before storage. | `test_security_event_redacts_secrets_and_control_characters` |
| NFR-PERF-01 | Performance | List endpoints are paginated with a maximum of 100 rows per page; exports are capped at 10,000 rows. | `test_export_limit_bounds_are_enforced` |
| NFR-PERF-02 | Performance | Typical list and detail requests complete in under 2 seconds on the deployed site. | Manual check in the browser network tab (D2) |
| NFR-USE-01 | Usability | Pages are responsive down to phone width, with a bottom navigation bar for signed-in roles on mobile. | Manual check; frontend layout tests |
| NFR-USE-02 | Usability | Every data screen shows loading, empty, error and retry states; forms show field validation, a password-strength indicator and a Caps Lock warning. | Manual check; `dashboard.test.mjs` |
| NFR-REL-01 | Reliability | Data is stored in hosted PostgreSQL and survives function restarts and redeployments; Vercel deployments refuse the ephemeral SQLite fallback. | `test_vercel_deployment_refuses_the_ephemeral_sqlite_fallback` |
| NFR-REL-02 | Reliability | The full migration chain replays cleanly on an empty PostgreSQL database in CI. | `test_supabase_migration_chain.py` (CI job) |
| NFR-MNT-01 | Maintainability | Authentication and role checks live in one module (`backend/app/auth.py`), admin capabilities in one matrix (`ADMIN_PERMISSION_MATRIX`). | Code review |
| NFR-MNT-02 | Maintainability | Backend and frontend tests, the TypeScript build and dependency audits run automatically on every push in GitHub Actions. | `.github/workflows/ci.yml` |

### B4. Roles and Permission Matrix

**Table 10: Endpoint groups by role** (Yes = allowed, No = denied by the server, Own = only the caller's own records)

| Endpoint group | Visitor | Student | Group member | Group owner (Tutor) | Admin |
|---|---|---|---|---|---|
| `POST /api/auth/register/*`, `/login`, `/refresh`, `/logout` | Yes | Yes | Yes | Yes | Yes (login only; no self-registration) |
| `GET/DELETE /api/auth/sessions*` | No | Own | Own | Own | Own |
| `GET/PUT /api/me/profile*`, `POST /api/me/password` | No | Own | Own | Own | No (admins have no profile) |
| `GET /api/tutors`, `GET /api/subjects` | Yes | Yes | Yes | Yes | Yes |
| `GET /api/dashboard` | No | Own | Own | Own | No |
| `POST/PUT/DELETE /api/requests` | No | Own | Own | No | No |
| `POST /api/requests/{id}/responses` | No | No | No | Yes (as Tutor) | No |
| `POST /api/requests/{id}/responses/{rid}/accept` | No | Own request | Own request | No | No |
| `/api/me/tasks*` (personal tasks) | No | Own | Own | Own | No |
| `GET /api/groups`, `GET /api/groups/{id}` | No | Groups they belong to | Yes | Own groups | No |
| `POST /api/groups`, `PUT /api/groups/{id}` | No | No | No | Own groups | No |
| Group members and permissions | No | No | No | Own groups | No |
| Create / edit / assign group task | No | No | If permission enabled | Yes | No |
| Delete group task | No | No | No | Yes | No (admin uses admin endpoint) |
| Update assignment completion | No | Own assignment | Own assignment | No | No |
| `POST /api/reports` | No | Yes | Yes | Yes | Yes |
| `/api/admin/*` | No | No | No | No | Yes (subject to Table 12) |

**Table 11: Group permissions**

| Permission | What it allows | Default for a new member |
|---|---|---|
| `can_create_tasks` | Create a new task in the group (`POST /api/groups/{id}/tasks`) | Off |
| `can_edit_tasks` | Change the title, description, due date or video link of any task in the group (`PUT /api/groups/{id}/tasks/{task_id}`) | Off |
| `can_assign_tasks` | Assign a task to all members or to chosen current members (`POST .../assignments`) | Off |
| Owner only | Rename the group, add and remove members, change member permissions, delete tasks, see members' emails and every member's assignment progress | — |
| Every member | View the group, see tasks they created, were assigned or may edit/assign, and mark their own assignments complete | Always |

**Table 12: Admin rules**

| Rule | Behaviour |
|---|---|
| Admin changes their own status | Rejected, 409 "Admin accounts and your own account cannot be moderated here." |
| Admin bans or suspends another admin | Rejected, 409 (single) or reported as failed per item (bulk) |
| Admin revokes their own admin role | Rejected, 403 |
| Demote the last active admin | Rejected, 409 |
| Ordinary admin grants the admin role | Rejected, 403; only the First Admin may grant it |
| Anyone acts against the First Admin | Rejected, 403 (protected from suspension, demotion and deletion; also enforced by a database trigger) |
| Manual activity cleanup | First Admin only (403 for other admins and moderators) |
| Admin rights inside a group | None. Group endpoints accept only Student and Tutor roles. Admins can view and delete groups and tasks only through `/api/admin/*`, and every deletion is audited. |
| Moderator | May view requests, tasks and groups, delete learning content and review password resets; may not manage accounts or roles, view activity or security, export or run cleanup |

### B5. Use Cases

**Figure 1: Use case diagram**

```mermaid
flowchart LR
  V([Visitor]) --- UC0((Register / browse tutors))
  S([Student]) --- UC1((UC-01 Log in and refresh))
  T([Tutor]) --- UC1
  A([Admin]) --- UC1
  S --- UC2((UC-02 Create a tutoring request))
  T --- UC3((UC-03 Change a member's permissions))
  S --- UC4((UC-04 Denied group action))
  A --- UC5((UC-05 Ban a user))
  A --- UC6((UC-06 Read the audit log))
  S --- UC7((UC-07 Complete own assignment))
  T --- UC8((UC-08 Respond to a request))
```

**Table 13: Use case descriptions**

**UC-01 Log in and refresh**
- *Actor:* Student, Tutor or Admin. *Preconditions:* the account exists and is active.
- *Main flow:* 1. The user enters email and password on `/login`. 2. The API checks the IP rate limit and the lockout counter. 3. It verifies the password hash. 4. It creates a refresh session, sets the `tutorinn_refresh` and `tutorinn_csrf` cookies and returns an access token. 5. The frontend keeps the token in memory and opens the dashboard. 6. When a request later returns 401, the frontend calls `POST /api/auth/refresh` once with the CSRF header, receives a new token pair and repeats the request.
- *Alternative and error flows:* wrong email or password → 401 "Invalid email or password."; 5 failures within 15 minutes → 429; too many requests from one IP → 429; suspended or banned → 403; missing or mismatched CSRF on refresh → 403; reused refresh token → 401 and the family is revoked; refresh fails → the frontend clears the session and shows the login page.
- *Postconditions:* one active refresh session exists; `login_succeeded` and `refresh_succeeded` events are recorded.

**UC-02 Create a tutoring request**
- *Actor:* Student. *Preconditions:* signed in; profile linked.
- *Main flow:* 1. The student opens the dashboard and fills in subjects, level, availability, location, fee and description. 2. The frontend sends `POST /api/requests`. 3. The API validates the body with Pydantic and sets the author from the token, not from the body. 4. The request is saved with status `Pending`. 5. It appears in the student's list and in tutors' incoming lists.
- *Errors:* invalid fields → 422; not signed in → 401; signed in as Tutor or Admin → 403; account without profile → 409.
- *Postconditions:* a new request owned by the student exists; an activity event is recorded.

**UC-03 Change a member's permissions**
- *Actor:* Tutor (group owner). *Preconditions:* the group exists, is owned by the tutor and the student is a member.
- *Main flow:* 1. The owner opens `/groups`, selects the group and a member. 2. They tick or untick create, edit and assign. 3. The frontend sends `PUT /api/groups/{id}/members/{student_id}/permissions`. 4. The API checks ownership and saves the three flags. 5. The updated group is returned and the member sees the new effective permissions on their next load.
- *Errors:* caller is a Tutor who does not own the group → 403 "Only the group owner can perform this action."; caller is a Student → 403; unknown member → 404.
- *Postconditions:* flags updated; `activity_group_member_permissions_updated` recorded with the new values.

**UC-04 A denied action**
- *Actor:* Student who is a group member without `can_create_tasks`.
- *Main flow:* 1. The member tries to add a task. 2. The frontend sends `POST /api/groups/{id}/tasks`. 3. The API finds the membership but the permission is off. 4. It returns 403 with "The group owner has not enabled permission: create tasks." 5. The page shows the message and nothing is created.
- *Alternative:* a student who is not a member gets 404, so the group's existence is not revealed; a student calling an admin endpoint gets 403 and an `access_denied` event is recorded.
- *Postconditions:* no data changed.

**UC-05 Ban a user**
- *Actor:* Admin. *Preconditions:* the target is a Student or Tutor account that is not pending deletion.
- *Main flow:* 1. The admin opens the user's detail page. 2. They choose Ban and type a reason (5–500 characters). 3. The frontend sends `PATCH /api/admin/users/{id}/status` with `{"status": "banned", "reason": ...}`. 4. The API sets the status, revokes all of the target's refresh sessions and writes `admin_account_status_changed` with the old status, new status and reason. 5. The list shows the account as banned.
- *Errors:* reason too short → 422; target is an admin or the caller → 409; target is the First Admin → 403; deletion pending → 409; not found → 404.
- *Postconditions:* the banned user's next API request returns 403 and their refresh is refused.

**UC-06 Read the audit log**
- *Actor:* Admin. *Preconditions:* signed in as admin.
- *Main flow:* 1. The admin opens the Activity tab. 2. They filter by event type, account, text or dates. 3. The frontend calls `GET /api/admin/activity` with the filters. 4. The API returns one page of events with the total count. 5. The admin can export the same filtered list with `GET /api/admin/export/activity`.
- *Errors:* start date after end date → 422; caller is a moderator → 403.
- *Postconditions:* nothing changes, except that the export itself is audited.

### B6. Acceptance Criteria

**Table 14: Acceptance criteria**

| ID | Requirement | Given | When | Then |
|---|---|---|---|---|
| AC-01 | FR-AUTH-05 | a valid access token whose `exp` is in the past | it is sent to `GET /api/auth/me` | the API returns 401 "Invalid or expired access token." |
| AC-02 | FR-AUTH-05 | a valid token whose payload or signature has been changed (for example `role` set to `admin`) | it is sent to any protected endpoint | the API returns 401 and records `access_token_rejected` |
| AC-03 | FR-AUTH-05 | a token signed with the wrong issuer, audience or algorithm | it is used | the API returns 401 |
| AC-04 | FR-AUTH-07 | a refresh token that has already been rotated | it is presented to `/api/auth/refresh` | the API returns 401, revokes every session in the family and records `refresh_token_reuse` |
| AC-05 | FR-RBAC-03 | Student A and Student B each have a personal task and a tutoring request | Student A requests B's task or request by ID | the API returns 404 and B's record is unchanged |
| AC-06 | FR-RBAC-05 | a group member without `can_create_tasks` | they post a new group task | the API returns 403 and no task is created |
| AC-07 | FR-RBAC-05 | the owner enables only `can_assign_tasks` for a member | the member tries to edit a task | the API returns 403, but assigning the task succeeds |
| AC-08 | FR-RBAC-10 | a signed-in student with a valid access token | an admin bans the student and the student makes another request | the request returns 403 and refreshing returns 401/403 |
| AC-09 | FR-RBAC-08 | Admin A and Admin B | Admin A tries to ban Admin B | the API returns 409 and B stays active |
| AC-10 | FR-RBAC-09 | an ordinary admin | they try to grant the admin role or suspend the First Admin | the API returns 403 |
| AC-11 | FR-AUTH-11 | an existing account | 5 wrong passwords are tried, then the correct one | the sixth attempt returns 429 |
| AC-12 | FR-AUTH-08 | a valid refresh cookie but a missing or different `X-CSRF-Token` | refresh or logout is called | the API returns 403 and the session stays valid |
| AC-13 | FR-AUTH-13 | a signed-in user with two sessions | they change their password with the correct current password | both sessions are revoked |
| AC-14 | FR-ADM-12 | an admin user list filtered by a search term | the admin exports users | the CSV contains only matching rows and cells starting with `=`, `+`, `-` or `@` are prefixed with `'` |

### B7. Traceability Matrix

**Table 15: Requirement, implementation, test and screenshot**

| Requirement | Endpoint or screen | Automated test | Screenshot |
|---|---|---|---|
| FR-AUTH-01 | `POST /api/auth/register/student`, `/register/tutor`; `/register` | `test_student_registration_password_hash_login_and_current_account`, `test_tutor_registration_and_duplicate_account_email_are_rejected` | S1 |
| FR-AUTH-02 | `auth.hash_password`, `verify_password` | `test_legacy_argon2_hash_is_upgraded_after_successful_login`, `test_password_hashing_requires_a_configured_server_side_pepper` | — (code, C6) |
| FR-AUTH-03 | `POST /api/auth/login`; `/login` | `test_student_registration_password_hash_login_and_current_account` | S1 |
| FR-AUTH-04 | `auth.create_access_token` | `test_student_registration_password_hash_login_and_current_account` | S7 |
| FR-AUTH-05 | `auth.get_current_account` | `test_invalid_and_tampered_access_tokens_are_rejected`, `test_expired_access_tokens_are_rejected`, `test_jwt_rejects_wrong_issuer_audience_and_unsupported_algorithm` | S7 |
| FR-AUTH-06 | `_set_auth_cookies` | `test_auth_cookies_are_secure_on_vercel` | S8 |
| FR-AUTH-07 | `POST /api/auth/refresh` | `test_refresh_rotation_reuse_detection_revokes_entire_session_family` | S8 |
| FR-AUTH-08 | `_require_csrf` | `test_refresh_rejects_missing_or_mismatched_csrf_token`, `test_logout_rejects_invalid_csrf_without_revoking_session` | S8 |
| FR-AUTH-09 | `POST /api/auth/logout` | `test_logout_revokes_access_session_and_clears_auth_cookies` | S4 |
| FR-AUTH-10 | `/api/auth/sessions*`; `/profile` sessions panel | `test_account_can_list_and_revoke_only_its_own_sessions`, `test_account_can_revoke_other_sessions_without_revoking_current_session`, `test_account_can_revoke_all_sessions_including_current_session`, `test_account_cannot_revoke_another_accounts_session` | S4 |
| FR-AUTH-11 | `enforce_auth_rate_limit`, `failed_login_count` | `test_repeated_failed_logins_trigger_temporary_lockout`, `test_login_ip_rate_limit_is_enforced`, `test_registration_endpoint_enforces_configurable_ip_rate_limit`, `test_refresh_ip_rate_limit_is_enforced` | S16 |
| FR-AUTH-12 | `/api/me/profile*`; `/profile` | `test_student_owns_private_profile_and_can_update_only_student_fields`, `test_profile_updates_reject_client_supplied_identity_and_stay_self_scoped` | S3 |
| FR-AUTH-13 | `POST /api/me/password`; `/profile` | `test_password_change_verifies_current_password_and_revokes_all_sessions` | S3 |
| FR-AUTH-14 | `/api/auth/password-reset/*`; `/forgot-password`, `/admin/password-resets` | `test_password_reset_request_is_non_enumerating_and_requires_verified_email`, `test_password_reset_approval_and_single_use_reset_revoke_sessions` | — |
| FR-RBAC-01 | `get_current_account` | `test_authenticated_request_ownership_and_role_enforcement` | S6 |
| FR-RBAC-02 | `require_roles` | `test_authenticated_request_ownership_and_role_enforcement`, `test_admin_management_overview_and_role_protection` | S6 |
| FR-RBAC-03 | `/api/requests*`, `/api/me/tasks*` | `test_task_ownership_isolated_between_student_and_tutor`, `test_student_request_crud_and_tutor_response_privacy` | S2 |
| FR-RBAC-04 | `/api/groups/{id}` owner routes; `/groups` | `test_member_permissions_are_enforced_and_owner_controls_group_tasks` | S5 |
| FR-RBAC-05 | `_can(...)` in `groups.py` | `test_each_member_permission_is_independent_and_enforced` | S5, S6 |
| FR-RBAC-06 | `_group_read`, `_task_read` | `test_tutor_group_crud_membership_and_private_group_access`, `test_member_task_responses_never_expose_other_students_assignment_details` | S5 |
| FR-RBAC-07 | `PATCH /api/groups/{id}/tasks/{tid}/completion` | `test_student_sees_only_own_assignments_and_can_update_only_own_completion` | S5 |
| FR-RBAC-08 | `/api/admin/users/{id}/status`, `/admin-role` | `test_admin_cannot_moderate_self_or_another_admin_and_ban_revokes_existing_access`, `test_an_admin_cannot_revoke_their_own_admin_role` | S13 |
| FR-RBAC-09 | `grant_admin_role`, First Admin trigger | `test_ordinary_admin_cannot_grant_admin_role`, `test_other_admins_and_moderators_cannot_suspend_or_demote_the_first_admin` | — |
| FR-RBAC-10 | `get_current_account`, `/api/auth/refresh` | `test_suspended_account_cannot_use_existing_access_or_refresh_session`, `test_admin_moderation_revokes_sessions_and_blocks_login` | S9 |
| FR-RBAC-11 | `ADMIN_PERMISSION_MATRIX` | `test_moderator_can_review_requests_and_moderate_learning_content`, `test_moderator_cannot_manage_accounts_roles_exports_or_activity_cleanup` | — |
| FR-ADM-01 | `GET /api/admin/overview`; Admin › Overview | `test_admin_overview_includes_beta_resource_counts_and_recent_accounts` | S10 |
| FR-ADM-02 | `GET /api/admin/users`; Admin › Students/Tutors/Admins | `test_admin_accounts_are_searchable_and_role_filtered_and_detail_includes_related_records` | S11 |
| FR-ADM-03 | `GET /api/admin/users/{id}` | same as above | S12 |
| FR-ADM-04 | `PATCH /api/admin/users/{id}/status` | `test_admin_moderation_revokes_sessions_and_blocks_login` | S13 |
| FR-ADM-05 | `/api/admin/users/{id}/admin-role` | `test_admin_role_grants_are_audited_reversible_and_admin_can_revoke_account_sessions`, `test_role_grant_and_revocation_are_audited_with_actor_affected_account_and_reason` | — |
| FR-ADM-06 | `DELETE /api/admin/users/{id}/sessions/{sid}` | `test_admin_role_grants_are_audited_reversible_and_admin_can_revoke_account_sessions` | S12 |
| FR-ADM-07 | `POST /api/admin/users/bulk-status` | `test_admin_bulk_moderation_reports_partial_failures_and_enforces_limit` | S14 |
| FR-ADM-08 | `/api/admin/tutors/*verification` | `test_admin_tutor_verification_is_separate_from_role` | — |
| FR-ADM-09 | `/api/admin/requests*`, `/groups*`, `/tasks*`, `/reports`, `/subjects` | `test_admin_removes_tutoring_requests_singly_and_in_bulk_with_audit`, `test_bulk_delete_reports_partial_failures_and_audits_each_removed_group`, `test_bulk_delete_requires_confirmation_reason_and_a_bounded_unique_list` | S14 |
| FR-ADM-10 | `GET /api/admin/activity`; Admin › Activity | `test_admin_activity_and_security_views_filter_by_event_type_account_and_search` | S15 |
| FR-ADM-11 | `GET /api/admin/security`; Admin › Security | `test_admin_security_report_has_distinct_source_summaries_and_50_hostile_events` | S16 |
| FR-ADM-12 | `GET /api/admin/export/{kind}` | `test_user_export_contains_only_rows_matching_the_active_search_filter`, `test_spreadsheet_formulas_are_neutralized_in_exported_cells`, `test_large_export_is_capped_at_the_requested_limit_and_marks_itself_as_limited` | S17 |
| FR-ADM-13 | cron route, `DELETE /api/admin/activity/purge` | `test_automatic_activity_retention_removes_only_rate_limit_counters_and_keeps_login_history`, `test_ordinary_admin_cannot_run_activity_cleanup_because_only_the_first_admin_can` | — |
| FR-ADM-14 | `/api/admin/account-deletion-requests*`; `/admin/deletions` | `test_account_deletion_request_rejection_restores_account_and_keeps_sessions_revoked`, `test_admin_must_explain_deletion_scope_override_and_email_the_reason` | — |
| FR-ADM-15 | `/api/admin/password-reset-requests*` | `test_password_reset_approval_and_single_use_reset_revoke_sessions` | — |
| FR-ADM-16 | `/api/admin/first-admin-transfer*` | `test_first_admin_transfer.py` (8 tests) | — |
| FR-DOMAIN-01 | `GET /api/tutors`; Student dashboard discovery | `test_student_dashboard_and_tutor_discovery_filters` | S2 |
| FR-DOMAIN-02 | `/api/requests*` | `test_student_request_crud_and_tutor_response_privacy` | S2 |
| FR-DOMAIN-03 | `POST /api/requests/{id}/responses` | `test_student_request_crud_and_tutor_response_privacy` | — |
| FR-DOMAIN-04 | `POST .../responses/{rid}/accept` | `test_student_acceptance_updates_request_and_tutor_response_statuses` | — |
| FR-DOMAIN-05 | `/api/me/tasks*` | `test_student_task_crud_completion_and_due_status`, `test_task_filters_summary_validation_and_authentication` | — |
| FR-DOMAIN-06 | `POST /api/groups`, `/members` | `test_tutor_group_crud_membership_and_private_group_access` | S5 |
| FR-DOMAIN-07 | group task routes | `test_drive_video_links.py`, `test_group_video_links_api.py` | S5 |
| FR-DOMAIN-08 | `POST .../assignments` | `test_assignment_targets_must_be_current_group_members` | S5 |
| FR-DOMAIN-09 | `POST /api/reports` | `test_moderation_subjects.py` | — |
| FR-DOMAIN-10 | `POST /api/me/deletion-request` | `test_pending_deletion_blocks_access_and_rejection_restores_group_membership` | — |
| NFR-SEC-01…05, NFR-REL-01/02 | see Table 9 | see Table 9 | S19 |

---

## Part C. Technical Design (TDD)

### C1. Technology Stack

**Table 16: Technology stack**

| Component | Technology | Version | Reason |
|---|---|---|---|
| Frontend | React with TypeScript | React 19.3, TypeScript 7.0 | Component model and static typing for shared API contracts |
| Build tool | Rspack | 2.3 | Fast Rust-based bundler with a webpack-compatible config; used by the course template |
| UI library | None — hand-written CSS with design tokens (`index.css`) | — | Full control over light/dark themes, four palettes and accessibility without a large dependency |
| Backend | FastAPI (`fastapi[standard]`) | ≥ 0.141.1 | Typed request validation with Pydantic, dependency injection for auth checks, automatic OpenAPI docs |
| Validation | Pydantic | v2 (bundled with FastAPI) | Server-side validation and safe response models |
| Database | PostgreSQL on Supabase (production); SQLite (local and tests) | PostgreSQL 17 in CI | Free hosted Postgres with backups; SQLite needs no setup for development |
| ORM and migrations | SQLAlchemy, Alembic, Supabase SQL migrations | SQLAlchemy ≥ 2.0.40, Alembic ≥ 1.15 | Parameterised queries, typed models, versioned schema changes |
| DB driver | psycopg (binary) | ≥ 3.2.6 | Modern PostgreSQL driver |
| Password hashing | argon2-cffi (Argon2id) + HMAC-SHA256 pepper | ≥ 23.1 | Memory-hard hashing recommended by OWASP; pepper protects a leaked database |
| JWT library | PyJWT | ≥ 2.10.1 | Small, well-maintained, strict claim validation |
| Backend tests | pytest + httpx (FastAPI TestClient) | pytest ≥ 8, httpx ≥ 0.27 | API-level tests against an isolated database |
| Frontend tests | Node test runner (`node --test`) | Node 22 | No extra test framework needed |
| CI | GitHub Actions | — | Runs tests, migration replay, build and dependency audits on every push |
| Hosting | Vercel (one project, two services) + Vercel Cron | — | Free tier, Git-based deploys, FastAPI support |

### C2. System Architecture

**Figure 2: System architecture**

```mermaid
flowchart LR
  B["Browser: React SPA<br/>access token in memory"] -- "1. GET / (HTML, JS)" --> F["Vercel frontend service<br/>static dist/"]
  B -- "2. /api/* with Authorization: Bearer" --> R{"Vercel routing<br/>vercel.json rewrites"}
  B -- "3. POST /api/auth/refresh<br/>httpOnly cookie + X-CSRF-Token" --> R
  R --> API["Vercel backend service<br/>FastAPI app.main:app"]
  API -- "4. SQL via SQLAlchemy, DATABASE_URL (TLS)" --> DB[("Supabase PostgreSQL")]
  API -- "5. INSERT security_events" --> LOG[("Audit log table<br/>security_events")]
  CRON["Vercel Cron 03:00 UTC"] -- "6. GET /api/internal/maintenance/activity-retention<br/>Bearer CRON_SECRET" --> API
```

1. **Browser → frontend service.** The browser downloads the compiled React app from the frontend service. Every non-API path is rewritten to `index.html`, so client-side routes such as `/admin` load the same bundle.
2. **Browser → API with the access token.** Each API call is a same-origin `fetch` to `/api/...`. The shared client (`frontend/src/api/api.ts`) adds `Authorization: Bearer <token>` from a module variable; the token never touches `localStorage`.
3. **Browser → refresh endpoint with the cookie.** When a token expires the client calls `POST /api/auth/refresh`. The browser sends the httpOnly `tutorinn_refresh` cookie automatically (path `/api/auth` only), and the client copies the readable `tutorinn_csrf` cookie into the `X-CSRF-Token` header.
4. **API → database.** FastAPI handlers read and write through SQLAlchemy sessions over a TLS connection given by `DATABASE_URL`. The browser has no database credentials, and Supabase's public Data API is closed: RLS is on and `anon`/`authenticated` grants are revoked.
5. **API → audit log.** Security events, user activity and admin actions are inserted into `security_events` in the same database. Values are sanitised first, and noisy unauthenticated events are capped per IP per minute.
6. **Cron → API.** Vercel Cron calls the retention route once a day with `Authorization: Bearer <CRON_SECRET>`. The route deletes only old rate-limit counters and keeps all incident and audit records.

### C3. Backend and Frontend Structure

**Backend (two levels)**

```text
backend/
├── app/
│   ├── main.py            # FastAPI app, CORS, security headers, 500 handler, router registration
│   ├── auth.py            # Hashing, JWT, get_current_account, require_roles, rate limits, audit writer
│   ├── dependencies.py    # Legacy demo-mode guards (disabled on Vercel)
│   ├── database.py        # Engine, session dependency, Vercel SQLite refusal
│   ├── models.py          # SQLAlchemy models (23 tables)
│   ├── schemas.py         # Pydantic request/response models
│   ├── crud.py            # MVP profile, post and response workflows
│   ├── notifications.py   # Optional SMTP notifications
│   └── routers/           # auth, account, beta_requests, tasks, groups, admin, moderation,
│                          # password_resets, email_verification, first_admin_transfer,
│                          # students, tutors, posts, profiles, system
├── alembic/               # env.py, versions/ (ordered schema revisions)
├── scripts/               # create_first_admin.py, seed_demo_accounts.py, setup_local_env.py
├── tests/                 # pytest modules (one per feature area)
├── requirements.txt, requirements-dev.txt, alembic.ini, .env.example
supabase/migrations/       # SQL migrations applied to the hosted database
```

- **Routes:** `backend/app/routers/`, one module per domain. `main.py` only registers them.
- **Services and repositories:** MVP workflows sit in `crud.py`. The newer admin, groups and tasks routers still run their SQLAlchemy queries inside the handlers; this is a known layering gap (E3), not a separate services package.
- **Models:** `models.py`. **Schemas:** `schemas.py`.
- **Authentication code:** `auth.py` (tokens, hashing, `get_current_account`) and `routers/auth.py` (login, refresh, logout, sessions, cookies, CSRF).
- **RBAC module:** `require_roles` in `auth.py`; `ADMIN_PERMISSION_MATRIX` and `require_admin_permission` in `routers/admin.py`; group checks `_owner`, `_member` and `_can` in `routers/groups.py`.
- **Admin code:** `routers/admin.py`, `moderation.py`, `password_resets.py`, `first_admin_transfer.py`.

**Frontend (two levels)**

```text
frontend/
├── src/
│   ├── App.tsx            # Path-based router: picks the page for window.location.pathname
│   ├── main.tsx           # Mounts ThemeProvider and AuthProvider
│   ├── api/               # api.ts (shared HTTP client, token, refresh-once) + auth, dashboard,
│   │                      # tasks, groups, admin, moderation, profiles, posts, subjects, ...
│   ├── context/           # AuthContext.tsx, ThemeContext.tsx
│   ├── pages/             # route-level pages (Login, Register, Dashboard, MyProfile,
│   │                      # GroupLearning, AdminReview, AdminReports, AdminSubjects, ...)
│   ├── components/        # SiteHeader, PasswordField, PersonalTasksPanel, SubjectPicker, ...
│   ├── layouts/           # AppLayout.tsx (shell + mobile bottom navigation)
│   ├── hooks/             # useSelectedProfile.ts
│   ├── types/             # domain.ts, auth.ts, forms.ts
│   └── index.css          # Design tokens, themes, responsive rules
├── tests/                 # node:test modules
├── rspack.config.mjs, tsconfig.json, package.json
```

- **Pages and components:** `pages/` and `components/`. Pages never call `fetch` directly.
- **API client:** `api/api.ts` owns transport, the in-memory token, the single-flight refresh and error parsing.
- **Authentication context:** `context/AuthContext.tsx` restores the session on load through one refresh call and exposes `account`, `login`, `register` and `logout`.
- **Route guards:** each protected page checks `account` and its role from the context and shows a "sign in" or "access required" state. These guards are for user experience only; the API enforces access.

### C4. Data Model

**Figure 3: ER diagram (main tables)**

```mermaid
erDiagram
  user_accounts ||--o{ refresh_sessions : has
  user_accounts ||--o{ security_events : "actor of"
  user_accounts ||--o| students : "linked profile"
  user_accounts ||--o| tutors : "linked profile"
  tutors ||--o| tutor_verifications : "verified by"
  students ||--o{ learning_posts : "authors (student request)"
  learning_posts ||--o{ interest_responses : receives
  user_accounts ||--o{ personal_learning_tasks : owns
  user_accounts ||--o{ learning_groups : "owns (tutor)"
  learning_groups ||--o{ learning_group_members : has
  user_accounts ||--o{ learning_group_members : "is (student)"
  learning_groups ||--o{ group_learning_tasks : contains
  group_learning_tasks ||--o{ group_task_assignments : "assigned via"
  user_accounts ||--o{ group_task_assignments : "assigned to"
  user_accounts ||--o{ content_reports : files
  user_accounts ||--o{ password_reset_requests : requests
  password_reset_requests ||--o{ password_reset_tokens : issues
  user_accounts ||--o{ email_verification_tokens : verifies
  user_accounts ||--o{ account_deletion_requests : requests
  account_deletion_requests ||--o{ retained_content : keeps
  account_deletion_requests ||--o{ former_user_content_tokens : issues
  account_deletion_requests ||--o{ former_user_content_removal_requests : receives
  user_accounts ||--o{ first_admin_transfers : "initiates / receives"
```

`managed_subjects` stands alone (the subject catalogue). Timestamps are stored as ISO-8601 UTC strings.

**Table 17: `user_accounts`**

| Column | Type | Keys / constraints | Index |
|---|---|---|---|
| id | integer | PK | yes |
| email | varchar(255) | unique, not null | yes |
| password_hash | varchar(255) | not null (prefix `tutorinn$argon2id$pepper-v1$`) | — |
| role | varchar(16) | not null: student, tutor, admin, moderator | yes |
| is_first_admin | boolean | default false; at most one true (partial unique index + trigger in Supabase) | — |
| status | varchar(16) | default `active`: active, banned, suspended, deletion_pending | yes |
| email_verified_at | varchar(40) | nullable | — |
| created_at, updated_at | varchar(40) | not null | — |

**Table 18: `refresh_sessions`**

| Column | Type | Keys / constraints | Index |
|---|---|---|---|
| id | integer | PK (also the `sid` claim) | yes |
| account_id | integer | FK → user_accounts.id, not null | yes |
| token_hash | varchar(64) | SHA-256 of the refresh token, unique | unique |
| family_id | varchar(36) | UUID shared by one login's rotations | yes |
| csrf_token_hash | varchar(64) | SHA-256 of the CSRF token | — |
| created_at, last_used_at | varchar(40) | not null | — |
| expires_at | varchar(40) | not null | yes |
| revoked_at | varchar(40) | null while active | — |
| replaced_by | varchar(64) | hash of the next token after rotation | — |
| user_agent, ip_address | varchar(512), varchar(64) | for the session list | — |

**Table 19: `security_events` (audit log)**

| Column | Type | Keys / constraints | Index |
|---|---|---|---|
| id | integer | PK | yes |
| account_id | integer | FK → user_accounts.id, nullable (unknown for anonymous attempts) | yes |
| event_type | varchar(64) | e.g. `login_failed`, `access_denied`, `admin_account_status_changed`, `activity_group_task_created` | yes |
| attempted_email | varchar(255) | attempted email, or the target for admin/activity events | — |
| ip_address, user_agent | varchar(64), varchar(512) | request context | — |
| details | text | sanitised `key=value` context, never secrets | — |
| created_at | varchar(40) | not null | — |

No API route edits or deletes audit rows (checked by `test_audit_immutability.py`); the only deletions are of old `auth_attempt_%` rate-limit counters by the retention job or the First Admin purge.

**Table 20: Profiles and tutoring requests**

| Table | Main columns | Keys and constraints |
|---|---|---|
| `students` | id, account_id, full_name, email, phone_number, education_level, preferred_subjects, subjects_json | PK id; FK account_id → user_accounts (unique when not null); email unique |
| `tutors` | id, account_id, full_name, email, phone_number, subject, teaching_level, experience_years, hourly_rate, bio, availability, subjects_json | as above; subject indexed |
| `tutor_verifications` | id, tutor_id, status (pending/approved/rejected), reviewer_account_id, reviewed_at, review_note | FK tutor_id unique, ON DELETE CASCADE |
| `learning_posts` | id, post_type, author_profile_type, author_profile_id, subject, subjects_json, level, availability, location, fee, description, status (Pending/Accepted), created_at | PK id; indexes on post_type, subject, author fields, created_at |
| `interest_responses` | id, post_id, profile_type, profile_id, response (Interested/Not Interested), review_status, created_at, updated_at | unique (post_id, profile_type, profile_id) |

**Table 21: Tasks and groups**

| Table | Main columns | Keys and constraints |
|---|---|---|
| `personal_learning_tasks` | id, owner_account_id, title (≤160), description, category, due_date, completed, created_at, updated_at | FK owner → user_accounts ON DELETE SET NULL; indexes (owner, due_date) and (owner, category) |
| `learning_groups` | id, owner_account_id, name (≤100), description | FK owner → user_accounts |
| `learning_group_members` | id, group_id, student_account_id, can_create_tasks, can_edit_tasks, can_assign_tasks, joined_at | FK group ON DELETE CASCADE; unique (group_id, student_account_id) |
| `group_learning_tasks` | id, group_id, created_by_account_id, title, description, video_url (≤2048), due_date | FK group ON DELETE CASCADE |
| `group_task_assignments` | id, task_id, student_account_id, completed, assigned_at, completed_at | FK task ON DELETE CASCADE; unique (task_id, student_account_id) |

**Table 22: Moderation, recovery and admin workflow tables**

| Table | Purpose |
|---|---|
| `content_reports` | User reports (target type and ID, reason, status, reviewer); indexed by status and date |
| `managed_subjects` | Admin-managed subject catalogue; name unique |
| `password_reset_requests` / `password_reset_tokens` | Admin-approved reset queue and single-use hashed reset tokens |
| `email_verification_tokens` | Hashed single-use email verification tokens |
| `account_deletion_requests`, `retained_content`, `former_user_content_tokens`, `former_user_content_removal_requests` | Deletion requests, what content is kept or anonymised, and the former-user recovery links |
| `first_admin_transfers` | Pending, accepted, declined, cancelled or expired transfer of the First Admin flag |

**How the key concepts are stored**

- **Roles** are one column, `user_accounts.role`, plus the `is_first_admin` flag. Changing a role revokes the account's sessions, so the next request sees the new role.
- **Bans** are `user_accounts.status`. The history is not overwritten: each change writes an `admin_account_status_changed` event with old status, new status and reason.
- **Sessions and refresh tokens** are rows in `refresh_sessions`. Revoking sets `revoked_at`; rotation sets `replaced_by` and creates a new row with the same `family_id`.
- **Group membership with permissions** is one row per (group, student) in `learning_group_members` with three boolean flags. The owner is not stored as a member; ownership is `learning_groups.owner_account_id`.
- **The activity log** is `security_events`. Admin actions use the prefix `admin_`, user actions `activity_`, and authentication events their own names.

### C5. API Design

All routes are under the `/api` prefix. There is no `/v1` segment; the OpenAPI document reports version 2.3.0. Errors use FastAPI's standard shape:

```json
{ "detail": "Only the group owner can perform this action." }
```

Validation errors (422) return `detail` as a list of `{loc, msg, type}` objects. Unhandled errors return `{"detail": "Internal server error"}` with 500.

**Table 23: Endpoint list** (Auth: — none, B bearer token, C refresh cookie + CSRF header)

| Method and path | Auth | Role / permission | Body | Success | Errors |
|---|---|---|---|---|---|
| POST /api/auth/register/student | — | public | email, password, full_name, education_level, subjects | 201 | 409, 422, 429 |
| POST /api/auth/register/tutor | — | public | email, password, profile fields | 201 | 409, 422, 429 |
| POST /api/auth/login | — | public | email, password | 200 | 401, 403, 422, 429 |
| POST /api/auth/refresh | C | any active | — | 200 | 401, 403, 429 |
| POST /api/auth/logout | C | — | — | 200 | 403 |
| GET /api/auth/me | B | any | — | 200 | 401, 403 |
| GET /api/auth/sessions | B | any | — | 200 | 401 |
| DELETE /api/auth/sessions/{id} · /others · /all | B | own sessions | — | 204 | 401, 404 |
| POST /api/auth/password-reset/request · /complete | — | public | email · token, new_password | 202 · 200 | 400, 422, 429 |
| POST /api/auth/email-verification/request · /complete | B · — | — | — · token | 202 · 200 | 400, 429 |
| GET /api/me/profile | B | student, tutor | — | 200 | 401, 403, 409 |
| PUT /api/me/profile/student · /tutor | B | student · tutor | profile fields | 200 | 403, 422 |
| POST /api/me/password | B | student, tutor | current_password, new_password | 200 | 400, 422 |
| GET/POST /api/me/deletion-request | B | student, tutor | password, options | 200/201 | 400, 409 |
| GET /api/tutors · /api/tutors/{id} | — | public | q, subject, level, min_experience, availability | 200 | 404, 422 |
| GET /api/subjects · /api/health | — | public | — | 200 | — |
| GET /api/dashboard | B | student, tutor | — | 200 | 401, 403, 409 |
| GET/POST /api/requests | B | GET: student, tutor · POST: student | request fields | 200/201 | 403, 422 |
| GET/PUT/DELETE /api/requests/{id} | B | owner student | request fields | 200/204 | 403, 404, 409 |
| POST /api/requests/{id}/responses | B | tutor | response | 200 | 403, 404, 409 |
| GET /api/requests/{id}/responses | B | owner student | — | 200 | 404 |
| GET /api/me/responses | B | tutor | — | 200 | 403 |
| POST /api/requests/{id}/responses/{rid}/accept | B | owner student | — | 200 | 404, 409 |
| GET /api/me/tasks · /summary | B | student, tutor (own) | q, category, uncategorized, status | 200 | 401, 403, 422 |
| POST /api/me/tasks | B | student, tutor | title, description, category, due_date | 201 | 422 |
| GET/PUT/DELETE /api/me/tasks/{id} | B | owner | task fields | 200/204 | 404 |
| GET /api/groups | B | student, tutor | — | 200 | 403 |
| POST /api/groups | B | tutor | name, description | 201 | 403, 422 |
| GET /api/groups/{id} | B | owner or member | — | 200 | 404 |
| PUT /api/groups/{id} | B | owner | name, description | 200 | 403, 404 |
| POST /api/groups/{id}/members | B | owner | student_email | 201 | 403, 404, 409 |
| DELETE /api/groups/{id}/members/{sid} | B | owner | — | 204 | 403, 404 |
| PUT /api/groups/{id}/members/{sid}/permissions | B | owner | can_create_tasks, can_edit_tasks, can_assign_tasks | 200 | 403, 404 |
| POST /api/groups/{id}/tasks | B | owner or `can_create_tasks` | title, description, video_url, due_date | 201 | 403, 404, 422 |
| PUT /api/groups/{id}/tasks/{tid} | B | owner or `can_edit_tasks` | same | 200 | 403, 404, 422 |
| DELETE /api/groups/{id}/tasks/{tid} | B | owner | — | 204 | 403, 404 |
| POST /api/groups/{id}/tasks/{tid}/assignments | B | owner or `can_assign_tasks` | all_members or student_account_ids | 200 | 403, 404, 422 |
| PATCH /api/groups/{id}/tasks/{tid}/completion | B | assigned student | completed | 200 | 404 |
| POST /api/reports | B | any signed-in | target_type, target_id, reason, description | 201 | 404, 409, 422 |
| GET /api/admin/overview | B | admin (`view_dashboard`) | — | 200 | 401, 403 |
| GET /api/admin/users · /users/{id} | B | admin (`view_users`) | role, status, q, created_from/to, offset, limit | 200 | 403, 404, 422 |
| PATCH /api/admin/users/{id}/status | B | admin (`manage_accounts`) | status, reason | 200 | 403, 404, 409, 422 |
| POST /api/admin/users/bulk-status | B | admin | account_ids (≤50), status, reason | 200 | 422 |
| POST/DELETE /api/admin/users/{id}/admin-role | B | First Admin to grant; admin to revoke | reason | 200 | 403, 404, 409, 422 |
| DELETE /api/admin/users/{id}/sessions/{sid} | B | admin | — | 200 | 404, 409 |
| GET /api/admin/tutors · PATCH …/{id}/verification · POST …/bulk-verification | B | admin | status, note | 200 | 404, 422 |
| GET /api/admin/requests · POST …/{id}/remove · …/bulk-remove | B | admin, moderator | reason, confirm | 200 | 404, 422 |
| GET /api/admin/groups · group-tasks · tasks; DELETE single and /bulk | B | admin, moderator | ids, reason, confirm | 200 | 404, 422 |
| GET /api/admin/activity | B | admin (`view_activity`) | event_type, q, account_id, dates, offset, limit | 200 | 403, 422 |
| GET /api/admin/security | B | admin (`view_security`) | hours, min_events, event_type, q, account_id | 200 | 403 |
| GET /api/admin/export/{users\|posts\|tasks\|activity} | B | admin (`export_data`) | same filters + limit | 200 (text/csv) | 403, 404, 422 |
| DELETE /api/admin/activity/purge | B | First Admin | before, reason, confirm | 200 | 403, 422 |
| GET /api/admin/reports · PATCH …/{id} | B | admin, moderator | status, review_note | 200 | 404, 422 |
| GET/POST/PATCH/DELETE /api/admin/subjects | B | admin, moderator | name, active | 200/201 | 409, 422 |
| GET/PATCH /api/admin/account-deletion-requests | B | admin | decision, final options, reason | 200 | 404, 409, 422 |
| GET/PATCH /api/admin/password-reset-requests | B | admin, moderator | decision, note | 200 | 404, 409 |
| GET/POST/DELETE /api/admin/first-admin-transfer · /accept · /decline | B | First Admin / recipient admin | password, recipient email ×2 | 200/201 | 400, 403, 409, 429 |
| GET /api/internal/maintenance/activity-retention | Bearer CRON_SECRET | Vercel Cron | — | 200 | 401, 503 |

The legacy MVP routes (`/api/students`, `/api/posts`, `/api/responses`, mutation routes on `/api/tutors`) need demo mode, which is off on Vercel, so they return 403 in production.

### C6. JWT Authentication Design

**Figure 4: JWT sequence**

```mermaid
sequenceDiagram
  participant B as Browser (React)
  participant A as FastAPI
  participant D as Database
  B->>A: POST /api/auth/login {email, password}
  A->>D: count failures, load account, verify Argon2id(HMAC(pepper, pw))
  A->>D: INSERT refresh_sessions (hash, family, csrf hash)
  A-->>B: 200 {access_token, csrf_token} + Set-Cookie tutorinn_refresh (httpOnly), tutorinn_csrf
  B->>A: GET /api/dashboard  Authorization: Bearer AT
  A->>A: verify HS256 signature, iss, aud, exp, required claims
  A->>D: load account (exists, active) + session sid (not revoked, not expired)
  A-->>B: 200 data
  Note over B,A: 15 minutes later the access token has expired
  B->>A: GET /api/dashboard (expired AT)
  A-->>B: 401 Invalid or expired access token
  B->>A: POST /api/auth/refresh  cookie + X-CSRF-Token (single flight)
  A->>D: find session by token hash, check CSRF hash, revoke it, set replaced_by, INSERT new session (same family)
  A-->>B: 200 new AT + new cookies
  B->>A: retry GET /api/dashboard (new AT)
  A-->>B: 200
  Note over B,A: An attacker replays the old refresh token
  B->>A: POST /api/auth/refresh (old, already rotated token)
  A->>D: revoke every session in the family, log refresh_token_reuse
  A-->>B: 401 — all devices of that login must sign in again
  B->>A: POST /api/auth/logout  cookie + X-CSRF-Token
  A->>D: set revoked_at on the session
  A-->>B: 200 + cookies cleared (old AT now fails: session revoked)
```

**Table 24: Token claims**

| Claim | Value | Purpose |
|---|---|---|
| `sub` | account ID as a string | Which account |
| `role` | `student`, `tutor`, `admin` or `moderator` | Informational only; the role is re-read from the database |
| `sid` | refresh-session ID | Links the token to a session so that revocation and logout take effect immediately |
| `iss` / `aud` | `tutorinn` / `tutorinn-web` (from `JWT_ISSUER` / `JWT_AUDIENCE`) | Rejects tokens minted for another system |
| `iat` / `exp` | issue time / issue time + 15 minutes | Lifetime |
| `jti` | 16 random bytes, URL-safe | Unique token ID |

- **Algorithm and secret.** HS256 with `JWT_SECRET` from the environment; the server refuses to start authentication if the secret is shorter than 32 characters. Decoding accepts only HS256, so `alg: none` and algorithm-switching attacks fail.
- **Lifetimes.** Access tokens last 15 minutes (configurable 1–60): short enough that a stolen token is useful only briefly, long enough to avoid constant refreshes. Refresh tokens last 7 days (configurable 1–30) so a user who visits weekly stays signed in. Rotation and reuse detection limit the damage if one leaks.
- **Storage in the browser.** The access token lives only in a JavaScript module variable (lost on reload, never in `localStorage`), so an XSS payload cannot read it from storage. The refresh token is in an httpOnly cookie that JavaScript cannot read, scoped to `/api/auth`, `SameSite=Lax`, and `Secure` on Vercel (the API refuses to run with insecure cookies in production). CSRF is handled with a double-submit token: the readable `tutorinn_csrf` cookie must be echoed in `X-CSRF-Token`, and the server compares it with the hash stored for that session. XSS risk is further reduced by a strict Content-Security-Policy (`script-src 'self'`) and by React's output escaping.
- **Checks on every request** (`get_current_account`): a bearer header is present; signature, algorithm, issuer, audience, expiry and all required claims are valid; the account still exists; the session in `sid` belongs to that account, is not revoked and has not expired; and the account status is `active`. Failures return 401, except an inactive account, which returns 403.
- **Frontend on a 401.** `api.ts` calls `refreshSessionOnce()` — a single shared promise, so parallel requests cannot rotate the same token twice — and repeats the original request once. If the refresh fails or the retry is still 401, it clears the token and the account state and the user is shown the login page.
- **Password hashing.** `hash_password` computes `HMAC-SHA256(PASSWORD_PEPPER, password)` and hashes that with Argon2id (unique salt per hash). Older hashes without the pepper are still accepted and are upgraded on the next successful login.

### C7. RBAC Design

**Figure 5: Authorisation flow for one request** (example: `POST /api/groups/7/tasks`)

```mermaid
flowchart TD
  A[Request arrives] --> B{Bearer token valid?<br/>signature, iss, aud, exp}
  B -- no --> E401[401 + access_token_rejected]
  B -- yes --> C{Account exists, session active,<br/>status = active?}
  C -- session revoked/expired --> E401b[401]
  C -- banned/suspended --> E403a[403 + blocked_inactive_account]
  C -- yes --> D{Role check<br/>require_roles student, tutor}
  D -- no --> E403b[403 + access_denied]
  D -- yes --> F{Group exists and visible?}
  F -- no --> E404[404]
  F -- yes --> G{Caller is owner?}
  G -- yes --> H[Handler runs]
  G -- no --> I{Caller is a member?}
  I -- no --> E404b[404 hides the group]
  I -- yes --> J{member.can_create_tasks?}
  J -- no --> E403c[403 permission not enabled]
  J -- yes --> H
  H --> K[Commit + record_activity_event]
```

**Roles and permission constants**

- Roles: `student`, `tutor`, `admin`, `moderator`; flag `is_first_admin`.
- Admin capabilities (`ADMIN_PERMISSION_MATRIX`): `view_dashboard`, `view_users`, `manage_accounts`, `manage_admin_roles`, `view_tutors`, `manage_tutor_verification`, `view_activity`, `view_security`, `export_data`, `manage_retention` (admin only); `view_requests`, `view_tasks`, `delete_tasks`, `view_groups`, `delete_groups`, `moderate_learning` (admin and moderator).
- Group permissions: `can_create_tasks`, `can_edit_tasks`, `can_assign_tasks`.

**The reusable check** (`backend/app/auth.py`):

```python
def require_roles(*roles: str) -> Callable:
    def role_dependency(
        request: Request,
        account: UserAccount = Depends(get_current_account),
        db: Session = Depends(get_db),
    ) -> UserAccount:
        if account.role not in roles:
            record_security_event(
                db, "access_denied", request, account_id=account.id,
                details=f"Required role: {', '.join(roles)}; current role: {account.role}",
            )
            raise HTTPException(status_code=403,
                                detail="You do not have permission to perform this action.")
        return account
    return role_dependency
```

A route declares it once, for example `account: UserAccount = Depends(require_roles("tutor"))`. Admin routes use `require_admin_permission("export_data")`, which calls `require_roles("admin", "moderator")` and then looks the capability up in the matrix.

**Ownership in queries.** Private records are looked up with the owner in the `WHERE` clause, so a record that belongs to someone else is never loaded:

```python
task = db.scalar(select(PersonalLearningTask).where(
    PersonalLearningTask.id == task_id,
    PersonalLearningTask.owner_account_id == account.id))
if task is None:
    raise HTTPException(status_code=404, detail="Personal task not found.")
```

Tutoring requests are filtered by `(author_profile_type, author_profile_id)` of the caller's own profile, sessions by `account_id`, and assignments by `student_account_id`. Returning 404 rather than 403 avoids confirming that another user's record exists.

**Adding a new role or permission.** For a new admin capability: add a key to `ADMIN_PERMISSION_MATRIX` with the roles that hold it and protect the route with `require_admin_permission("<key>")`; an unknown key raises an error at import time, so typos are caught immediately. For a new role: add it to the `role` validation patterns, give it entries in the matrix or `require_roles(...)` lists, add navigation in `SiteHeader.tsx` and `AppLayout.tsx`, and add allowed and denied tests. For a new group permission: add a boolean column with a migration, add it to `GroupMemberPermissions`, and call `_can(group, account, db, "can_<name>")` in the route.

**Special rules for admins and banned users**

- Admins cannot change their own status, cannot moderate other admins, cannot revoke their own admin role, and cannot demote the last active admin. Only the First Admin can grant the admin role, and the First Admin cannot be suspended, demoted or deleted (checked in code and by a database trigger).
- Role changes revoke all of the target's sessions, so a demoted admin loses access on the next request.
- A banned or suspended user is rejected with 403 by `get_current_account` on the next request, even with an unexpired token, because the status is read from the database each time; their refresh sessions are revoked when the ban is applied, and any refresh attempt by an inactive account revokes the whole family.

### C8. Admin Dashboard Design

**Figure 6: Admin pages and endpoints**

```mermaid
flowchart LR
  AR["/admin tabs (AdminReviewPage)"]
  AR --> O["Overview"] --> E1["GET /api/admin/overview"]
  AR --> U["Students / Tutors / Admins / Moderators"] --> E2["GET users, users/{id}; PATCH status; bulk-status; admin-role; sessions"]
  AR --> TV["Tutors"] --> E3["GET tutors; PATCH verification; bulk-verification"]
  AR --> RQ["Requests and tutor interest"] --> E4["GET requests; remove; bulk-remove; interest-responses"]
  AR --> TK["Tasks / Groups"] --> E5["GET/DELETE tasks, group-tasks, groups, bulk"]
  AR --> AC["Activity"] --> E6["GET activity; export/activity"]
  AR --> SC["Security"] --> E7["GET security"]
  AR --> DC["Decisions"] --> E8["GET decisions"]
  REP["/admin/reports"] --> E9["GET/PATCH reports"]
  SUB["/admin/subjects"] --> E10["subjects CRUD"]
  DEL["/admin/deletions"] --> E11["account-deletion-requests"]
  PR["/admin/password-resets"] --> E12["password-reset-requests"]
  FT["/admin/first-admin-transfer"] --> E13["first-admin-transfer"]
```

All endpoint labels are relative to `/api/admin/`.

**Table 25: Admin pages**

| Page / tab | Endpoints | Filters and pagination | Actions | Audit events written |
|---|---|---|---|---|
| Overview | `GET /api/admin/overview` | — | — | — |
| Students, Tutors, Admins, Moderators | `GET /api/admin/users`, `/users/{id}` | q, status, created date range; offset/limit (25 per page, max 100); state kept in the URL | Inspect, ban, suspend, reactivate, bulk status, revoke a session, grant/revoke admin | `admin_user_inspected`, `admin_account_status_changed`, `admin_bulk_account_status_changed`, `admin_account_session_revoked`, `admin_admin_role_granted`, `admin_admin_role_revoked` |
| Tutors (verification) | `GET /api/admin/tutors`, `PATCH …/verification`, `POST …/bulk-verification` | q, verification status, pagination | Approve, reject, with note | `admin_tutor_verification_changed` |
| Requests and tutor interest | `GET /api/admin/requests`, `POST …/remove`, `…/bulk-remove`, interest-response review | q, status, dates, pagination | Remove one or many requests (reason + confirm), approve/reject interest | `admin_request_removed` per item; `admin_interest_approved` / `admin_interest_rejected` |
| Tasks, Groups | `GET /api/admin/tasks`, `/group-tasks`, `/groups`; DELETE single and `/bulk` | scope (personal/group), owner account, q, dates, pagination | Delete one or many with reason and confirmation | one `admin_personal_task_deleted`, `admin_group_task_deleted` or `admin_learning_group_deleted` event per removed item |
| Activity | `GET /api/admin/activity`, `GET /api/admin/export/activity` | event type, account ID, text, date range, pagination, optional auto-refresh | Export CSV; First Admin: purge old counters | `admin_data_exported`, `admin_activity_retention_cleanup` |
| Security | `GET /api/admin/security` | time window (1–720 h), minimum events, event type, account, text | Links to the user detail and the filtered activity log | — |
| Decisions | `GET /api/admin/decisions` | type, dates | Read the history of moderation decisions | — |
| Reports | `GET/PATCH /api/admin/reports` | status | Resolve or dismiss with note | `admin_report_<status>` |
| Subjects | `/api/admin/subjects` | — | Add, rename, deactivate, delete if unused | `admin_subject_created`, `admin_subject_updated`, `admin_subject_deleted` |
| Account deletions | `/api/admin/account-deletion-requests` | status | Approve (complete or anonymise) or reject | `admin_account_deletion_*` (e.g. `admin_account_deletion_rejected`) |
| Password resets | `/api/admin/password-reset-requests` | status | Approve or reject | reviewer decision recorded in the request row and the activity log |
| First Admin transfer | `/api/admin/first-admin-transfer` | — | Start, cancel, accept, decline | `first_admin_transfer_started`, `_cancelled`, `_accepted`, `_declined`, `_password_failed` |

**Bulk actions.** Each bulk endpoint accepts 1–50 unique IDs (group/task bulk deletes also need `confirm: true` and a reason). Every ID is processed separately and the response lists, per ID, `success: true` or the error (for example "Admin accounts cannot be bulk moderated."), plus `succeeded` and `failed` totals. Only the successful items are audited, one event each, so the activity log matches what actually changed.

**CSV export and filters.** The Export button sends the screen's current filter values (q, role, status, account, owner, scope and date range) to `GET /api/admin/export/{kind}`, which builds the same SQL query as the list endpoint, without pagination but capped at 10,000 rows. Cells that begin with `=`, `+`, `-`, `@`, tab or carriage return are prefixed with `'` to stop spreadsheet formula injection; the file starts with a UTF-8 BOM so Excel opens it correctly; the header `X-Export-Limit-Reached` tells the admin if the cap cut the result; and each export is audited with its filters and row count.

### C9. Security Design and Threats

**Table 26: Threats and defences**

| Threat | Defence | File or module |
|---|---|---|
| Password database leak | Argon2id (64 MiB, t=3) with a unique salt per hash, applied to an HMAC-SHA256 with a pepper that lives only in the environment; minimum 12-character passwords | `auth.py` `hash_password`; `schemas.py` |
| Stolen access token | 15-minute lifetime; kept only in memory; tied to a session (`sid`) so logout, ban or revocation stops it immediately | `auth.py` `create_access_token`, `get_current_account` |
| Stolen refresh token | httpOnly, Secure, path-scoped cookie; only its hash is stored; rotation on every use; reuse revokes the whole family; CSRF token bound to the session | `routers/auth.py` `refresh_session` |
| Brute-force login | 5 failures per email in 15 minutes → 429; per-IP limits on login (30/15 min), registration and refresh (30/min); events visible in the security view | `auth.py` `enforce_auth_rate_limit`, `failed_login_count` |
| Privilege escalation | Role and status read from the database, not the token; registration can only create student/tutor; only the First Admin can grant admin; admin self-protection rules; role changes revoke sessions | `auth.py`, `routers/admin.py` |
| Access to another user's record | Owner ID in every query; 404 for foreign records; private profile fields excluded from public schemas | `routers/tasks.py`, `beta_requests.py`, `groups.py`, `schemas.py` |
| Cross-site scripting | React escapes output; no `dangerouslySetInnerHTML` for user content; strict CSP (`script-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`); video links shown as plain links, never embedded | `main.py` `security_headers` |
| Cross-site request forgery | Protected API calls use a bearer header that a forged form cannot add; cookie-based refresh and logout need the double-submit CSRF token; `SameSite=Lax` cookies | `routers/auth.py` `_require_csrf` |
| CORS misuse | CORS is off for same-origin deployment; when set, `TRUSTED_ORIGINS` must be exact http(s) origins without wildcards, paths or queries | `main.py` `parse_trusted_origins` |
| Secrets in the repository | `.env` ignored by Git; `.env.example` holds placeholders; secrets set in Vercel's environment settings; GitHub secret scanning; no credentials in Markdown | `.gitignore`, `backend/.env.example` |
| SQL injection | All queries built with SQLAlchemy expressions and bound parameters; `LIKE` wildcards in search are escaped | all routers |
| Over-posting of fields | Pydantic input models list only the fields a user may set; owner, role and status come from the token and database, never from the body | `schemas.py`; `test_profile_updates_reject_client_supplied_identity_and_stay_self_scoped` |
| Clickjacking and sniffing | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, HSTS in production | `main.py` |
| Information leakage in errors and logs | Generic 500 handler; generic login and reset messages; secrets and JWT-shaped strings redacted before events are stored; per-IP write cap on noisy events | `main.py`, `auth.py` `_safe_log_text` |
| Direct database access through Supabase | RLS enabled on all public tables with no browser policies; `anon`/`authenticated` grants revoked | `supabase/migrations/*secure*` |

### C10. Deployment on Vercel

**Figure 7: Deployment layout**

```mermaid
flowchart TB
  GH["GitHub repository"] -- "push / PR" --> VP
  subgraph VP["Vercel project (vercel.json services)"]
    FE["frontend service<br/>root: frontend<br/>npm run build to dist/<br/>SPA rewrite to /index.html"]
    BE["backend service<br/>root: backend<br/>framework: fastapi<br/>entrypoint: app.main:app"]
    CR["Cron: 0 3 * * *"]
  end
  U["User browser"] --> RW{"Top-level rewrites"}
  RW -- "/api/*" --> BE
  RW -- "everything else" --> FE
  CR --> BE
  BE -- "DATABASE_URL / POSTGRES_URL" --> SB[("Supabase PostgreSQL")]
```

- **Projects.** TutorInn uses one Vercel project, `2111584-tutorinn`, whose `vercel.json` declares two services: `backend` (FastAPI, entry point `app.main:app`) and `frontend` (Rspack build, output `dist`). Every push to a branch creates a preview deployment, and the production deployment at https://2111584-tutorinn.vercel.app is built from `main`.
- **Build settings and rewrites.** The frontend build runs `npm run build` (`tsc --noEmit && rspack build`). Top-level rewrites send `/api/*` to the backend and everything else to the frontend, where an SPA rewrite returns `index.html`.
- **How the frontend finds the API.** It calls relative paths (`/api/...`), so the frontend and the API share one origin. No API URL is baked into the bundle, CORS is not needed and the cookies are first-party.
- **Database.** Supabase PostgreSQL through `DATABASE_URL` (falling back to `POSTGRES_URL`). On Vercel the app refuses to fall back to SQLite. Schema changes are applied as reviewed SQL migrations in `supabase/migrations/`, which CI replays on an empty PostgreSQL 17 database.
- **Redeploying.** Push to `main` (or merge a PR) to trigger a production build; use "Redeploy" on a deployment in the Vercel dashboard to rebuild the same commit, for example after changing an environment variable. Environment variable changes only apply to new deployments.

**Table 27: Environment variables** (names only; values are set in Vercel and never committed)

| Name | Purpose |
|---|---|
| `DATABASE_URL` / `POSTGRES_URL` | PostgreSQL connection string |
| `JWT_SECRET` | HS256 signing key (≥ 32 characters) |
| `PASSWORD_PEPPER` | HMAC key mixed into password hashes (≥ 32 characters) |
| `JWT_ISSUER`, `JWT_AUDIENCE` | Expected `iss` and `aud` claims |
| `ACCESS_TOKEN_MINUTES`, `REFRESH_TOKEN_DAYS` | Token lifetimes (15 and 7 by default) |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | Cookie flags (Secure is forced on Vercel) |
| `LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES` | Per-account lockout |
| `LOGIN_IP_MAX_ATTEMPTS`, `LOGIN_IP_WINDOW_SECONDS`, `REFRESH_MAX_ATTEMPTS`, `REFRESH_WINDOW_SECONDS` | Per-IP rate limits (optional, have defaults) |
| `PASSWORD_RESET_*`, `EMAIL_VERIFICATION_*`, `FIRST_ADMIN_TRANSFER_*` (`_MAX_ATTEMPTS`, `_WINDOW_SECONDS`) | Rate limits for those workflows |
| `SECURITY_EVENT_MAX_PER_MINUTE` | Cap on noisy event writes per IP |
| `ENVIRONMENT`, `ENABLE_DEMO_MODE` | Production flag; legacy demo routes (off on Vercel) |
| `TRUSTED_ORIGINS`, `FRONTEND_ORIGIN` | Optional exact CORS origins |
| `CRON_SECRET` | Bearer secret checked by the retention route |
| `ACTIVITY_RETENTION_DAYS` | Age after which rate-limit counters are deleted (default 90) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `PUBLIC_APP_URL` | Optional email delivery |
| `DEMO_PASSWORD` | Used only by the demo seed script, never by the running app |

### C11. Testing

**Strategy.**
1. *Automated API tests* (pytest, more than 200 test functions) call the real FastAPI app with `TestClient` against a fresh SQLite database per test. They cover authentication, token tampering and expiry, refresh rotation and reuse, CSRF, sessions, lockout, ownership, the group permission matrix, admin rules, moderation, exports, retention, deletion workflows, error shapes, security headers, CORS and deployment configuration.
2. *PostgreSQL tests in CI:* critical account-deletion workflows run against a real PostgreSQL service, and every Supabase migration is replayed in order on an empty database with RLS and grant checks.
3. *Frontend tests* (Node test runner, more than 60 tests) check the API client, dashboard, admin views, groups, personal tasks and First Admin transfer logic; `tsc --noEmit` and the production build run as part of CI.
4. *Dependency audits:* `pip-audit` and `npm audit --audit-level=high`.
5. *Manual tests on the live site:* each flow in Part D is repeated on the Vercel URL with the demo accounts, using the browser developer tools to check headers, cookies and status codes.

**How to run**

```bash
# backend (from backend/)
pip install -r requirements-dev.txt
pytest -q

# frontend (from frontend/)
npm ci
npm test
npm run build
```

**Table 28: Tests and results** (key tests; full output in S21). Results are from the final GitHub Actions run on `main`, where the `backend-tests`, `supabase-migration-chain`, `frontend-build` and `dependency-audit` jobs all passed.

| Test | Requirement | Result |
|---|---|---|
| `test_expired_access_tokens_are_rejected` | FR-AUTH-05 | Pass |
| `test_invalid_and_tampered_access_tokens_are_rejected` | FR-AUTH-05 | Pass |
| `test_jwt_rejects_wrong_issuer_audience_and_unsupported_algorithm` | FR-AUTH-05 | Pass |
| `test_refresh_rotation_reuse_detection_revokes_entire_session_family` | FR-AUTH-07 | Pass |
| `test_refresh_rejects_missing_or_mismatched_csrf_token` | FR-AUTH-08 | Pass |
| `test_logout_revokes_access_session_and_clears_auth_cookies` | FR-AUTH-09 | Pass |
| `test_account_cannot_revoke_another_accounts_session` | FR-AUTH-10 | Pass |
| `test_repeated_failed_logins_trigger_temporary_lockout` | FR-AUTH-11 | Pass |
| `test_password_change_verifies_current_password_and_revokes_all_sessions` | FR-AUTH-13 | Pass |
| `test_authenticated_request_ownership_and_role_enforcement` | FR-RBAC-02/03 | Pass |
| `test_task_ownership_isolated_between_student_and_tutor` | FR-RBAC-03 | Pass |
| `test_each_member_permission_is_independent_and_enforced` | FR-RBAC-05 | Pass |
| `test_member_permissions_are_enforced_and_owner_controls_group_tasks` | FR-RBAC-04/05 | Pass |
| `test_student_sees_only_own_assignments_and_can_update_only_own_completion` | FR-RBAC-06/07 | Pass |
| `test_admin_cannot_moderate_self_or_another_admin_and_ban_revokes_existing_access` | FR-RBAC-08/10 | Pass |
| `test_ordinary_admin_cannot_grant_admin_role` | FR-RBAC-09 | Pass |
| `test_other_admins_and_moderators_cannot_suspend_or_demote_the_first_admin` | FR-RBAC-09 | Pass |
| `test_suspended_account_cannot_use_existing_access_or_refresh_session` | FR-RBAC-10 | Pass |
| `test_admin_bulk_moderation_reports_partial_failures_and_enforces_limit` | FR-ADM-07 | Pass |
| `test_user_export_contains_only_rows_matching_the_active_search_filter` | FR-ADM-12 | Pass |
| `test_spreadsheet_formulas_are_neutralized_in_exported_cells` | FR-ADM-12 | Pass |
| `test_automatic_activity_retention_removes_only_rate_limit_counters_and_keeps_login_history` | FR-ADM-13 | Pass |
| `test_admin_ban_role_change_delete_and_export_record_actor_affected_account_and_context` | G-06 | Pass |
| `test_supabase_migration_chain.py` (CI PostgreSQL job) | NFR-REL-02 | Pass |
| Frontend suite (`npm test`) and `npm run build` | NFR-MNT-02 | Pass |

---

## Part D. Evidence: Screenshots of the Running Application

All screenshots were taken on the deployed site (https://2111584-tutorinn.vercel.app) using the demo accounts listed in the Appendix. Token and cookie values are masked; the browser tab strip is cropped. IP addresses shown are those of the network used during testing.

### D1. User Side

**S1. Sign-up validation and generic login error** (FR-AUTH-01, FR-AUTH-03)

![S1a: Registration rejects a short password](../images/S01a.png)

![S1b: Login shows a generic error](../images/S01b.png)

*S1: The server enforces the password rules (minimum 12 characters, with a strength indicator), and a failed login shows "Invalid email or password." without revealing whether the account exists.*

**S2. Student dashboard and tutor discovery** (FR-RBAC-03, FR-DOMAIN-01, FR-DOMAIN-02)

![S2a: Student dashboard for demo-student-1](../images/S02a.png)

![S2b: Discover tutors filtered by Physics, HSC and 2+ years](../images/S02b.png)

*S2: A student sees only their own tutoring requests, and the discovery filters (subject, level, minimum experience) return matching tutors.*

**S3. Profile and password change** (FR-AUTH-12, FR-AUTH-13)

![S3: Change password with a wrong current password](../images/S03.png)

*S3: The profile is self-scoped, and a password change is refused with "Current password is incorrect." when the current password is wrong.*

**S4. Active sessions with revoke actions** (FR-AUTH-09, FR-AUTH-10)

![S4: Active sessions on the profile page](../images/S04.png)

*S4: Users can see each signed-in device, with the current session marked, and log out one device, other devices or everywhere.*

**S5. Group members, permissions and an assigned task** (FR-RBAC-04, FR-RBAC-05, FR-DOMAIN-06–08)

![S5a: Demo Shared Group members and their permissions](../images/S05a.png)

![S5b: Group task with a Google Drive link, assigned to both members](../images/S05b.png)

*S5: The group owner (demo-tutor-1) controls each member's create/edit/assign permissions and assigns a task with a Drive video link to all members (2 assigned).*

**S6. Action denied by RBAC** (FR-RBAC-02, FR-RBAC-05)

![S6a: demo-student-2 sees that it has no group permissions](../images/S06a.png)

![S6b: POST /api/groups/1/tasks returns 403](../images/S06b.png)

*S6: demo-student-2 has no permissions in the group; the page explains this, and the server refuses a direct task-creation request with 403 "The group owner has not enabled permission: create tasks."*

### D2. Security Behaviour

**S7. Bearer token and rejected tampered token** (FR-AUTH-04, FR-AUTH-05)

![S7a: GET /api/auth/me with a valid Bearer token returns 200](../images/S07a.png)

![S7b: The same call with an edited token returns 401](../images/S07b.png)

*S7: The access token travels in the `Authorization: Bearer` header; a tampered token is rejected with 401 "Invalid or expired access token."*

**S8. Refresh rotation and the httpOnly cookie** (FR-AUTH-06, FR-AUTH-07, FR-AUTH-08)

![S8a: POST /api/auth/refresh with X-CSRF-Token returns 200](../images/S08a.png)

![S8b: The refresh response contains a new access_token](../images/S08b.png)

![S8c: tutorinn_refresh cookie flags](../images/S08c.png)

*S8: The refresh call needs the CSRF header and returns a new 15-minute access token; the refresh token lives in the `tutorinn_refresh` cookie with HttpOnly, Secure, SameSite=Lax and Path=/api/auth, so JavaScript cannot read it.*

**S9. Banned user rejected** (FR-RBAC-10)

![S9: Admin window shows the account banned; the user's login returns 403](../images/S09.png)

*S9: After an admin bans demo-student-2 (right), the account's sessions are revoked and its next login is refused with 403 "This account is suspended or inactive." (left).*

### D3. Admin Dashboard

**S10. Overview statistics** (FR-ADM-01)

![S10a: Admin overview statistic cards](../images/S10a.png)

![S10b: Moderation cards and 7-day trends](../images/S10b.png)

*S10: The admin overview shows live platform totals, moderation counts and 7-day registration and request trends.*

**S11. User list with search, filters and pagination** (FR-ADM-02)

![S11: Students tab with search "demo", status active and pagination](../images/S11.png)

*S11: Admins can search, filter by status and page through accounts.*

**S12. Account detail with sessions and activity** (FR-ADM-03, FR-ADM-06)

![S12a: Account details with active sessions and Revoke session buttons](../images/S12a.png)

![S12b: Recent activity for the account](../images/S12b.png)

*S12: Admins can inspect an account's profile, records and devices, revoke individual sessions, and review its recent activity.*

**S13. Ban dialog and banned state** (FR-ADM-04, FR-RBAC-08)

![S13a: Ban dialog with a reason](../images/S13a.png)

![S13b: demo-student-2 shown as banned](../images/S13b.png)

*S13: A ban requires a written reason, which is stored in the audit trail, and the account's status changes to banned.*

**S14. Bulk moderation** (FR-ADM-07, FR-ADM-09)

![S14a: Bulk account moderation dialog for two selected students](../images/S14a.png)

![S14b: Bulk action result](../images/S14b.png)

*S14: Admins select several accounts, give a reason, and the bulk action reports each result separately ("2 succeeded, 0 failed").*

**S15. Activity log with filters** (FR-ADM-10)

![S15a: Activity filtered to today](../images/S15a.png)

![S15b: Activity filtered to account 5 (demo-student-2)](../images/S15b.png)

*S15: The audit trail records the actions shown above, including admin_bulk_account_status_changed and blocked_inactive_account, and can be filtered by date and account.*

**S16. Security view** (FR-ADM-11, FR-AUTH-11)

![S16: Security incidents grouped by source IP and by account](../images/S16.png)

*S16: Admins can spot repeated failures by source IP and by account.*

**S17. CSV export** (FR-ADM-12)

![S17: Filtered users CSV opened in Excel](../images/S17.png)

*S17: The export contains only the rows that match the active filter.*

### D4. Deployment

**S18. Vercel production deployment** (NFR-REL-01)

![S18: Vercel project overview](../images/S18.png)

*S18: The production deployment from `main` is Ready on 2111584-tutorinn.vercel.app.*

**S19. Environment variables with values hidden** (NFR-SEC-01)

![S19: Vercel environment variables](../images/S19.png)

*S19: Secrets such as PASSWORD_PEPPER, CRON_SECRET and POSTGRES_URL are kept in Vercel, with values hidden, not in the repository.*

**S20. Live API documentation** (C5)

![S20: Swagger UI at /api/docs](../images/S20.png)

*S20: The API documentation (TutorInn API 2.3.0) is available on the deployed site.*

### D5. Tests

**S21. Automated test results** (C11)

![S21a: GitHub Actions run on main with all jobs green](../images/S21a.png)

![S21b: backend-tests summary line](../images/S21b.png)

*S21: backend-tests, supabase-migration-chain, frontend-build and dependency-audit all pass on `main`; the backend suite reports 216 passed, 1 skipped.*

---

## Part E. Project Management and Conclusion

### E1. How to Run and Test

**Prerequisites:** Git, Python 3.10 or newer (CI uses 3.12), Node.js 22 with npm. PostgreSQL is not needed locally: with `DATABASE_URL` left empty the API uses the SQLite file `backend/tutorinn.db`.

**1. Clone the repository**

```bash
git clone https://github.com/almahmudshafin20/2111584-TutorInn.git
cd 2111584-TutorInn
```

**2. Create the backend environment file.** Run `python backend/scripts/setup_local_env.py` from the repository root. It writes `backend/.env` from `.env.example` with freshly generated secrets and never prints them. (Alternative: copy `backend/.env.example` to `backend/.env` and replace each `CHANGE_ME` value.) The important names, with example local values:

```text
DATABASE_URL=                        # empty = local SQLite file backend/tutorinn.db
JWT_SECRET=<48+ random characters>   # python -c "import secrets; print(secrets.token_urlsafe(48))"
PASSWORD_PEPPER=<another 48+ random characters>
JWT_ISSUER=tutorinn
JWT_AUDIENCE=tutorinn-web
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
LOGIN_MAX_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15
```

**3. Start the backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
fastapi dev app/main.py --env-file .env
```

The API runs at http://localhost:8000 and the Swagger UI at http://localhost:8000/api/docs. The tables are created automatically on first start.

**4. Create local test accounts.** In a second terminal inside `backend/`, with the virtual environment active, run the demo seed script against the same local database. Use the same `PASSWORD_PEPPER` as in `backend/.env`, and choose any demo password of at least 12 characters:

```bash
PASSWORD_PEPPER=<value from backend/.env> DEMO_PASSWORD=<demo password> python -m scripts.seed_demo_accounts
# Windows PowerShell:
#   $env:PASSWORD_PEPPER="<value>"; $env:DEMO_PASSWORD="<demo password>"; python -m scripts.seed_demo_accounts
```

It creates 2 Admin, 1 Tutor and 2 Student accounts and the group *Demo Shared Group*. You can also register Student and Tutor accounts on the `/register` page. (`scripts/create_first_admin.py` is only for the hosted PostgreSQL database; it refuses to run against SQLite.)

**5. Start the frontend** (third terminal)

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. The Rspack dev server forwards `/api` requests to FastAPI on port 8000.

**6. Run the tests**

```bash
cd backend && pytest -q
cd ../frontend && npm test && npm run build
```

**7. Log in on the live site.** The deployed site has demo accounts for two role groups: **Admin** (two accounts) and **normal users** (one Tutor and two Students, plus *Demo Shared Group*). Their user IDs and passwords are only in the Appendix of the PDF report, never in this file or anywhere in the repository.

### E2. GitHub Work

**How the work was done.** This was an individual project. Every commit in the repository is recorded under my name (Al Mahmud Shafin, 2111584@iub.edu.bd), but most of the code was written by AI tools working from my instructions: about 90% by ChatGPT and about 10% by Claude. I decided what to build and what to change, wrote the instructions, checked the results and asked for fixes. For example, I gave every topic and checklist item in the Beta roadmap (Issue #41), and the content rules for `README.md` and `AGENTS.md`. I also gave instructions on design details ("this colour is not needed", "add this function").

1. **Pull requests and authorship.** I created the early pull requests myself (roughly the first ten, from the documentation and MVP stage, before the Beta task). Later pull requests were mostly opened by the AI tools from my instructions. A few pull requests had problems, so I closed them and deleted their branches.
2. **AI share of the work.** About 90% of the code and text was produced with ChatGPT and about 10% with Claude. Every change came from my instruction: what to add, what to remove and what to correct.
3. **Starting early.** I knew the final task would be long, so I started before the faculty gave the Beta assignment. I built some basic features first. My first pull requests for this failed, so I created new ones with the basic features. When the faculty gave the main task, I added its requirements on top.
4. **Live checking.** I tested the deployed site on Vercel myself, found where it was broken, and told the AI what to fix. ChatGPT did most of the deployment fixes; Claude helped several times, especially when ChatGPT could not solve a problem.
5. **Milestone pull requests #42–#45.** These were the hardest part. Some I opened myself and some the AI opened. I checked each one against its Issue #41 milestone checkboxes and corrected the titles, including ones where I had given the wrong title myself.

**Table 29: Issues and pull requests**

| Period | Issue / PR | Title | What it delivered |
|---|---|---|---|
| 13–14 Oct | Issue #1 → PR #2; PRs #4, #6, #7 | Project documentation | First PRD, SRS and TDD; MVP/Beta plan; project title |
| 19 Oct | Issues #9, #10 → PRs #20, #21 | Core data models | Student, Tutor and request models, validation and model tests |
| 31 Oct | Issue #22 → PR #23; PRs #25, #26 | Student/Tutor CRUD; API docs routing | MVP CRUD screens and APIs; Swagger served under `/api/docs` |
| 8 Nov | Issue #27 → PR #28; Issue #29 → PR #30; PRs #32, #34 | Profile ownership, interests, multi-subjects; post-MVP refactor; fixes | Interested/Not Interested responses, admin review queue, multiple subjects, render-crash and numbering fixes |
| 9–11 Nov | PR #36; Issue #38 → PR #39 | Admin-approved matching; development guidelines | Private contact details shown only after approval; `AGENTS.md` rules |
| 14 Nov | Issue #41 (roadmap) → PR #42 | Milestone 0: modular frontend and backend | Pages/components/API modules; domain routers |
| 15–19 Nov | PR #43 | Milestones 1–3: authentication, profiles, dashboards | JWT + refresh rotation, Argon2id + pepper, sessions, lockout, profile ownership, Student/Tutor dashboards, requests and responses |
| 16–19 Nov | PR #44 | Milestones 4–5: personal tasks, groups, assignments | Personal tasks with filters and summaries; learning groups, member permissions, assignments, Drive video links |
| 16–20 Nov | PR #45 | Milestones 6–8: admin, security, deployment | Admin dashboard, moderation, bulk actions, activity/security views, CSV export, retention, account deletion, password-reset queue, First Admin transfer, migration-chain CI, Vercel configuration, demo seed |

All pull requests in Table 29, including the milestone pull requests #42–#45, are merged into `main`. Issue #41 (the Beta roadmap) and the other feature issues are closed, and the production site is deployed from `main`.

### E3. Limitations

- **Email delivery is not configured in production.** SMTP variables are not set on Vercel, so verification, password-reset and deletion-outcome emails are not sent. Because a password reset needs a verified email, the self-service reset cannot be completed on the live site; an admin has to follow up manually.
- **No way to assign the Moderator role.** Moderator permissions are enforced and tested, but the invitation and acceptance workflow for Admin and Moderator roles was not built.
- **Group lifecycle gaps.** The group API has no endpoint for an owner to delete their own group or for a member to leave; only admins can delete groups (through the admin dashboard), and only the owner can remove a member.
- **Backend layering.** The admin, groups and tasks routers contain their SQLAlchemy queries directly in the route handlers instead of a service/repository layer, so `admin.py` is over 2,000 lines.
- **IP-based signals.** Rate limits and the security view rely on the client IP reported by the platform. Users behind one NAT share a limit, and the IP is treated only as an investigation signal.
- **Timestamps as text.** Dates are stored as ISO-8601 strings rather than `timestamptz`, which works for ordering in UTC but is weaker for database-side date arithmetic.
- **Security not covered:** no two-factor authentication, no CAPTCHA after repeated failures, no email verification required at sign-up, and no automated end-to-end browser tests against the live site.
- **Legacy MVP code.** The old demo-profile routes remain in the codebase (disabled on Vercel), which adds code to maintain.

### E4. Future Work

1. **Configure SMTP on Vercel and test the email flows** — unblocks password reset, email verification and deletion notifications.
2. **Add owner delete-group and member leave-group endpoints and buttons** — closes the main gap in the group lifecycle.
3. **Build the Admin/Moderator invitation workflow** — makes the existing Moderator role usable without database access.
4. **Move admin, group and task queries into service modules** — smaller files and easier testing.
5. **Add optional TOTP two-factor authentication for admins** — admin accounts hold the most power.
6. **Add Playwright end-to-end tests against preview deployments** — catch UI regressions that API tests cannot.

### E5. Sources, Libraries and Tools

**Table 30: Libraries, services and references**

| Name | Version or link | Used for |
|---|---|---|
| FastAPI (`fastapi[standard]`) | ≥ 0.141.1 | Backend framework, dependencies, OpenAPI docs |
| Pydantic | v2 (installed with FastAPI) | Request/response validation |
| SQLAlchemy | ≥ 2.0.40 | ORM and query building |
| Alembic | ≥ 1.15.0 | Versioned migrations |
| psycopg (binary) | ≥ 3.2.6 | PostgreSQL driver |
| PyJWT | ≥ 2.10.1 | Access-token signing and validation |
| argon2-cffi | ≥ 23.1.0 | Argon2id password hashing |
| pytest, httpx | ≥ 8.0, ≥ 0.27 | Backend tests |
| React, React DOM | 19.3.0 | Frontend UI |
| TypeScript | 7.0.2 | Static typing |
| @rspack/core, @rspack/cli | 2.3.2 | Bundling and build |
| @rspack/dev-server, @rspack/plugin-react-refresh, react-refresh | 2.2.2, 2.0.2, 0.18.0 | Local dev server and hot reload |
| Python / Node.js | 3.12 / 22 (CI) | Runtimes |
| GitHub, GitHub Actions | github.com | Repository, issues, pull requests, CI, dependency audits |
| Vercel (Hobby plan) | vercel.com | Hosting, preview deployments, daily cron |
| Supabase | supabase.com | Hosted PostgreSQL database |
| pip-audit, npm audit | — | Dependency vulnerability checks |
| RFC 7519 (JWT), OWASP ASVS 4.0 and Cheat Sheets | rfc-editor.org, owasp.org | Token design and security requirements |
| Course template | github.com/sayef-reyadh-labs/smarter-todo | Report structure and requirement IDs |

Backend versions are the minimums in `backend/requirements.txt`; frontend versions are the exact ones locked in `frontend/package-lock.json`.

**AI tools**

| Tool | Share of the work | Parts it was used for |
|---|---|---|
| ChatGPT | About 85–90% | Most of the code, tests, documentation, pull requests and Vercel deployment fixes, from Milestone 0 to Milestone 8 |
| Claude | About 10% | Problems ChatGPT could not solve, especially in Milestones 6–8: the First Admin setup and protection, admin features, deployment checks, and drafting this report from the repository |

**How I directed and checked the AI work**

- I gave every requirement and change: the Issue #41 roadmap topics and checkboxes, the `README.md` and `AGENTS.md` rules, and UI corrections (colours to remove, functions to add).
- I tested the deployed site myself after changes, found where it failed and gave the AI the problem to fix.
- I checked that each pull request matched its milestone checkboxes, had the right title and contained only the intended work.

**Problems with the tools and how I handled them**

- **Too many pull requests.** ChatGPT sometimes opened several pull requests at once. I told it to stop creating new ones, then went through them to decide what each was for, its title and its checkboxes. I closed and deleted the ones that were wrong.
- **Wrong answers.** Some AI changes did not match the checkboxes or broke the site. I compared them with the milestone checklist and the live site, and asked for corrections.
- **Vercel deployment limit.** Many small commits each started a deployment, and Vercel's free Hobby plan allows 100 deployments per day, including previews. When I reached the limit, deployments stopped for about 24 hours.
- **ChatGPT free plan.** At first I used the free plan, so I had to start new chats often and explain the project context again.

---

## Appendix. Test Accounts, Roles and Video Demo

**Video demo** (about 11 minutes, recorded on the deployed Vercel site): https://youtu.be/EtYkuMW_a5Y

**Test accounts.** The site has five demo accounts: two Admins, one Tutor and two Students, plus the group *Demo Shared Group* with mixed member permissions. Their user IDs, passwords and what each account can and cannot do are listed **only in the PDF version of this report**. They are deliberately left out of this Markdown file and the whole repository, because GitHub flags committed credentials.

**Shared group with mixed permissions**

| Group | Owner | Member | Create tasks | Edit tasks | Assign tasks |
|---|---|---|---|---|---|
| Demo Shared Group | Tutor demo account | Student demo account 1 | Yes | No | No |
| Demo Shared Group | Tutor demo account | Student demo account 2 | No | No | No |
