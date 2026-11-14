import { useEffect, useState } from "react"
import { selectedProfile } from "../services/session"
import type { SelectedProfile } from "../types/domain"

export function useSelectedProfile(): SelectedProfile | null {
  const [active, setActive] = useState<SelectedProfile | null>(selectedProfile)

  useEffect(() => {
    const sync = () => setActive(selectedProfile())
    window.addEventListener("tutorinn-profile-change", sync)
    return () => window.removeEventListener("tutorinn-profile-change", sync)
  }, [])

  return active
}
