# TutorInn Beta — Milestones 4–5 Implementation Plan

> **Status:** Planning/documentation only. This document defines the implementation scope and acceptance criteria for Milestones 4 and 5 in Issue #41. It does not claim that either milestone has been implemented.

## Tracking

- Master roadmap: [Issue #41](https://github.com/almahmudshafin20/2111584-TutorInn/issues/41)
- Previous foundation: [PR #43 — Authentication, profiles and dashboards](https://github.com/almahmudshafin20/2111584-TutorInn/pull/43)
- Planning branch: `feat/44-personal-learning-tasks-group-assignments`
- Planning PR: [PR #44](https://github.com/almahmudshafin20/2111584-TutorInn/pull/44)
- PR #44 is intended to be stacked on `feat/43-auth-profiles-dashboards` because PR #43 is currently open and unmerged. Do not target `main` until the dependency is integrated.
- This is one combined Milestones 4–5 workstream and one PR. No separate implementation issue is created.

## Goals and implementation order

1. **Part 4 — Personal learning tasks:** deliver private, account-owned task CRUD and completion tracking first.
2. **Part 5 — Group learning and assignments:** let Tutors create/manage learning groups and assign learning tasks to their Student members, with per-student completion state and server-enforced permissions.
3. Reuse the authenticated account, role, ownership, API, database and UI foundations from PR #43. Do not rebuild authentication, profiles or tutoring requests.

---

## Part 4 — Personal learning tasks

### Functional scope

- Create a personal learning task.
- List and view only the authenticated account's own personal tasks.
- Update and delete an owned task.
- Mark a task complete or incomplete.
- Store and expose task category, optional description, optional due date and completion state.
- Support filtering/searching by text, category (including uncategorized) and status (open, completed, overdue).
- Show useful empty, loading, validation and error states.
- Provide task summary counts for open, completed and overdue items using the same status rules as the task list.
- Keep search/filter state in URL query parameters where appropriate, without putting private task content or identifiers into shareable URLs.
- Support the `/` search-focus shortcut only when the user is not typing in an input, textarea or editable control.

### Data and API design considerations

- Inspect the current models, migrations, routers, schemas, CRUD functions and frontend API/types before deciding whether a new table or existing structure should be extended.
- Associate every personal task with the authenticated account on the server. Never accept the owner/account ID as an authorization claim from the browser.
- A task should have a stable ID, title, optional description, optional category, optional due date, completion state and created/updated timestamps. Validate required text, lengths, supported values and date handling on the backend.
- Derive overdue consistently: a task is overdue only when it is incomplete and its due date is before the agreed current-date boundary. Completed tasks must not remain overdue.
- Enforce ownership on list, read, update, delete and completion endpoints. Return appropriate not-found/forbidden behavior without disclosing another account's private task data.
- Use focused FastAPI routers and Pydantic schemas, existing CRUD/business logic boundaries, the shared frontend API transport and canonical TypeScript types.
- Keep personal tasks distinct from group assignments. Do not expose personal tasks to Tutors, other Students or Admin/public endpoints unless a separately authorized feature explicitly requires it.

### Personal task dashboard/discovery enhancement in the roadmap

- Personalized greeting and summary tiles for open, completed and overdue personal tasks/assignments.
- Clear task cards and due-date labels.
- Text search combined with category and status filters, including uncategorized.
- Bookmarkable filter state where safe; private task data must remain server-authorized.
- Responsive, accessible controls and keyboard behavior.

### Acceptance criteria

- An authenticated Student or Tutor can create, list, view, update, delete and complete/incomplete only their own personal tasks.
- A user cannot access another user's task by guessing/changing an ID, request payload, URL or frontend state.
- Category, due date and completion state persist and validate correctly.
- Open/completed/overdue filters and summary counts agree with the backend's status rules.
- Automated backend tests cover CRUD, validation, ownership isolation, completion transitions, due-date boundaries and unauthorized access.
- Frontend tests cover API contracts, filtering/search behavior, status presentation, loading/error/empty states and relevant keyboard behavior.
- Frontend type-checking and production build pass.

---

## Part 5 — Group learning and assignments

### Group management

- An authenticated Tutor can create a learning group and edit its details.
- The group owner can add Students as members, remove members and view the group/member list.
- Enforce Tutor ownership and membership rules on every group endpoint.
- Prevent unauthorized users from discovering or accessing private group information.

### Group tasks and assignments

- A Tutor can create/share a learning task with a group.
- The Tutor can assign work to all group members, selected members or an individual Student.
- A Student can view only assignments addressed to them through groups they belong to.
- Each Student can update their own completion state without changing another member's status or the original shared task.
- Keep shared task content separate from each student's assignment/progress record so that one student's completion does not mark the task complete for everyone.
- Define behavior for member removal, group changes and existing assignments before implementation; do not silently delete historical completion records.

### Fine-grained group permissions

- The group owner can configure whether members may create, edit or assign group tasks.
- Enforce each permission in backend authorization/business logic for every relevant action; hiding a frontend button is not sufficient.
- Only the group owner may delete the group, rename it or manage membership unless a later approved rule explicitly changes this.
- Show members their effective permissions and explain unavailable actions.
- Test owners and members against every allowed/denied permission combination.

### Data and API design considerations

- Inspect existing tables and relationships first. Reuse existing entities where appropriate; avoid duplicating personal tasks or introducing parallel group systems.
- Model group ownership, membership, shared group-task content, assignment recipients and per-student progress with explicit relationships and database constraints.
- Enforce role, group ownership, active membership and task permissions server-side. Do not trust submitted tutor IDs, student IDs, group IDs or permission flags.
- Validate that only eligible Students can be added/assigned and that the acting Tutor owns the group or has the relevant permission.
- Review indexes, foreign keys, uniqueness constraints, deletion behavior, migration safety and RLS/grants for every new table.
- Continue using FastAPI as the only application data-access layer. Do not add direct browser access to Supabase.

### Acceptance criteria

- Tutors can create/update groups and manage their own groups' Student memberships.
- Tutors can create group tasks and assign them to all, selected or individual members.
- Students see only their own assignments and can update only their own progress.
- Completion/progress is independent per Student.
- A Tutor cannot manage another Tutor's group; a non-member cannot access a private group or its assignments.
- Owner-only group operations and configurable member permissions are enforced by the backend.
- Automated backend tests cover group ownership, membership, assignment targeting, per-student progress isolation, permission combinations and unauthorized access.
- Frontend tests cover group/assignment service contracts, role-specific controls, permission states and relevant empty/error states.
- Frontend type-checking and production build pass.

---

## Cross-cutting security, compatibility and quality rules

- Preserve the existing Student, Tutor and Admin roles and the authenticated account/session mechanism.
- Enforce authentication, current account status, role, ownership, membership and permissions on the backend for every protected operation.
- Preserve existing MVP tutoring posts, tutoring requests, profiles, subjects and records. Do not silently migrate legacy records to a new account or group.
- Inspect the deployed/current schema and versioned migration history before designing schema changes. Use one reviewed migration path; do not duplicate the same change across Supabase SQL and Alembic.
- Do not apply migrations to a shared/production database without explicit owner approval and a reviewed backup/recovery plan.
- Keep pages, reusable components, feature API modules, shared TypeScript types, FastAPI routers, schemas, models and CRUD logic in their established locations as documented in `AGENTS.md`.
- Add regression tests for authorization and existing workflows; run backend tests, frontend tests, frontend type-checking and production build.
- Report exact checks run and their outcomes. Do not claim browser/device testing unless it was performed.
- Update `README.md` and `AGENTS.md` only if the implemented architecture actually changes; do not document planned architecture as already implemented.

## Out of scope for this combined workstream

- Part 6 Admin dashboard and management.
- Part 7 full Beta security/final preparation beyond tests and security controls directly required by Parts 4–5.
- Part 8 environment/deployment completion.
- Unrelated redesigns or changes to the Home/About pages.
- Merging PR #43 or this PR into `main` without explicit approval.

## Completion rule

Do not check Part 4 or Part 5 complete in Issue #41 until the implementation is present on the PR head, code-level review is complete, the relevant backend and frontend automated tests pass, the frontend type-check and production build pass, and all acceptance criteria for the relevant part are met. A planning document or open PR alone does not count as implementation.
