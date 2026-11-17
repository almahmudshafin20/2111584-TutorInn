import assert from "node:assert/strict"
import { after, before, test } from "node:test"
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { resolve } from "node:path"
import { loadWithRspack } from "./rspack-test-utils.mjs"

import { readFile } from "node:fs/promises"

let cleanup
let DashboardPage
let dashboardService
let apiModule

before(async () => {
  const loaded = await loadWithRspack({
    source: `
      import DashboardPage from ${JSON.stringify(resolve(process.cwd(), "src/pages/DashboardPage.tsx"))};
      import * as dashboardService from ${JSON.stringify(resolve(process.cwd(), "src/api/dashboard.ts"))};
      import * as apiModule from ${JSON.stringify(resolve(process.cwd(), "src/api/api.ts"))};
      export { DashboardPage, dashboardService, apiModule };
    `,
    aliases: {
      "../context/AuthContext": 'export function useAuth() { return globalThis.__TUTORINN_TEST_AUTH__ ?? { account: null, loading: false } }',
      "../layouts/AppLayout": 'import React from "react"; export function AppLayout({ children }) { return React.createElement("main", null, children) }',
      "./StudentDashboardPage": 'import React from "react"; export default function StudentDashboardPage() { return React.createElement("h1", null, "Student dashboard test view") }',
      "./TutorDashboardPage": 'import React from "react"; export default function TutorDashboardPage() { return React.createElement("h1", null, "Tutor dashboard test view") }',
    },
  })
  cleanup = loaded.cleanup
  ;({ DashboardPage, dashboardService, apiModule } = loaded.exports)
})

