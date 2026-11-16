import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

export type Theme = "light" | "dark"
export type PaletteId = "royal-blue" | "charcoal-red" | "nude-mocha" | "teal-peach"

export const THEME_PALETTES: { id: PaletteId; name: string; colors: [string, string, string] }[] = [
  { id: "royal-blue", name: "Royal Blue", colors: ["#F7F9FC", "#2457D6", "#17233C"] },
  { id: "charcoal-red", name: "Charcoal & Red", colors: ["#1C1C1C", "#EDE6D8", "#B3261E"] },
  { id: "nude-mocha", name: "Nude & Mocha", colors: ["#F2E4DA", "#5E4B42", "#B87866"] },
  { id: "teal-peach", name: "Teal & Peach", colors: ["#F4F8FA", "#0F3D47", "#F59E7B"] },
]

type ThemeContextValue = {
  theme: Theme
  palette: PaletteId
  setTheme: (theme: Theme) => void
  setPalette: (palette: PaletteId) => void
  toggleTheme: () => void
}
const ThemeContext = createContext<ThemeContextValue | null>(null)

function getInitialTheme(): Theme {
  try {
    return window.localStorage.getItem("tutorinn-theme") === "dark" ? "dark" : "light"
  } catch {
    return "light"
  }
}

function getInitialPalette(): PaletteId {
  try {
    const saved = window.localStorage.getItem("tutorinn-palette")
    return THEME_PALETTES.some(palette => palette.id === saved) ? saved as PaletteId : "royal-blue"
  } catch {
    return "royal-blue"
  }
}

function applyTheme(theme: Theme, palette: PaletteId) {
  const root = document.documentElement
  root.dataset.theme = theme
  root.dataset.palette = palette
  root.style.colorScheme = theme

  // Keep the browser toolbar/status area aligned with the active TutorInn theme.
  const themeColors: Record<PaletteId, string> = {
    "royal-blue": theme === "dark" ? "#17191D" : "#F7F9FC",
    "charcoal-red": theme === "dark" ? "#171717" : "#EDE6D8",
    "nude-mocha": theme === "dark" ? "#211B19" : "#F2E4DA",
    "teal-peach": theme === "dark" ? "#14272B" : "#F4F8FA",
  }
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", themeColors[palette])

  try {
    window.localStorage.setItem("tutorinn-theme", theme)
    window.localStorage.setItem("tutorinn-palette", palette)
  } catch {
    // Theme switching remains available for this session when storage is unavailable.
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme)
  const [palette, setPaletteState] = useState<PaletteId>(getInitialPalette)

  useEffect(() => {
    applyTheme(theme, palette)
  }, [theme, palette])

  function setTheme(nextTheme: Theme) {
    // Apply the visual theme synchronously so there is no frame of stale styling.
    applyTheme(nextTheme, palette)
    setThemeState(nextTheme)
  }

  function setPalette(nextPalette: PaletteId) {
    applyTheme(theme, nextPalette)
    setPaletteState(nextPalette)
  }

  function toggleTheme() {
    setTheme(theme === "dark" ? "light" : "dark")
  }

  return <ThemeContext.Provider value={{ theme, palette, setTheme, setPalette, toggleTheme }}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used inside ThemeProvider")
  return context
}
