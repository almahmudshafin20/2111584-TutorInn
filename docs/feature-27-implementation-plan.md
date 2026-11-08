# Issue #27 implementation plan

This document records the coordinated implementation scope for Issue #27. The current commit is a planning scaffold for the draft pull request; it does not yet implement the application changes.

## Goals

Improve TutorInn's demo identity workflow, profile management, post ownership, individual interest responses, and multi-subject support without introducing user authentication.

## Planned implementation

### 1. Selected demo profile
- Replace role-only session identity with `tutorinn-profile-id` and `tutorinn-profile-type`.
- Validate the stored profile against the API when the app starts.
- Provide a persistent profile switcher.
- Keep Admin access separate through the existing admin-key flow.
- Clearly label this as demo identity, not authentication.

### 2. Direct profile management
- Allow Student Profiles and Tutor Profiles pages to create, view, edit, delete, and select profiles directly.
- Do not gate profile CRUD on the active profile type.
- Confirm deletion and clear the selected profile when it is deleted.
- Define safe behavior for profiles that still own posts.

### 3. Post ownership
- Add author profile ID and type to new tutoring posts.
- Scope edit/delete operations to the selected author profile.
- Preserve legacy posts without assigning them to an arbitrary profile.

### 4. Individual interest responses
- Add a response record keyed by post and responding profile.
- Support Interested, Not Interested, and no response per profile/post pair.
- Prevent duplicate records and allow response changes.
- Route each Interested response through admin review independently.
- Keep Not Interested records separate and hide those posts only for the responding profile.

### 5. Multi-subject support
- Support multiple subjects on tutor profiles, student profiles, and tutoring posts.
- Use structured values instead of comma-separated free text.
- Render subjects as separate chips/labels and support subject filtering.
- Preserve existing single-subject values during migration.

## Migration and compatibility requirements

- Add new database columns/tables without dropping existing data.
- Backfill legacy subject text into structured subject lists where unambiguous.
- Leave legacy post ownership unknown rather than guessing.
- Preserve legacy interest fields for compatibility until all callers use response records.
- Add tests for existing SQLite databases and the configured PostgreSQL-compatible schema.

## Security limitation

This remains a demo identity model. Profile IDs and types supplied by browser storage/request headers are user-controlled and are not proof of identity. Backend checks can prevent accidental cross-profile actions in the demo but cannot replace authenticated ownership authorization.

## Verification plan

- Backend tests for profile CRUD, ownership checks, independent response records, response transitions, admin review, and subject validation.
- Frontend production build and workflow checks for switching profiles, direct profile management, multi-subject entry/display, and per-profile interest history.
- Verify legacy records remain readable and are not silently reassigned.
