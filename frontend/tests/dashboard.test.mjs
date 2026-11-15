import assert from "node:assert/strict"
import { after, before, test } from "node:test"
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import reactPlugin from "@vitejs/plugin-react"
import { createServer } from "vite"
import { readFile } from "node:fs/promises"

let vite
let DashboardPage
let dashboardService
let apiModule

const dashboardMocks = {
  name: "tutorinn-dashboard-test-mocks",
  enforce: "pre",
  resolveId(source, importer) {
    if (!importer?.endsWith("/src/pages/DashboardPage.tsx")) return null
    if (source === "../context/AuthContext") return "\0tutorinn-test-auth"
    if (source === "../layouts/AppLayout") return "\0tutorinn-test-layout"
    if (source === "./StudentDashboardPage") return "\0tutorinn-test-student"
    if (source === "./TutorDashboardPage") return "\0tutorinn-test-tutor"
    return null
  },
  load(id) {
    if (id === "\0tutorinn-test-auth") {
      return 'export function useAuth() { return globalThis.__TUTORINN_TEST_AUTH__ ?? { account: null, loading: false } }'
    }
    if (id === "\0tutorinn-test-layout") {
      return 'import React from "react"; export function AppLayout({ children }) { return React.createElement("main", null, children) }'
    }
    if (id === "\0tutorinn-test-student") {
      return 'import React from "react"; export default function StudentDashboardPage() { return React.createElement("h1", null, "Student dashboard test view") }'
    }
    if (id === "\0tutorinn-test-tutor") {
      return 'import React from "react"; export default function TutorDashboardPage() { return React.createElement("h1", null, "Tutor dashboard test view") }'
    }
    return null
  },
}

before(async () => {
  vite = await createServer({
    configFile: false,
    root: process.cwd(),
    plugins: [reactPlugin(), dashboardMocks],
    server: { middlewareMode: true },
    appType: "custom",
    logLevel: "error",
  })
  ;({ default: DashboardPage } = await vite.ssrLoadModule("/src/pages/DashboardPage.tsx"))
  dashboardService = await vite.ssrLoadModule("/src/services/dashboard.ts")
  apiModule = await vite.ssrLoadModule("/src/services/api.ts")
})

after(async () => {
  delete globalThis.__TUTORINN_TEST_AUTH__
  await vite?.close()
})

function renderDashboard(auth) {
  globalThis.__TUTORINN_TEST_AUTH__ = auth
  return renderToStaticMarkup(React.createElement(DashboardPage))
}

test("dashboard requires an authenticated account", () => {
  const markup = renderDashboard({ account: null, loading: false })
  assert.match(markup, /Sign in required/)
  assert.match(markup, /href="\/login"/)
})

test("dashboard shows a loading state while the session is checked", () => {
  const markup = renderDashboard({ account: null, loading: true })
  assert.match(markup, /Checking your session/)
})

test("student accounts are routed to the Student dashboard only", () => {
  const markup = renderDashboard({ account: { id: 7, email: "student@example.test", role: "student" }, loading: false })
  assert.match(markup, /Student dashboard test view/)
  assert.doesNotMatch(markup, /Tutor dashboard test view/)
})

test("tutor accounts are routed to the Tutor dashboard only", () => {
  const markup = renderDashboard({ account: { id: 8, email: "tutor@example.test", role: "tutor" }, loading: false })
  assert.match(markup, /Tutor dashboard test view/)
  assert.doesNotMatch(markup, /Student dashboard test view/)
})

test("admin accounts do not enter Student or Tutor dashboards", () => {
  const markup = renderDashboard({ account: { id: 9, email: "admin@example.test", role: "admin" }, loading: false })
  assert.match(markup, /Admin workspace/)
  assert.doesNotMatch(markup, /Student dashboard test view|Tutor dashboard test view/)
})

test("dashboard service maps discovery filters to trimmed query parameters", async () => {
  const requests = []
  globalThis.window = { localStorage: { getItem: () => null }, dispatchEvent() {} }
  globalThis.document = { cookie: "" }
  globalThis.fetch = async (url, init = {}) => {
    requests.push({ url: String(url), init })
    return new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } })
  }
  await dashboardService.discoverTutors({ subject: "  Mathematics ", level: " HSC ", min_experience: " 2 ", availability: " Weekends " })
  assert.equal(requests[0].url, "/api/tutors?subject=Mathematics&level=HSC&min_experience=2&availability=Weekends")
})

test("dashboard service uses the expected request and response endpoints and methods", async () => {
  const requests = []
  globalThis.window = { localStorage: { getItem: () => null }, dispatchEvent() {} }
  globalThis.document = { cookie: "" }
  globalThis.fetch = async (url, init = {}) => {
    requests.push({ url: String(url), method: init.method ?? "GET", body: init.body ? JSON.parse(init.body) : undefined })
    return new Response(init.method === "DELETE" ? null : "{}", { status: init.method === "DELETE" ? 204 : 200, headers: { "Content-Type": "application/json" } })
  }

  await dashboardService.loadDashboard()
  await dashboardService.createTutoringRequest({ subjects: ["Physics"] })
  await dashboardService.updateTutoringRequest(12, { level: "HSC" })
  await dashboardService.deleteTutoringRequest(12)
  await dashboardService.respondToRequest(12, "Interested")
  await dashboardService.acceptTutorResponse(12, 31)

  assert.deepEqual(requests.map(({ url, method }) => [url, method]), [
    ["/api/dashboard", "GET"],
    ["/api/requests", "POST"],
    ["/api/requests/12", "PUT"],
    ["/api/requests/12", "DELETE"],
    ["/api/requests/12/responses", "POST"],
    ["/api/requests/12/responses/31/accept", "POST"],
  ])
  assert.deepEqual(requests[1].body, { subjects: ["Physics"] })
  assert.deepEqual(requests[4].body, { response: "Interested" })
})

test("authenticated dashboard and request calls ignore spoofed legacy profile headers", async () => {
  let captured
  globalThis.window = {
    localStorage: { getItem: key => key === "tutorinn-profile-id" ? "999" : "tutor" },
    dispatchEvent() {},
  }
  globalThis.document = { cookie: "" }
  globalThis.fetch = async (_url, init) => {
    captured = init
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } })
  }
  apiModule.setAccessToken("test-access-token")
  await apiModule.api("/api/requests")
  const headers = new Headers(captured.headers)
  assert.equal(headers.get("Authorization"), "Bearer test-access-token")
  assert.equal(headers.has("X-TutorInn-Profile-ID"), false)
  assert.equal(headers.has("X-TutorInn-Profile-Type"), false)
  apiModule.setAccessToken(null)
})

test("Student and Tutor dashboard source retains key workflow controls", async () => {
  const [student, tutor] = await Promise.all([
    readFile("src/pages/StudentDashboardPage.tsx", "utf8"),
    readFile("src/pages/TutorDashboardPage.tsx", "utf8"),
  ])
  for (const label of ["Filter tutor search", "Subject", "Qualification / level", "Minimum experience (years)", "Availability", "Create a tutoring request", "Edit request", "Delete", "Accept this Tutor"]) {
    assert.ok(student.includes(label), `Student dashboard is missing: ${label}`)
  }
  for (const label of ["Student tutoring requests", "I'm interested", "Not interested", "aria-pressed", "My responses"]) {
    assert.ok(tutor.includes(label), `Tutor dashboard is missing: ${label}`)
  }
})

test("responsive and reduced-motion styles remain present", async () => {
  const css = await readFile("src/index.css", "utf8")
  assert.match(css, /@media\s*\(/)
  assert.match(css, /prefers-reduced-motion/)
})
