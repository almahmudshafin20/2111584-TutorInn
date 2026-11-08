import type { LearningPost, Profile } from "../types"

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


// Resource-specific API functions keep endpoint URLs, HTTP methods, and request
// serialization out of page components.
export type ProfileKind = "student" | "tutor"
export type ProfilePayload = Record<string, string | number>
export type PostPayload = Record<string, string | number>

export function listPosts(offset = 0, limit = 20, postType?: "tutor" | "student") {
  const typeQuery = postType ? `&post_type=${encodeURIComponent(postType)}` : ""
  return api<LearningPost[]>(`/api/posts?offset=${offset}&limit=${limit}${typeQuery}`)
}

export function getPost(id: number) {
  return api<LearningPost>(`/api/posts/${id}`)
}

export function createPost(payload: PostPayload) {
  return api<LearningPost>("/api/posts", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function updatePost(id: number, payload: PostPayload) {
  return api<LearningPost>(`/api/posts/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  })
}

export function deletePost(id: number) {
  return api<void>(`/api/posts/${id}`, { method: "DELETE" })
}

export function respondToPost(id: number, action: "confirm" | "not-interested", actor: "student" | "tutor") {
  return api<LearningPost>(`/api/posts/${id}/${action}`, {
    method: "POST",
    body: JSON.stringify({ actor }),
  })
}

export function approvePost(id: number) {
  return api<LearningPost>(`/api/posts/${id}/approve`, {
    method: "POST",
    headers: getAdminHeaders(),
  })
}

export function rejectPost(id: number) {
  return api<LearningPost>(`/api/posts/${id}/reject`, {
    method: "POST",
    headers: getAdminHeaders(),
  })
}

export function listProfiles(kind: ProfileKind, term = "") {
  const query = term.trim() ? `?q=${encodeURIComponent(term.trim())}` : ""
  return api<Profile[]>(`/api/${kind}s${query}`)
}

export function getProfile(kind: ProfileKind, id: number) {
  return api<Profile>(`/api/${kind}s/${id}`)
}

export function createProfile(kind: ProfileKind, payload: ProfilePayload) {
  return api<Profile>(`/api/${kind}s`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function updateProfile(kind: ProfileKind, id: number, payload: ProfilePayload) {
  return api<Profile>(`/api/${kind}s/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  })
}

export function deleteProfile(kind: ProfileKind, id: number) {
  return api<void>(`/api/${kind}s/${id}`, { method: "DELETE" })
}