after(async () => {
  delete globalThis.__TUTORINN_TEST_AUTH__
  await cleanup?.()
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
  assert.match(header, /<a href="\/" aria-current=/)
  assert.match(header, /<a href="\/about" aria-current=/)
  assert.match(header, /<a className="button nav-login" href="\/login" aria-current=/)
  assert.match(css, /nav a\[aria-current="page"\]::after/)
  assert.match(css, /background:\s*var\(--public-nav-underline\)/)
  assert.match(css, /\.theme-switcher\s*\{[\s\S]*?overflow:\s*hidden/)
  assert.match(css, /focus-visible[\s\S]*?var\(--focus-ring\)/)
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

  for (const token of ["--surface-raised", "--control-border", "--control-hover", "--accent-mid", "--focus-ring"]) {
    assert.ok(finalPaletteRules.includes(token), `Missing control-state token ${token}`)
  }

  assert.doesNotMatch(finalPaletteRules, /#[0-9a-f]{3,8}\b/i, "Control-state rules must not use fixed hex colors")
})


test("remaining headings, text selection and legacy theme controls use palette tokens", async () => {
  const css = await readFile("src/index.css", "utf8")
  const finalPaletteRules = css.slice(css.lastIndexOf("/* Final palette-completeness correction"))

  for (const selector of [
    ":root[data-palette] h1",
    ":root[data-palette] h2",
    ":root[data-palette] h3",
    ":root[data-palette] h4",
    ":root[data-palette] ::selection",
    ":root[data-palette] .site-header nav a",
    ":root[data-palette] .claim-details summary",
    ":root[data-palette] .theme-toggle",
  ]) {
    assert.ok(finalPaletteRules.includes(selector), `Missing final audit rule for ${selector}`)
  }

  assert.doesNotMatch(finalPaletteRules, /#[0-9a-f]{3,8}\b/i, "Final audit rules must use palette tokens")
})


test("Home hero illustration is integrated as an accessible theme-aware SVG", async () => {
  const [home, illustration, css, theme] = await Promise.all([
    readFile("src/pages/HomePage.tsx", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/index.css", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])

  assert.match(home, /import HomeHeroIllustration from "\.\.\/components\/HomeHeroIllustration"/)
  assert.match(home, /<HomeHeroIllustration\s*\/>/)
  assert.match(illustration, /role="img"/)
  assert.match(illustration, /aria-labelledby=/)
  assert.match(illustration, /laptop|Laptop/)
  assert.match(illustration, /open book|Open book/)
  assert.match(illustration, /notebook|Notebook/)
  assert.match(css, /\.home-hero-illustration\s*\{[\s\S]*?width:\s*min\(100%,\s*610px\)/)
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(css, /--illustration-shadow:\s*color-mix/)
  assert.match(theme, /root\.dataset\.theme = theme/)
  assert.match(theme, /root\.dataset\.palette = palette/)
  assert.doesNotMatch(illustration, /#[0-9a-f]{3,8}\b/i, "Illustration fills must use theme variables, not fixed palette colours")
})

test("Home hero illustration supports all eight palette and day/night combinations", async () => {
  const [theme, css, illustration] = await Promise.all([
    readFile("src/context/ThemeContext.tsx", "utf8"),
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
  ])
  const palettes = ["royal-blue", "charcoal-red", "nude-mocha", "teal-peach"]

  assert.match(theme, /export type Theme = "light" \| "dark"/)
  assert.match(theme, /export type PaletteId = "royal-blue" \| "charcoal-red" \| "nude-mocha" \| "teal-peach"/)
  for (const palette of palettes) {
    assert.ok(css.includes(`:root[data-palette="${palette}"]`), `Missing light palette tokens for ${palette}`)
    assert.ok(css.includes(`:root[data-theme="dark"][data-palette="${palette}"]`), `Missing dark palette tokens for ${palette}`)
  }

  for (const token of [
    "--illustration-accent",
    "--illustration-accent-strong",
    "--illustration-accent-mid",
    "--illustration-highlight",
    "--illustration-ink",
    "--illustration-muted",
    "--illustration-line",
    "--illustration-surface",
    "--illustration-surface-raised",
    "--illustration-warm",
    "--illustration-shadow",
  ]) {
    assert.ok(css.includes(token), `Missing illustration token ${token}`)
    assert.ok(illustration.includes(`var(${token})`), `SVG does not consume ${token}`)
  }

  assert.match(css, /@media\s*\(max-width:\s*760px\)[\s\S]*?\.home-hero/)
  assert.match(css, /prefers-reduced-motion:\s*reduce/)
})

test("Home hero illustration visual contract — Royal Blue Day", async () => {
  const [css, illustration, theme] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.ok(theme.includes('"royal-blue"'), "The palette must be selectable")
  assert.ok(css.includes(':root[data-palette="royal-blue"]'), "The palette surface tokens must exist")
  assert.ok(css.includes(':root[data-palette="royal-blue"]'), "The Day-mode palette tokens must exist")
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-ink:\s*var\(--ink\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(illustration, /fill="var\(--illustration-(?:accent|surface|highlight|ink|line|shadow)/)
  assert.match(illustration, /stroke="var\(--illustration-/)
})


test("Home hero illustration visual contract — Royal Blue Night", async () => {
  const [css, illustration, theme] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.ok(theme.includes('"royal-blue"'), "The palette must be selectable")
  assert.ok(css.includes(':root[data-palette="royal-blue"]'), "The palette surface tokens must exist")
  assert.ok(css.includes(':root[data-theme="dark"][data-palette="royal-blue"]'), "The Night-mode palette tokens must exist")
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-ink:\s*var\(--ink\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(illustration, /fill="var\(--illustration-(?:accent|surface|highlight|ink|line|shadow)/)
  assert.match(illustration, /stroke="var\(--illustration-/)
})


test("Home hero illustration visual contract — Charcoal & Red Day", async () => {
  const [css, illustration, theme] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.ok(theme.includes('"charcoal-red"'), "The palette must be selectable")
  assert.ok(css.includes(':root[data-palette="charcoal-red"]'), "The palette surface tokens must exist")
  assert.ok(css.includes(':root[data-palette="charcoal-red"]'), "The Day-mode palette tokens must exist")
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-ink:\s*var\(--ink\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(illustration, /fill="var\(--illustration-(?:accent|surface|highlight|ink|line|shadow)/)
  assert.match(illustration, /stroke="var\(--illustration-/)
})


test("Home hero illustration visual contract — Charcoal & Red Night", async () => {
  const [css, illustration, theme] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.ok(theme.includes('"charcoal-red"'), "The palette must be selectable")
  assert.ok(css.includes(':root[data-palette="charcoal-red"]'), "The palette surface tokens must exist")
  assert.ok(css.includes(':root[data-theme="dark"][data-palette="charcoal-red"]'), "The Night-mode palette tokens must exist")
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-ink:\s*var\(--ink\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(illustration, /fill="var\(--illustration-(?:accent|surface|highlight|ink|line|shadow)/)
  assert.match(illustration, /stroke="var\(--illustration-/)
})


test("Home hero illustration visual contract — Nude & Mocha Day", async () => {
  const [css, illustration, theme] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.ok(theme.includes('"nude-mocha"'), "The palette must be selectable")
  assert.ok(css.includes(':root[data-palette="nude-mocha"]'), "The palette surface tokens must exist")
  assert.ok(css.includes(':root[data-palette="nude-mocha"]'), "The Day-mode palette tokens must exist")
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-ink:\s*var\(--ink\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(illustration, /fill="var\(--illustration-(?:accent|surface|highlight|ink|line|shadow)/)
  assert.match(illustration, /stroke="var\(--illustration-/)
})


test("Home hero illustration visual contract — Nude & Mocha Night", async () => {
  const [css, illustration, theme] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.ok(theme.includes('"nude-mocha"'), "The palette must be selectable")
  assert.ok(css.includes(':root[data-palette="nude-mocha"]'), "The palette surface tokens must exist")
  assert.ok(css.includes(':root[data-theme="dark"][data-palette="nude-mocha"]'), "The Night-mode palette tokens must exist")
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-ink:\s*var\(--ink\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(illustration, /fill="var\(--illustration-(?:accent|surface|highlight|ink|line|shadow)/)
  assert.match(illustration, /stroke="var\(--illustration-/)
})


test("Home hero illustration visual contract — Teal & Peach Day", async () => {
  const [css, illustration, theme] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.ok(theme.includes('"teal-peach"'), "The palette must be selectable")
  assert.ok(css.includes(':root[data-palette="teal-peach"]'), "The palette surface tokens must exist")
  assert.ok(css.includes(':root[data-palette="teal-peach"]'), "The Day-mode palette tokens must exist")
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-ink:\s*var\(--ink\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(illustration, /fill="var\(--illustration-(?:accent|surface|highlight|ink|line|shadow)/)
  assert.match(illustration, /stroke="var\(--illustration-/)
})


test("Home hero illustration visual contract — Teal & Peach Night", async () => {
  const [css, illustration, theme] = await Promise.all([
    readFile("src/index.css", "utf8"),
    readFile("src/components/HomeHeroIllustration.tsx", "utf8"),
    readFile("src/context/ThemeContext.tsx", "utf8"),
  ])
  assert.ok(theme.includes('"teal-peach"'), "The palette must be selectable")
  assert.ok(css.includes(':root[data-palette="teal-peach"]'), "The palette surface tokens must exist")
  assert.ok(css.includes(':root[data-theme="dark"][data-palette="teal-peach"]'), "The Night-mode palette tokens must exist")
  assert.match(css, /--illustration-accent:\s*var\(--accent\)/)
  assert.match(css, /--illustration-ink:\s*var\(--ink\)/)
  assert.match(css, /--illustration-surface:\s*var\(--surface\)/)
  assert.match(illustration, /fill="var\(--illustration-(?:accent|surface|highlight|ink|line|shadow)/)
  assert.match(illustration, /stroke="var\(--illustration-/)
})


test("About page contains six complete sections and uses no human imagery", async () => {
  const about = await readFile("src/pages/AboutPage.tsx", "utf8")
  const css = await readFile("src/index.css", "utf8")
  for (const section of ["ABOUT TUTORINN", "OUR MISSION", "HOW TUTORINN WORKS", "WHAT MAKES TUTORINN USEFUL", "DESIGNED FOR TWO ROLES", "YOUR NEXT STEP"]) {
    assert.ok(about.includes(section), `About page is missing section: ${section}`)
  }
  for (const className of ["about-hero", "about-mission-panel", "about-steps", "about-benefit-grid", "about-role-grid", "about-closing"]) {
    assert.ok(about.includes(className), `About page is missing layout: ${className}`)
    assert.ok(css.includes(`.${className}`), `About page is missing styles: ${className}`)
  }
  assert.match(about, /AboutLearningIllustration/)
  assert.match(about, /about-dashboard/)
  assert.match(about, /about-book-stack/)
  assert.doesNotMatch(about, /<img|portrait|avatar|person|people|human|\bface\b/i)
  assert.match(css, /:root\[data-palette\] \.about-hero/)
  assert.match(css, /var\(--accent-soft\)/)
})
