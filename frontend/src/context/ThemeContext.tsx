import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

type Theme = "light" | "dark"
type ThemeContextValue = { theme: Theme; toggleTheme: () => void }
const ThemeContext = createContext<ThemeContextValue | null>(null)

function getInitialTheme(): Theme {
  try {
    return window.localStorage.getItem("tutorinn-theme") === "dark" ? "dark" : "light"
  } catch {
    return "light"
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    const root = document.documentElement
    root.dataset.theme = theme
    root.style.colorScheme = theme

    // Keep the browser toolbar/status area aligned with the active TutorInn theme.
    const themeColor = theme === "dark" ? "#101c27" : "#f5f9fd"
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", themeColor)

    try {
      window.localStorage.setItem("tutorinn-theme", theme)
    } catch {
      // Theme switching remains available for this session when storage is unavailable.
    }
  }, [theme])

  function toggleTheme() {
    setTheme(current => current === "dark" ? "light" : "dark")
  }

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used inside ThemeProvider")
  return context
}
