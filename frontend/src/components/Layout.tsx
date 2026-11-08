import type { ReactNode } from "react"
import { useTheme } from "../context/ThemeContext"

function Header() {
  const { theme, toggleTheme } = useTheme()
  const nextTheme = theme === "dark" ? "light" : "dark"

  return (
    <header className="site-header">
      <a className="brand" href="/">TutorInn<span>.</span></a>
      <nav aria-label="Main navigation">
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/posts">Tutoring Hub</a>
        <a href="/task-details">Task Details</a>
      </nav>
      <button
        className="theme-toggle"
        type="button"
        onClick={toggleTheme}
        aria-label={`Switch to ${nextTheme} theme`}
        title={`Switch to ${nextTheme} theme`}
      >
        <span aria-hidden="true">{theme === "dark" ? "☀" : "☾"}</span>
        <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
      </button>
    </header>
  )
}

function Footer() {
  return <footer className="site-footer">TutorInn · A simple place to connect learners and tutors.</footer>
}

export function Layout({ children }: { children: ReactNode }) {
  return <><Header /><main className="page">{children}</main><Footer /></>
}
