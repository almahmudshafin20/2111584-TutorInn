import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"

const api = await readFile(new URL("../src/api/admin.ts", import.meta.url), "utf8")
const page = await readFile(new URL("../src/pages/AdminReviewPage.tsx", import.meta.url), "utf8")
const router = await readFile(new URL("../../backend/app/routers/admin.py", import.meta.url), "utf8")
const deployment = await readFile(new URL("../../vercel.json", import.meta.url), "utf8")

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
  assert.match(page, /\}, \[tab, search, status, createdFrom, createdTo, ownerAccountId, page\]\)/)
  assert.match(page, /getAdminRequests\(\{ status, q: search, owner_account_id:/)
  assert.match(page, /getAdminGroupTasks\(\{ q: search, owner_account_id:/)
})


test("Admin groups endpoint is registered only once and keeps paginated filters", () => {
  assert.equal((router.match(/@router\.get\("\/api\/admin\/groups"\)/g) ?? []).length, 1)
  assert.match(router, /offset: int = Query\(default=0/)
  assert.match(router, /"items": result, "total": total/)
})

test("Admin security investigation supports server-side pagination", () => {
  assert.match(api, /offset\?: number; limit\?: number/)
  assert.match(page, /security\?\.total/)
  assert.match(page, /Page \{page \+ 1\} of \{pages\}/)
  assert.match(router, /offset: int = Query\(default=0/)
  assert.match(router, /\.offset\(offset\)\.limit\(limit\)/)
})

test("Admin security investigation exposes filtered events and attributable context", () => {
  assert.ok(api.includes("getAdminSecurity = (hours = 24, minEvents = 3, filters:"))
  assert.ok(api.includes("user_agent?: string"))
  assert.ok(page.includes("Attempted account:"))
  assert.ok(page.includes("Browser/device:"))
  assert.ok(page.includes("Unattributed attempts"))
  assert.ok(page.includes("Inspect account"))
  assert.ok(router.includes("by_attempted_email"))
  assert.ok(router.includes("SecurityEvent.user_agent"))
  assert.ok(router.includes('SecurityEvent.details.ilike(f"%target={target.id}%")'))
})

test("Admin security summaries expose distinct sources and the newest 50 hostile events", () => {
  assert.match(api, /distinct_accounts: number/)
  assert.match(api, /distinct_source_ips: number/)
  assert.match(api, /hostile_events: AdminActivity\[\]/)
  assert.match(page, /50 newest hostile events/)
  assert.match(page, /distinct accounts/)
  assert.match(page, /source IPs/)
  assert.ok(router.includes("func.count(func.distinct(SecurityEvent.account_id))"))
  assert.ok(router.includes("func.count(func.distinct(SecurityEvent.ip_address))"))
  assert.ok(router.includes(".limit(50)"))
})

test("activity retention is configurable, secret-protected and scheduled", () => {
  assert.match(router, /ACTIVITY_RETENTION_DAYS/)
  assert.match(router, /CRON_SECRET/)
  assert.match(router, /timedelta\(hours=1\)/)
  assert.match(router, /SecurityEvent\.event_type\.like\("auth_attempt_%"/)
  assert.match(deployment, /"path": "\/api\/internal\/maintenance\/activity-retention"/)
  assert.match(deployment, /"schedule": "0 3 \* \* \*"/)
})


test("account deletion is request-only for Students and Tutors and Admin-reviewed", async () => {
  const accountPage = await readFile(new URL("../src/pages/MyProfilePage.tsx", import.meta.url), "utf8")
  const deletionPage = await readFile(new URL("../src/pages/AdminDeletionRequestsPage.tsx", import.meta.url), "utf8")
  const app = await readFile(new URL("../src/App.tsx", import.meta.url), "utf8")
  const accountApi = await readFile(new URL("../src/api/auth.ts", import.meta.url), "utf8")
  const accountRouter = await readFile(new URL("../../backend/app/routers/account.py", import.meta.url), "utf8")
  assert.match(accountPage, /Request account deletion/)
  assert.match(accountPage, /Preferred deletion method/)
  assert.match(accountPage, /anonymize/)
  assert.match(accountPage, /complete/)
  assert.match(accountPage, /requestMyAccountDeletion\(deletionPassword, deletionReason, \{/)
  assert.match(accountPage, /content_action: deletionContentAction/)
  assert.match(accountApi, /\/api\/me\/deletion-request/)
  assert.match(deletionPage, /account\.role !== "admin"/)
  assert.match(deletionPage, /Approve and choose method/)
  assert.match(deletionPage, /requested_content_action/)
  assert.match(deletionPage, /former_user_link_status/)
  assert.match(deletionPage, /issueFreshLink/)
  assert.match(deletionPage, /Reject and reactivate/)
  assert.match(app, /\/admin\/deletions/)
  assert.match(accountRouter, /@router\.post\("\/api\/me\/deletion-request"/)
  assert.match(router, /@router\.get\("\/api\/admin\/account-deletion-requests"/)
  assert.match(router, /@router\.patch\("\/api\/admin\/account-deletion-requests\/{request_id}"/)
  assert.match(router, /deletion_pending/)
  assert.match(router, /_delete_selected_content/)
  assert.match(router, /former-user-link/)
})


test("Admin security exposes pseudonymous registration counts by source IP", () => {
  assert.match(api, /registrations_by_ip:/)
  assert.match(page, /registrations_by_ip: \{ ip_address: string; registrations: number;/)
  assert.match(page, /Account registrations by source IP/)
  assert.match(page, /including anonymized deleted accounts/)
  assert.match(router, /deleted_account_id=/)
  assert.match(router, /registration_identity = case/)
  assert.match(router, /"registrations_by_ip"/)
})


test("Admin must explain and email any deletion-scope override", async () => {
  const deletionPage = await readFile(new URL("../src/pages/AdminDeletionRequestsPage.tsx", import.meta.url), "utf8")
  assert.match(deletionPage, /scopeChanged/)
  assert.match(deletionPage, /at least 5 characters/)
  assert.match(deletionPage, /This explanation will be emailed to the user/)
  assert.match(deletionPage, /An explanation of at least 5 characters is required/)
  assert.match(router, /admin_reason=note if scope_changed else/)
  assert.match(router, /scope_changed=\{scope_changed\}/)
})


test("Admin dashboard is the authenticated dashboard and exposes separate privileged account lists", async () => {
  const dashboard = await readFile(new URL("../src/pages/DashboardPage.tsx", import.meta.url), "utf8")
  assert.match(dashboard, /return <AdminReviewPage \/>/)
  for (const section of ["admins", "moderators"]) assert.ok(page.includes(`"${section}"`))
  assert.match(page, /page \* pageSize \+ index \+ 1/)
  assert.match(page, /key=\{user\.id\}/)
  assert.match(page, /inspectUser\(user\.id\)/)
  assert.match(page, /First Admin/)
})

test("Admin main-resource CSV export is available and filtered", () => {
  assert.match(api, /"users" \| "posts" \| "tasks" \| "activity"/)
  assert.match(page, /download\("posts"\)/)
})

test("Admin account lists show recomputed display positions (for example 'Tutor 1') and keep real IDs for actions", () => {
  assert.match(page, /`Tutor \$\{page \* pageSize \+ index \+ 1\}`/)
  assert.match(page, /`Student \$\{page \* pageSize \+ index \+ 1\}`/)
  assert.match(page, /`\$\{user\.role\.charAt\(0\)\.toUpperCase\(\)\}\$\{user\.role\.slice\(1\)\} \$\{page \* pageSize \+ index \+ 1\}`/)
  assert.match(page, /inspectUser\(user\.id\)/)
  assert.doesNotMatch(page, /<td>\{user\.id\}<\/td>/)
})
