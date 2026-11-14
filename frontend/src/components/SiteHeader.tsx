import { useAuth } from "../context/AuthContext"

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
    { label: "Availability", href: "/profile#availability" },
    { label: "My profile", href: "/profile" },
  ]
  return [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Review", href: "/admin#review-queue" },
    { label: "Settings", href: "/profile" },
  ]
}

export function SiteHeader() {
  const { account, logout } = useAuth()
  const items = account ? navigationFor(account.role) : []
  const currentLocation = window.location.pathname + window.location.hash

  return (
    <header className={`site-header ${account ? "site-header-authenticated" : "site-header-public"}`}>
      <a className="brand" href="/" aria-label="TutorInn home">TutorInn<span>.</span></a>
      {account ? (
        <>
          <nav className="desktop-nav" aria-label={`${account.role} navigation`}>
            {items.map(item => (
              <a key={item.href} href={item.href} aria-current={currentLocation === item.href || (!item.href.includes("#") && currentLocation === item.href) ? "page" : undefined}>
                {item.label}
              </a>
            ))}
          </nav>
          <div className="header-tools">
            <span className="account-email" title={account.email}>{account.email}</span>
            <button className="button secondary header-signout" type="button" onClick={() => { void logout().finally(() => window.location.assign("/")) }}>
              Sign out
            </button>
          </div>
        </>
      ) : (
        <div className="public-header-actions">
          <nav aria-label="Public navigation"><a href="/about">About</a></nav>
          <a className="text-link" href="/login">Log in</a>
          <a className="button primary" href="/register">Create account</a>
        </div>
      )}
    </header>
  )
}
