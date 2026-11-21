import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"

const api = await readFile(new URL("../src/api/firstAdminTransfer.ts", import.meta.url), "utf8")
const page = await readFile(new URL("../src/pages/FirstAdminTransferPage.tsx", import.meta.url), "utf8")
const app = await readFile(new URL("../src/App.tsx", import.meta.url), "utf8")
const adminPage = await readFile(new URL("../src/pages/AdminReviewPage.tsx", import.meta.url), "utf8")
const router = await readFile(new URL("../../backend/app/routers/first_admin_transfer.py", import.meta.url), "utf8")

test("transfer API module uses the shared client and the backend routes", () => {
  assert.match(api, /from "\.\/api"/)
  for (const route of ["/api/admin/first-admin-transfer", "/api/admin/first-admin-transfer/accept", "/api/admin/first-admin-transfer/decline"]) {
    assert.ok(api.includes(route), `missing ${route}`)
    assert.ok(router.includes(route), `backend missing ${route}`)
  }
  assert.doesNotMatch(api, /fetch\(|axios/)
})

test("transfer page explains the authority, requires re-confirmation and never renders secrets", () => {
  assert.match(page, /highest-privilege authority/)
  assert.match(page, /type="password"/)
  assert.match(page, /Type the recipient email again/)
  assert.match(page, /window\.confirm/)
  assert.doesNotMatch(page, /fetch\(/)
  assert.match(page, /account\.role !== "admin"/)
})

test("transfer page is routed and linked from the Admin workspace", () => {
  assert.match(app, /\/admin\/first-admin-transfer/)
  assert.match(adminPage, /href="\/admin\/first-admin-transfer"/)
})
