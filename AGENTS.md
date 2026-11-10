# TutorInn Development Guidelines

These instructions apply to all future work in this repository. Read this file before implementing a feature, refactoring code, or changing project structure. These rules are permanent project guidance and must be followed regardless of which chat, contributor, or coding agent is working on TutorInn.

## 1. Preserve the established architecture

The architecture below was introduced to address the TutorInn mid-assessment feedback. Do not treat these folders as decorative or optional. New code must use them.

### Frontend

- Put route/page-level UI in `frontend/src/pages/`, with each page in its own appropriately named file.
- Put reusable UI components in `frontend/src/components/`.
- Keep HTTP requests and API communication out of page and component implementations. Use `frontend/src/services/api.ts` as the shared API layer; add a focused service module only when the existing service design makes that appropriate.
- Put shared TypeScript interfaces, types, and related definitions in `frontend/src/types/`.
- Keep `frontend/src/App.tsx` focused on application composition and routing/page selection. Do not move whole feature implementations back into it.
- Keep Home, About, Task Details, and other distinct pages as separate pages rather than combining unrelated screens.

### Backend

- Put API endpoint groups in focused modules under `backend/routers/` and use FastAPI `APIRouter`.
- Keep `backend/main.py` focused on application creation/configuration and router registration.
- Keep database models separate from API request/response schemas. Follow the existing `backend/models.py` and `backend/schemas.py` separation unless the project grows enough to justify dedicated modules.
- Keep business and database operations out of route handlers. Put them in `backend/crud.py` or a suitable service/repository module.
- Reuse the existing database configuration, dependencies, and validation patterns. Do not duplicate setup or logic.

## 2. The six architecture recommendations

Every new feature and refactor must preserve all six recommendations:

1. **Frontend pages/components:** split UI into dedicated files under `frontend/src/pages/` and `frontend/src/components/`.
2. **API service layer:** centralize API calls in `frontend/src/services/api.ts` (or a focused service module that uses the shared API layer).
3. **TypeScript types:** keep shared types in `frontend/src/types/`, not scattered through components.
4. **Backend routers:** organize endpoints into modules under `backend/routers/`, not all in `main.py`.
5. **Models and schemas:** separate database models and request/response schemas from route definitions and from each other.
6. **Business/data logic:** place database operations and business logic in CRUD/service/repository modules, not directly in route handlers.

## 3. The three highest-priority recommendations

These three requirements must be checked on every frontend feature:

1. New pages and UI pieces belong in `frontend/src/pages/` or `frontend/src/components/`.
2. API calls must go through `frontend/src/services/api.ts` and must not be written directly inside UI components.
3. Shared TypeScript types belong in `frontend/src/types/`.

## 4. Workflow for every new feature

1. Inspect the current implementation and repository structure before editing.
2. Reuse existing components, API services, types, routers, models, schemas, and CRUD/service functions where appropriate.
3. Implement the feature in the correct existing folders. Do not create parallel or duplicate architecture.
4. Keep changes focused and preserve existing working behavior and API compatibility unless a change is explicitly required.
5. Add or update tests for the changed behavior.
6. Run relevant backend tests/checks and the frontend production build. Report the exact commands and outcomes; never claim a check passed unless it was run successfully.
7. Review the changed-file list before opening a PR. Confirm that files are in the correct locations and no unrelated changes are included.

## 5. GitHub issue, branch, and pull-request rules

- Use one focused issue, one feature branch, and one pull request for each approved task, unless the project owner explicitly requests otherwise.
- Include the PR number in the branch name, for example `feat/42-short-description` or `fix/43-short-description`.
- Create the feature branch from the latest appropriate base branch, normally `main`.
- Link the PR to its issue using GitHub's closing keyword where appropriate (for example, `Closes #42`).
- The PR description must summarize what changed, mention relevant related work where appropriate, and list verification performed.
- Do not create extra issues or PRs for the same task without explicit direction.
- **Never create, edit, merge, close, delete, or otherwise modify GitHub resources without the project owner's explicit approval for the requested action.**
- **Never merge a PR into `main` unless the project owner explicitly authorizes that merge.**
- An instruction to implement code or open a PR does not imply permission to merge it.

## 6. Quality checklist before requesting review

- [ ] Pages and reusable UI are in the correct frontend folders.
- [ ] No direct fetch/axios request logic has been added inside UI components; API calls use the service layer.
- [ ] Shared TypeScript types are in `frontend/src/types/`.
- [ ] Backend endpoints are in focused router modules.
- [ ] `main.py` remains focused on app setup and router registration.
- [ ] Database models and API schemas remain separate.
- [ ] Route handlers delegate business/database work to CRUD/service/repository code.
- [ ] Relevant tests/checks have been run and their results are accurately reported.
- [ ] Frontend production build has been run when frontend code changes.
- [ ] Existing behavior and compatibility have been considered.
- [ ] PR references the correct issue and includes a clear summary.
- [ ] No merge or other GitHub mutation is performed without explicit approval.

## 7. When a rule appears not to fit

Do not ignore a rule silently. First inspect the current code and explain why the existing pattern is unsuitable. Prefer a small, consistent extension of the established architecture. Document any justified exception in the PR description so it can be reviewed.

## 8. Source of truth

This file is the repository's persistent development-guideline reference. If a chat summary or informal instruction conflicts with the current repository architecture, inspect the code and follow this file unless the project owner explicitly approves a change to the guidelines. Update this file only through an explicitly approved, reviewed repository change.
