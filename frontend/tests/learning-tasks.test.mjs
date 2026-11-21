import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"

const read = (path) => readFile(new URL(path, import.meta.url), "utf8")

test("personal task API uses the shared client for CRUD, filters and summaries", async () => {
  const api = await read("../src/api/tasks.ts")
  assert.match(api, /from "\.\/api"/)
  for (const route of ["\/api\/me\/tasks", "\/api\/me\/tasks\/summary"]) assert.ok(api.includes(route))
  assert.match(api, /method:"POST"/)
  assert.match(api, /method:"PUT"/)
  assert.match(api, /method:"DELETE"/)
  assert.match(api, /uncategorized/)
  assert.match(api, /filters\.status/)
})

test("personal task panel exposes private task CRUD, completion, search and status filters", async () => {
  const panel = await read("../src/components/PersonalTasksPanel.tsx")
  for (const marker of ["Personal learning tasks", "createPersonalTask", "updatePersonalTask", "deletePersonalTask", "Mark complete", "Mark open", "Overdue tasks", "Press", "__uncategorized__"]) {
    assert.ok(panel.includes(marker), `Missing task workflow: ${marker}`)
  }
})

test("Student and Tutor dashboards both include personal tasks and the protected group workspace", async () => {
  const [student, tutor, app] = await Promise.all([
    read("../src/pages/StudentDashboardPage.tsx"),
    read("../src/pages/TutorDashboardPage.tsx"),
    read("../src/App.tsx"),
  ])
  for (const page of [student, tutor]) {
    assert.match(page, /PersonalTasksPanel/)
    assert.match(page, /href="\/groups"/)
  }
  assert.match(app, /path === "\/groups"/)
  assert.ok(app.includes('if (path === "/groups") return <RequireAccount roles={["student", "tutor"]}><GroupLearningPage /></RequireAccount>'))
})

test("group video links are rendered as safe click-through links, not embedded players", async () => {
  const page = await read("../src/pages/GroupLearningPage.tsx")
  const api = await read("../src/api/groups.ts")
  assert.match(page, /Google Drive video link/)
  assert.match(page, /href=\{t\.video_url\}/)
  assert.match(page, /target="_blank" rel="noopener noreferrer"/)
  assert.match(api, /video_url:string\|null/)
  assert.doesNotMatch(page, /<iframe|<video/)
})

test("role navigation separates Student, Tutor, Moderator and Admin menus", async () => {
  const header = await read("../src/components/SiteHeader.tsx")
  assert.match(header, /function navigationFor\(/)
  assert.match(header, /role === "student"/)
  assert.match(header, /role === "tutor"/)
  assert.match(header, /role === "moderator"/)
  assert.match(header, /Password reset requests/)
  assert.match(header, /Review/)
  assert.match(header, /aria-label=\{`\$\{account\.role\} navigation`\}/)
})
