export async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      "X-TutorInn-Role": window.localStorage.getItem("tutorinn-role") ?? "tutor",
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === "string") {
        message = body.detail
      } else if (Array.isArray(body.detail)) {
        const details = body.detail.map((item: { loc?: unknown[]; msg?: string }) => {
          const field = Array.isArray(item.loc) ? item.loc.filter(part => part !== "body").join(".") : ""
          return field ? `${field}: ${item.msg ?? "Invalid value"}` : (item.msg ?? "Invalid value")
        })
        if (details.length) message = details.join("; ")
      } else if (typeof body.message === "string") {
        message = body.message
      }
    } catch {
      // Keep the status message when the response is not JSON.
    }
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
    window.sessionStorage.setItem("tutorinn-admin-key", key)
  }
  return { "X-Admin-Key": key }
}
