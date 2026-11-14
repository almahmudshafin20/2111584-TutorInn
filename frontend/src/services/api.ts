let accessToken: string | null = null
export function setAccessToken(token: string | null): void { accessToken = token }

export async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const authenticatedRoute = url.startsWith("/api/auth/") || url.startsWith("/api/me/") || url.startsWith("/api/dashboard") || url.startsWith("/api/requests")
  const profileId = authenticatedRoute ? null : window.localStorage.getItem("tutorinn-profile-id")
  const profileType = authenticatedRoute ? null : window.localStorage.getItem("tutorinn-profile-type")
  const headers = new Headers(init?.headers)
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  if (profileId && profileType) { headers.set("X-TutorInn-Profile-ID", profileId); headers.set("X-TutorInn-Profile-Type", profileType) }
  if (accessToken && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${accessToken}`)
  const response = await fetch(url, { ...init, credentials: init?.credentials ?? "same-origin", headers })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === "string") message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((item: { loc?: unknown[]; msg?: string }) => (Array.isArray(item.loc) ? item.loc.filter(part => part !== "body").join(".") + ": " : "") + (item.msg ?? "Invalid value")).join("; ")
      else if (typeof body.message === "string") message = body.message
    } catch { /* retain HTTP status */ }
    if (response.status === 401 && accessToken && !url.startsWith("/api/auth/")) { accessToken = null; window.dispatchEvent(new Event("tutorinn-auth-invalid")) }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
export function getAdminHeaders(): HeadersInit {
  let key = window.sessionStorage.getItem("tutorinn-admin-key")
  if (!key) { key = window.prompt("Enter the configured TutorInn Admin API key"); if (!key) throw new Error("Admin API key is required for this action."); window.sessionStorage.setItem("tutorinn-admin-key", key) }
  return { "X-Admin-Key": key }
}
