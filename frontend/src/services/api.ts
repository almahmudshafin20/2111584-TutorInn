export async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const profileId = window.localStorage.getItem("tutorinn-profile-id")
  const profileType = window.localStorage.getItem("tutorinn-profile-type")
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(profileId && profileType ? { "X-TutorInn-Profile-ID": profileId, "X-TutorInn-Profile-Type": profileType } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let message = "Request failed (" + response.status + ")"
    try {
      const body = await response.json()
      if (typeof body.detail === "string") message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((item: { loc?: unknown[]; msg?: string }) => (Array.isArray(item.loc) ? item.loc.filter(part => part !== "body").join(".") + ": " : "") + (item.msg ?? "Invalid value")).join("; ")
      else if (typeof body.message === "string") message = body.message
    } catch { /* retain HTTP status */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function getAdminHeaders(): HeadersInit {
  let key = window.sessionStorage.getItem("tutorinn-admin-key")
  if (!key) {
    key = window.prompt("Enter the configured TutorInn Admin API key")
    if (!key) throw new Error("Admin API key is required for this action.")
    window.sessionSto¶»§q«^