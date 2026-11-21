let accessToken: string | null = null
let refreshPromise: Promise<unknown | null> | null = null

export function setAccessToken(token: string | null): void { accessToken = token }

function csrfCookie(): string {
  const item = document.cookie.split("; ").find(value => value.startsWith("tutorinn_csrf="))
  return item ? decodeURIComponent(item.slice("tutorinn_csrf=".length)) : ""
}

// One refresh at a time. The refresh token rotates on every call, so two parallel
// refreshes would make the second look like a reused token. Callers share this promise.
export function refreshSessionOnce<T extends { access_token?: string }>(): Promise<T | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const csrf = csrfCookie()
      if (!csrf) return null
      try {
        const response = await fetch("/api/auth/refresh", {
          method: "POST",
          credentials: "include",
          headers: { "X-CSRF-Token": csrf },
        })
        if (!response.ok) return null
        const result = await response.json() as T
        if (!result.access_token) return null
        setAccessToken(result.access_token)
        return result
      } catch {
        return null
      }
    })().finally(() => { refreshPromise = null })
  }
  return refreshPromise as Promise<T | null>
}

async function refreshAccessToken(): Promise<boolean> {
  return (await refreshSessionOnce()) !== null
}

async function readError(response: Response): Promise<string> {
  let message = `Request failed (${response.status})`
  try {
    const body = await response.json()
    if (typeof body.detail === "string") message = body.detail
    else if (Array.isArray(body.detail)) message = body.detail.map((item: { loc?: unknown[]; msg?: string }) => (Array.isArray(item.loc) ? item.loc.filter(part => part !== "body").join(".") + ": " : "") + (item.msg ?? "Invalid value")).join("; ")
    else if (typeof body.message === "string") message = body.message
  } catch { /* retain HTTP status */ }
  return message
}

export async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const authenticatedRoute = url.startsWith("/api/auth/") || url.startsWith("/api/me/") || url.startsWith("/api/dashboard") || url.startsWith("/api/requests") || url.startsWith("/api/admin/") || url.startsWith("/api/reports")
  const profileId = authenticatedRoute ? null : window.localStorage.getItem("tutorinn-profile-id")
  const profileType = authenticatedRoute ? null : window.localStorage.getItem("tutorinn-profile-type")
  const headers = new Headers(init?.headers)
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  if (profileId && profileType) { headers.set("X-TutorInn-Profile-ID", profileId); headers.set("X-TutorInn-Profile-Type", profileType) }

  const send = () => {
    const requestHeaders = new Headers(headers)
    if (accessToken && !requestHeaders.has("Authorization")) requestHeaders.set("Authorization", `Bearer ${accessToken}`)
    return fetch(url, { ...init, credentials: init?.credentials ?? "same-origin", headers: requestHeaders })
  }

  let response = await send()
  const authEntry = /^\/api\/auth\/(login|register\/student|register\/tutor|refresh|logout)$/.test(url)
  if (response.status === 401 && (accessToken || csrfCookie()) && !authEntry) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      response = await send()
      if (response.status === 401) {
        setAccessToken(null)
        window.dispatchEvent(new Event("tutorinn-auth-invalid"))
      }
    } else {
      setAccessToken(null)
      window.dispatchEvent(new Event("tutorinn-auth-invalid"))
    }
  }

  if (!response.ok) throw new Error(await readError(response))
  if (response.status === 204) return undefined as T
  if (response.headers.get("content-type")?.includes("text/csv")) return await response.text() as T
  return response.json() as Promise<T>
}
