import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

type Theme = "light" | "dark"
type ThemeContextValue = { theme: Theme; setTheme: (theme: Theme) => void; toggleTheme: () => void }
const ThemeContext = createContext<ThemeContextValue | null>(null)

function getInitialTheme(): Theme {
  try {
    return window.localStorage.getItem("tutorinn-theme") === "dark" ? "dark" : "light"
  } catch {
    return "light"
  }
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  root.dataset.theme = theme
  root.style.colorScheme = theme

  // Keep the browser toolbar/status area aligned with the active TutorInn theme.
  const themeColor = theme === "dark" ? "#17191D" : "#F6F9FC"
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", themeColor)

  try {
    window.localStorage.setItem("tutorinn-theme", theme)
  } catch {
    // Theme switching remains available for this session when storage is unavailable.
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  function setTheme(nextTheme: Theme) {
    // Apply the visual theme synchronously so there is no frame of stale styling.
    applyTheme(nextTheme)
    setThemeState(nextTheme)
  }

  function toggleTheme() {
    setTheme(theme === "dark" ? "light" : "dark")
  }

  return <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used inside ThemeProvider")
  return context
}
