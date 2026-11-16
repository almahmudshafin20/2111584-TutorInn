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
