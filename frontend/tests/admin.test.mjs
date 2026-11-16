import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"

const api = await readFile(new URL("../src/api/admin.ts", import.meta.url), "utf8")
const page = await readFile(new URL("../src/pages/AdminReviewPage.tsx", import.meta.url), "utf8")
const router = await readFile(new URL("../../backend/app/routers/admin.py", import.meta.url), "utf8")

test("Admin API exposes overview, moderation, verification, audit and export workflows", () => {
  for (const route of ["/api/admin/overview", "/api/admin/users", "/api/admin/tutors", "/api/admin/requests", "/api/admin/activity", "/api/admin/security", "/api/admin/export/"]) {
    assert.ok(router.includes(route), `missing backend route ${route}`)
  }
  assert.match(api, /bulkSetAdminUserStatus/)
  assert.match(api, /reviewAdminTutor/)
})

test("Admin dashboard has role-aware sections and URL-persisted filters", () => {
  for (const section of ["overview", "students", "tutors", "requests", "activity", "security", "settings"]) {
    assert.ok(page.includes(`"${section}"`))
  }
  assert.match(page, /history\.replaceState/)
  assert.match(page, /account\.role !== "admin"/)
})


test("Admin workspace separates paginated learning groups and tasks and offers controlled activity refresh", () => {
  assert.match(page, /id: "groups", label: "Learning groups"/)
  assert.match(page, /getAdminGroups\(\{ q: search, owner_account_id: ownerAccountId \? Number\(ownerAccountId\) : undefined, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize \}\)/)
  assert.match(page, /getAdminTasks\(\{ q: search, status, owner_account_id: ownerAccountId \? Number\(ownerAccountId\) : undefined, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize \}\)/)
  assert.match(page, /getAdminGroupTasks\(\{ q: search, owner_account_id: ownerAccountId \? Number\(ownerAccountId\) : undefined, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize \}\)/)
  assert.match(page, /Group learning tasks and assignments/)
  assert.match(router, /@router.get\("\/api\/admin\/group-tasks"\)/)
  assert.match(page, /Auto-refresh every 30 seconds/)
  assert.match(page, /Inspect account/)
  assert.match(page, /View related activity/)
  assert.match(router, /"assignment_count": assignments/)
  assert.match(router, /"trends": trends/)
})


test("Admin group-task bulk deletion is exposed with confirmation and a reason", () => {
  assert.match(api, /\/api\/admin\/group-tasks\/bulk/)
  assert.match(page, /Delete selected group tasks/)
  assert.match(page, /bulkDeleteAdminGroupTasks\(ids, reason\)/)
  assert.match(router, /def bulk_delete_group_tasks/)
  assert.match(router, /Select between 1 and 50 unique group task IDs/)
})


test("Admin management filters preserve date and owner scope in API requests and the URL", () => {
  assert.match(api, /created_from\?: string/)
  assert.match(api, /created_to\?: string/)
  assert.match(api, /owner_account_id\?: number/)
  assert.match(api, /account_id\?: number/)
  assert.match(page, /next\.set\("created_from", createdFrom\)/)
  assert.match(page, /next\.set\("created_to", createdTo\)/)
  assert.match(page, /next\.set\("owner_account_id", ownerAccountId\)/)
  assert.match(page, /getAdminRequests\(\{ status, q: search, owner_account_id:/)
  assert.match(page, /getAdminGroupTasks\(\{ q: search, owner_account_id:/)
})


test("Admin security investigation exposes filtered events and attributable context", () => {
  assert.match(api, /getAdminSecurity = \\(hours = 24, minEvents = 3, filters:/)
  assert.match(api, /user_agent\?: string/)
  assert.match(page, /Attempted account:/)
  assert.match(page, /Browser\\/device:/)
  assert.match(page, /Unattributed attempts/)
  assert.match(page, /Inspect account/)
  assert.match(router, /by_attempted_email/)
  assert.match(router, /SecurityEvent\\.user_agent/)
  assert.match(router, /target=\{target\\.id\}/)
})
