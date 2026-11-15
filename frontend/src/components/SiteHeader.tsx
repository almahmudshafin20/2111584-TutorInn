import { useAuth } from "../context/AuthContext"
import { useTheme } from "../context/ThemeContext"

type NavItem = { label: string; href: string }

function navigationFor(role: "student" | "tutor" | "admin"): NavItem[] {
  if (role === "student") return [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Find tutors", href: "/dashboard#find-tutors" },
    { label: "My responses", href: "/dashboard#my-responses" },
    { label: "My profile", href: "/profile" },
  ]
  if (role === "tutor") return [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Requests", href: "/dashboard#requests" },
    { label: "My responses", href: "/dashboard#my-responses" },
    { label: "My profile", href: "/profile" },
  ]
  return [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Review", href: "/admin#review-queue" },
    { label: "Settings", href: "/profile" },
  ]
}

function ThemeSwitcher() {
  const { theme, toggleTheme } = useTheme()
  return (
    <div className="theme-switcher" role="group" aria-label="Choose color theme">
      <button
        className={`theme-switch-option ${theme === "light" ? "is-active" : ""}`}
        type="button"
        onClick={() => { if (theme !== "light") toggleTheme() }}
        aria-label="Use light mode"
        aria-pressed={theme === "light"}
      >
        <span aria-hidden="true">☀</span>
        <span>Light</span>
      </button>
      <button
        className={`theme-switch-option ${theme === "dark" ? "is-active" : ""}`}
        type="button"
        onClick={() => { if (theme !== "dark") toggleTheme() }}
        aria-label="Use dark mode"
        aria-pressed={theme === "dark"}
      >
        <span aria-hidden="true">☾</span>
        <span>Dark</span>
      </button>
    </div>
  )
}

export function SiteHeader() {
  const { account, logout } = useAuth()
  const items = account ? navigationFor(account.role) : []
  const currentPath = window.location.pathname
  const currentLocation = currentPath + window.location.hash

  return (
    <header className={`site-header ${account ? "site-header-authenticated" : "site-header-public"}`}>
      <a className="brand" href="/" aria-label="TutorInn home">TutorInn<span>.</span></a>
      {account ? (
        <>
          <nav className="desktop-nav" aria-label={`${account.role} navigation`}>
            {items.map(item => (
              <a key={item.href} href={item.href} aria-current={(item.href.includes("#") ? currentLocation === item.href : currentPath === item.href && !window.location.hash) ? "page" : undefined}>
                {item.label}
              </a>
            ))}
          </nav>
          <div className="header-tools">
            <ThemeSwitcher />
            <span className="account-email" title={account.email}>{account.email}</span>
            <button className="button secondary header-signout" type="button" onClick={() => { void logout().finally(() => window.location.assign("/")) }}>
              Sign out
            </button>
          </div>
        </>
      ) : (
        <div className="public-header-actions">
          <nav aria-label="Public navigation">
            <a href="/" aria-current={currentPath === "/" ? "page" : undefined}>Home</a>
            <a href="/about" aria-current={currentPath === "/about" ? "page" : undefined}>About</a>
          </nav>
          <a className="button nav-login" href="/login">Login</a>
          <a className="button primary nav-register" href="/register">Create Account</a>
          <ThemeSwitcher />
        </div>
      )}
    </header>
  )
}
