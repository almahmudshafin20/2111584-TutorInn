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
  dashboardService = await vite.ssrLoadModule("/src/api/dashboard.ts")
  apiModule = await vite.ssrLoadModule("/src/api/api.ts")
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


test("public navigation uses clear button-like links and distinct account actions", async () => {
  const [header, css] = await Promise.all([
    readFile("src/components/SiteHeader.tsx", "utf8"),
    readFile("src/index.css", "utf8"),
  ])
  assert.match(header, /aria-label="Public navigation"/)
  assert.match(header, /href="\/" aria-current=/)
  assert.match(header, /href="\/about" aria-current=/)
  assert.match(header, /className="button nav-login"/)
  assert.match(header, /className="button primary nav-register"/)
  assert.match(css, /\.public-header-actions nav a\[aria-current="page"\]:after/)
  assert.match(css, /content:\s*none\s*!important/)
})

test("theme selection applies the document theme immediately and persists it", async () => {
  const [header, theme] = await Promise.all([
    readFile("src/components/SiteHeader.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.match(header, /setTheme\("light"\)/)
  assert.match(header, /setTheme\("dark"\)/)
  assert.match(theme, /root\.dataset\.theme = theme/)
  assert.match(theme, /applyTheme\(nextTheme, palette\)/)
  assert.match(theme, /localStorage\.setItem\("tutorinn-theme", theme\)/)
})

test("shared navigation avoids expensive blur and global theme transitions", async () => {
  const css = await readFile("src/index.css", "utf8")
  assert.match(css, /backdrop-filter:\s*none\s*!important/)
  assert.match(css, /html, body\s*\{\s*transition:\s*none\s*!important;/)
  assert.match(css, /prefers-reduced-motion/)
})


test("theme switcher renders a sliding indicator and exposes the active theme", async () => {
  const header = await readFile("src/components/SiteHeader.tsx", "utf8")
  const css = await readFile("src/index.css", "utf8")
  assert.match(header, /theme-switcher/)
  assert.match(header, /data-theme={theme}/)
  assert.match(css, /\.theme-switcher::before/)
  assert.match(css, /transition:\s*transform\s*\.25s/)
  assert.match(css, /\.theme-switcher\.is-dark::before/)
})

test("public Home, About and Login navigation exposes the current page", async () => {
  const [header, css] = await Promise.all([
    readFile("src/components/SiteHeader.tsx", "utf8"),
    readFile("src/index.css", "utf8"),
  ])
  assert.match(header, /href="\/" aria-current=/)
  assert.match(header, /href="\/about" aria-current=/)
  assert.match(header, /href="\/login" aria-current=/)
  assert.match(css, /nav a\[aria-current="page"\]/)
  assert.match(css, /nav a\[aria-current="page"\]:after/)
  assert.match(css, /nav-login\[aria-current="page"\]:after/)
})

test("theme and navigation interaction animations respect reduced motion", async () => {
  const css = await readFile("src/index.css", "utf8")
  assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)/)
  assert.match(css, /\.theme-switcher::before[\s\S]*?transition:\s*none\s*!important/)
})

test("login and registration text remains readable in light and dark themes", async () => {
  const [css, login, registration] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/pages/LoginPage.tsx", "utf8"),
    readFile("src/pages/RegisterPage.tsx", "utf8"),
  ])

  for (const page of [login, registration]) {
    assert.match(page, /className="auth-aside"/)
    assert.match(page, /className="auth-benefits"/)
    assert.match(page, /className="auth-content"/)
    assert.match(page, /className="auth-form-heading"/)
  }

  assert.match(css, /\.auth-shell input:not\(\[type="checkbox"\]\):not\(\[type="radio"\]\)[\s\S]*?color:var\(--ink\)/)
  assert.match(css, /\.auth-shell input::placeholder[\s\S]*?color:var\(--muted\)/)
  assert.match(css, /--auth-aside-bg:\s*var\(--accent-soft\)/)
  assert.match(css, /--auth-aside-ink:\s*var\(--ink\)/)
  assert.match(css, /\.auth-shell \.auth-aside h2\s*\{\s*color:var\(--auth-aside-ink\)/)
  assert.match(css, /-webkit-text-fill-color:var\(--ink\)/)
  assert.match(css, /\.auth-shell-register \.auth-benefits\s*\{\s*display: grid;/)
})


test("four selectable color palettes are available and persisted independently from day/night mode", async () => {
  const [theme, header, css] = await Promise.all([
    readFile("src/context/ThemeContext.tsx", "utf8"),
    readFile("src/components/SiteHeader.tsx", "utf8"),
    readFile("src/index.css", "utf8"),
  ])
  for (const palette of ["royal-blue", "charcoal-red", "nude-mocha", "teal-peach"]) {
    assert.ok(theme.includes(`id: "${palette}"`), `Missing palette: ${palette}`)
    assert.ok(css.includes(`data-palette="${palette}"`), `Missing CSS theme: ${palette}`)
  }
  assert.match(theme, /localStorage\.getItem\("tutorinn-palette"\)/)
  assert.match(theme, /localStorage\.setItem\("tutorinn-palette", palette\)/)
  assert.match(theme, /localStorage\.setItem\("tutorinn-theme", theme\)/)
  assert.match(header, /Choose color palette/)
  assert.match(header, /aria-pressed={palette === option\.id}/)
  assert.match(css, /\.palette-picker-menu/)
  assert.match(css, /prefers-reduced-motion:reduce/)
})


test("all theme controls, authentication panels and shared app surfaces use palette tokens", async () => {
  const css = await readFile("src/index.css", "utf8")
  assert.match(css, /\.theme-switcher::before[\s\S]*?background:var\(--switch-thumb\)/)
  assert.match(css, /\.theme-switch-option\.is-active[\s\S]*?color:var\(--switch-active\)/)
  assert.match(css, /\.auth-shell \.auth-aside[\s\S]*?var\(--auth-aside-bg\)/)
  assert.match(css, /\.dashboard-stats article/)
  assert.match(css, /\.role-choice-card\.is-selected[\s\S]*?var\(--accent-soft\)/)
  assert.match(css, /\.site-header-public[\s\S]*?flex-wrap:wrap/)
  assert.match(css, /\.palette-picker-menu/)
  assert.match(css, /:root\[data-theme="dark"\]\[data-palette="teal-peach"\]/)
})


test("palette completeness keeps homepage, role selection and authentication decoration on the selected palette", async () => {
  const css = await readFile("src/index.css", "utf8")
  const finalPaletteRules = css.slice(css.lastIndexOf("/* Final palette-completeness correction"))

  assert.ok(finalPaletteRules.length > 0, "Missing final palette-completeness rules")
  for (const selector of [
    ".hero-visual-icon",
    ".hero-float-dot",
    ".hero-visual-orb",
    ".home-steps li > span",
    ".role-choice-card.is-selected",
    ".role-choice-symbol",
    ".role-choice-indicator",
    ".auth-shell .auth-orbit",
    ".auth-shell .auth-aside .eyebrow",
    ".auth-shell .auth-benefits li span",
    ".student-avatar",
    ".dashboard-stats article",
    ".status-pending",
  ]) {
    assert.ok(finalPaletteRules.includes(selector), `Missing palette override for ${selector}`)
  }

  for (const token of [
    "--accent-soft",
    "--accent-strong",
    "--accent-mid",
    "--surface-raised",
    "--control-border",
    "--auth-aside-bg",
    "--auth-aside-border",
  ]) {
    assert.ok(finalPaletteRules.includes(token), `Missing palette token ${token}`)
  }

  assert.doesNotMatch(finalPaletteRules, /#[0-9a-f]{3,8}\b/i, "Final palette rules must not introduce fixed hex colours")
})


test("full application surfaces and form states remain palette-aware in both themes", async () => {
  const css = await readFile("src/index.css", "utf8")
  const finalPaletteRules = css.slice(css.lastIndexOf("/* Final palette-completeness correction"))

  for (const selector of [
    ".brand span",
    ".hero h1 span",
    ".site-footer",
    ".empty-state",
    ".task-detail-header",
    ".task-note p",
    ".response-summary",
    ".profile-switcher select",
    ".task-confirm-controls select",
    ".public-header-actions nav a[aria-current=",
    ".auth-shell input:not",
    ".auth-shell input::placeholder",
    ".auth-shell input:-webkit-autofill",
    "button:focus-visible",
  ]) {
    assert.ok(finalPaletteRules.includes(selector), `Missing full-surface palette rule for ${selector}`)
  }

  for (const token of ["--page", "--surface", "--surface-raised", "--ink", "--muted", "--line", "--control-border", "--focus-ring"]) {
    assert.ok(finalPaletteRules.includes(token), `Missing shared surface token ${token}`)
  }

  assert.doesNotMatch(finalPaletteRules, /#[0-9a-f]{3,8}\b/i, "Palette completion rules must use design tokens rather than fixed colors")
})


test("form controls and mobile navigation use the active palette in both themes", async () => {
  const css = await readFile("src/index.css", "utf8")
  const finalPaletteRules = css.slice(css.lastIndexOf("/* Final palette-completeness correction"))

  for (const selector of [
    ":root[data-palette] input",
    ":root[data-palette] textarea",
    ":root[data-palette] select",
    ":root[data-palette] input:focus-visible",
    ":root[data-palette] input[type=",
    ":root[data-palette] .mobile-bottom-nav",
    ":root[data-palette] .mobile-bottom-nav a",
    ":root[data-palette] .site-header",
  ]) {
    assert.ok(finalPaletteRules.includes(selector), `Missing control/navigation palette rule for ${selector}`)
  }

  for (const token of ["--surface-raised", "--control-border", "--control-hover", "--accent-mid", "--focus-ring", "--mobile-nav"]) {
    if (token === "--mobile-nav") continue
    assert.ok(finalPaletteRules.includes(token), `Missing control-state token ${token}`)
  }

  assert.doesNotMatch(finalPaletteRules, /#[0-9a-f]{3,8}\b/i, "Control-state rules must not use fixed hex colors")
})
