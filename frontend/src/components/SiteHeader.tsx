import { useAuth } from "../context/AuthContext"
import { THEME_PALETTES, useTheme } from "../context/ThemeContext"

type NavItem = { label: string; href: string }

function navigationFor(role: "student" | "tutor" | "admin" | "moderator"): NavItem[] {
  if (role === "student") return [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Find tutors", href: "/dashboard#find-tutors" },
    { label: "My responses", href: "/dashboard#my-responses" },
    { label: "My profile", href: "/profile" },
  ]
  if (role === "moderator") return [
    { label: "Home", href: "/admin/password-resets" },
    { label: "Password resets", href: "/admin/password-resets" },
    { label: "Verify email", href: "/verify-email" },
  ]
  if (role === "tutor") return [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Requests", href: "/dashboard#requests" },
    { label: "My responses", href: "/dashboard#my-responses" },
    { label: "My profile", href: "/profile" },
  ]
  return [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Review", href: "/admin?tab=tutors" },
    { label: "Settings", href: "/profile" },
  ]
}

function ThemeSwitcher() {
  const { theme, setTheme } = useTheme()
  return (
    <div className={`theme-switcher ${theme === "dark" ? "is-dark" : "is-light"}`} data-theme={theme} role="group" aria-label="Choose color theme">
      <button
        className={`theme-switch-option ${theme === "light" ? "is-active" : ""}`}
        type="button"
        onClick={() => setTheme("light")}
        aria-label="Use light mode"
        aria-pressed={theme === "light"}
      >
        <span aria-hidden="true">☀</span>
        <span>Light</span>
      </button>
      <button
        className={`theme-switch-option ${theme === "dark" ? "is-active" : ""}`}
        type="button"
        onClick={() => setTheme("dark")}
        aria-label="Use dark mode"
        aria-pressed={theme === "dark"}
      >
        <span aria-hidden="true">☾</span>
        <span>Dark</span>
      </button>
    </div>
  )
}

function ThemePalettePicker() {
  const { palette, setPalette } = useTheme()
  return (
    <details className="palette-picker">
      <summary className="palette-picker-trigger" aria-label="Choose color palette">
        <span aria-hidden="true">◉</span>
        <span>Colors</span>
      </summary>
      <div className="palette-picker-menu" role="group" aria-label="Color palettes">
        {THEME_PALETTES.map(option => (
          <button
            key={option.id}
            className="palette-picker-option"
            type="button"
            onClick={() => setPalette(option.id)}
            aria-pressed={palette === option.id}
          >
            <span className="palette-swatches" aria-hidden="true">
              {option.colors.map(color => <span key={color} style={{ backgroundColor: color }} />)}
            </span>
            <span>{option.name}</span>
            {palette === option.id ? <span className="palette-check" aria-hidden="true">✓</span> : null}
          </button>
        ))}
      </div>
    </details>
  )
}

export function SiteHeader() {
  const { account, logout } = useAuth()
  const items = account ? navigationFor(account.role) : []
  const currentPath = window.location.pathname.replace(/\/+$/, "") || "/"
  const isCurrentNavItem = (href: string) => {
    const target = new URL(href, window.location.origin)
    const targetPath = target.pathname.replace(/\/+$/, "") || "/"
    if (targetPath !== currentPath) return false
    if (target.search && target.search !== window.location.search) return false
    if (target.hash) return target.hash === window.location.hash
    return !window.location.hash
  }
  const isPublicPage = (href: string) => currentPath === href

  return (
    <header className={`site-header ${account ? "site-header-authenticated" : "site-header-public"}`}>
      <a className="brand" href="/" aria-label="TutorInn home">TutorInn<span>.</span></a>
      {account ? (
        <>
          <nav className="desktop-nav" aria-label={`${account.role} navigation`}>
            {items.map(item => (
              <a key={item.href} href={item.href} aria-current={isCurrentNavItem(item.href) ? "page" : undefined}>
                {item.label}
              </a>
            ))}
          </nav>
          <div className="header-tools">
            <ThemePalettePicker />
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
            <a href="/" aria-current={isPublicPage("/") ? "page" : undefined}>Home</a>
            <a href="/about" aria-current={isPublicPage("/about") ? "page" : undefined}>About</a>
            <a className="button nav-login" href="/login" aria-current={isPublicPage("/login") ? "page" : undefined}>Login</a>
          </nav>
          <a className="button primary nav-register" href="/register">Create Account</a>
          <ThemePalettePicker />
          <ThemeSwitcher />
        </div>
      )}
    </header>
  )
}
