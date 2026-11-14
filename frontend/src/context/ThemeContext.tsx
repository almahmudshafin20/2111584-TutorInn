import { createContext, useContext, useEffect, type ReactNode } from "react"

type ThemeContextValue = { theme: "light"; toggleTheme: () => void }
const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.dataset.theme = "light"
    document.documentElement.style.colorScheme = "light"
    try { window.localStorage.setItem("tutorinn-theme", "light") } catch {
      // The initial release stays light even when browser storage is unavailable.
    }
  }, [])

  return <ThemeContext.Provider value={{ theme: "light", toggleTheme: () => undefined }}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used inside ThemeProvider")
  return context
}
