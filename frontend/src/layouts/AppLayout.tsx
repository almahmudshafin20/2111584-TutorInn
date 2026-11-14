import type { ReactNode } from "react"
import { useAuth } from "../context/AuthContext"
import { SiteFooter } from "../components/SiteFooter"
import { SiteHeader } from "../components/SiteHeader"

const mobileItems = {
  student: [
    { label: "Home", short: "⌂", href: "/dashboard" },
    { label: "Tutors", short: "⌕", href: "/dashboard#find-tutors" },
    { label: "Responses", short: "▤", href: "/dashboard#my-responses" },
    { label: "Profile", short: "◉", href: "/profile" },
  ],
  tutor: [
    { label: "Home", short: "⌂", href: "/dashboard" },
    { label: "Requests", short: "▤", href: "/dashboard#requests" },
    { label: "Responses", short: "▤", href: "/dashboard#my-responses" },
    { label: "Profile", short: "◉", href: "/profile" },
  ],
  admin: [
    { label: "Home", short: "⌂", href: "/dashboard" },
    { label: "Review", short: "✓", href: "/admin#review-queue" },
    { label: "Settings", short: "⚙", href: "/profile" },
  ],
} as const

function MobileBottomNav({ role }: { role: "student" | "tutor" | "admin" }) {
  const currentPath = window.location.pathname
  const current = currentPath + window.location.hash
  return (
    <nav className="mobile-bottom-nav" aria-label="Mobile workspace navigation">
      {mobileItems[role].map(item => (
        <a key={item.href} href={item.href} aria-current={(item.href.includes("#") ? current === item.href : currentPath === item.href && !window.location.hash) ? "page" : undefined}>
          <span className="mobile-nav-icon" aria-hidden="true">{item.short}</span>
          <span>{item.label}</span>
        </a>
      ))}
    </nav>
  )
}

export function AppLayout({ children }: { children: ReactNode }) {
  const { account } = useAuth()
  return (
    <>
      <SiteHeader />
      <main className="page">{children}</main>
      <SiteFooter />
      {account && <MobileBottomNav role={account.role} />}
    </>
  )
}
