export type SelectedProfile = { id: number; type: "student" | "tutor" }
const PROFILE_ID_KEY = "tutorinn-profile-id"
const PROFILE_TYPE_KEY = "tutorinn-profile-type"

export function selectedProfile(): SelectedProfile | null {
  const id = Number(window.localStorage.getItem(PROFILE_ID_KEY))
  const type = window.localStorage.getItem(PROFILE_TYPE_KEY)
  return Number.isInteger(id) && id > 0 && (type === "student" || type === "tutor") ? { id, type } : null
}

export function saveSelectedProfile(profile: SelectedProfile | null): void {
  if (profile) {
    window.localStorage.setItem(PROFILE_ID_KEY, String(profile.id))
    window.localStorage.setItem(PROFILE_TYPE_KEY, profile.type)
  } else {
    window.localStorage.removeItem(PROFILE_ID_KEY)
    window.localStorage.removeItem(PROFILE_TYPE_KEY)
  }
  window.dispatchEvent(new Event("tutorinn-profile-change"))
}
