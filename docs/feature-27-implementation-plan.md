# Issue #27 — implementation record

This document records the implementation delivered on `feature/profile-ownership-interests-multi-subjects`.

## Implemented

### 1. Selected demo profile
- Browser storage now uses `tutorinn-profile-id` and `tutorinn-profile-type`.
- The navigation header provides a persistent profile switcher populated from Student and Tutor directories.
- Invalid or deleted selections are cleared when the directories are refreshed.
- Post creation, editing/deletion, and interest responses send the selected profile ID/type to the API.
- The UI and documentation explicitly describe this as demo identity, not authentication.

### 2. Direct profile management
- Student and Tutor directories independently provide create, view, edit, delete, and Use Profile actions.
- Profile CRUD no longer depends on a selected role.
- Deleting a profile removes posts authored by that profile and their related response records, plus responses the profile made elsewhere. The confirmation warns about this.
- Deleting the selected profile clears the stored selection.

### 3. Post ownership
- New posts store `author_profile_id` and `author_profile_type`.
- The API derives the author name from the selected profile.
- Update/delete operations require the selected profile to match the stored author.
- Legacy posts retain null owner metadata; they are not assigned to a guessed profile and cannot be edited/deleted through the new ownership flow.

### 4. Independent interest responses
- The `interest_responses` table stores one response per post and responding profile, with a database uniqueness constraint.
- Interested and Not Interested are independent for each profile/post pair.
- A profile can change its response. Changing to Interested resets its review state to Pending.
- Not Interested is not sent to Admin review and is hidden only from that profile's active Hub feed.
- The My Responses page displays response history and allows changing a response.
- Admin Review lists and approves/rejects each Interested response independently.
- The old confirmation routes remain as compatibility endpoints but now write profile-specific records.

### 5. Multiple subjects
- Student profiles, Tutor profiles, and tutoring posts accept structured `subjects: string[]`.
- The UI uses a multi-entry subject picker with duplicate prevention and removable subject chips.
- Profile and post views render each subject separately.
- Tutor and post subject filtering supports the structured subject list.
- Existing legacy subject text remains available as a one-or-more-item compatibility fallback; legacy data is not overwritten with an empty subject list.

### 6. Documentation and CI
- README documents the selected-profile headers, API routes, migration behavior, and demo identity limitation.
- Backend workflow tests cover multi-subject data, profile-owned posts, per-profile response isolation, admin review, and profile deletion.
- GitHub Actions runs backend tests and the frontend production build on pushes to this feature branch and pull requests targeting main.

## Migration and security notes

- Startup migrations add nullable subject JSON-text columns and nullable post owner columns to existing databases.
- Legacy post owners remain NULL because the old data cannot safely identify a particular profile.
- This is not authentication. Browser-supplied profile headers are user-controlled and must not be treated as secure proof of identity. Add real authentication and server-verified ownership before production use.
- Profile deletion intentionally cascades through the profile's authored posts and response records, after explicit confirmation in the UI.

## Verification status

The GitHub Actions workflow has been added. Its actual run status should be checked in the PR Checks tab; do not consider CI passed until GitHub reports green checks.
