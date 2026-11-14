import { useEffect, useState } from "react"
import { useTheme } from "../context/ThemeContext"
import { listAllProfiles } from "../services/profiles"
import { saveSelectedProfile, selectedProfile } from "../services/session"
import { useSelectedProfile } from "../hooks/useSelectedProfile"
import type { Profile } from "../types/domain"

export function SiteHeader() {
  const { theme, toggleTheme } = useTheme()
  const [profiles, setProfiles] = useState<Profile[]>([])
  const active = useSelectedProfile()

  async function loadProfiles() {
    try {
      const all = await listAllProfiles()
      setProfiles(all)
      const current = selectedProfile()
      if (current && !all.some(profile =>
        profile.id === current.id &&
        (current.type === "student" ? "education_level" in profile : "teaching_level" in profile)
      )) {
        saveSelectedProfile(null)
      }
    } catch {
      // Profile directories display their own request errors.
    }
  }

  useEffect(() => {
    void loadProfiles()
    const refresh = () => void loadProfiles()
    window.addEventListener("tutorinn-profile-change", refresh)
    return () => window.removeEventListener("tutorinn-profile-change", refresh)
  }, [])

  return (
    <header className="site-header">
      <a className="brand" href="/">TutorInn<span>.</span></a>
      <nav aria-label="Main navigation">
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/posts">Tutoring Hub</a>
        <a href="/task-details">My responses</a>
        <a href="/admin">Admin review</a>
      </nav>
      <div className="header-tools">
        <label className="profile-switcher">
          <span>Demo profile</span>
          <select
            aria-label="Selected demo profile"
            value={active ? `${active.type}:${active.id}` : ""}
            onChange={event => {
              const [type, id] = event.target.value.split(":")
              saveSelectedProfile(
                type === "student" || type === "tutor"
                  ? { type, id: Number(id) }
                  : null
              )
            }}
          >
            <option value="">Select profile</option>
            {profiles.map(profile => {
              const type = "education_level" in profile ? "student" : "tutor"
              return (
                <option key={`${type}:${profile.id}`} value={`${type}:${profile.id}`}>
                  {profile.full_name} · {type === "student" ? "Student" : "Tutor"} #{profile.id}
                </option>
              )
            })}
          </select>
        </label>
        <button
          className="theme-toggle"
          type="button"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        >
          <span aria-hidden="true">{theme === "dark" ? "☀" : "☾"}</span>
          <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
        </button>
      </div>
    </header>
  )
}
