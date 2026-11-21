import { api, setAccessToken } from "./api"
import type { AuthResponse, OwnProfile, ActiveSession } from "../types/auth"
function csrfCookie(): string {
  const item = document.cookie.split("; ").find(value => value.startsWith("tutorinn_csrf="))
  return item ? decodeURIComponent(item.slice("tutorinn_csrf=".length)) : ""
}
export async function signIn(email: string, password: string): Promise<AuthResponse> {
  const result = await api<AuthResponse>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }); setAccessToken(result.access_token); return result
}
export async function signUp(role: "student" | "tutor", payload: Record<string, unknown>): Promise<AuthResponse> {
  const result = await api<AuthResponse>(`/api/auth/register/${role}`, { method: "POST", body: JSON.stringify(payload) }); setAccessToken(result.access_token); return result
}
let restoreSessionPromise: Promise<AuthResponse> | null = null
export function restoreSession(): Promise<AuthResponse> {
  if (!restoreSessionPromise) {
    restoreSessionPromise = (async () => {
      const csrf = csrfCookie()
      if (!csrf) throw new Error("No saved session.")
      const result = await api<AuthResponse>("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRF-Token": csrf },
      })
      setAccessToken(result.access_token)
      return result
    })().finally(() => { restoreSessionPromise = null })
  }
  return restoreSessionPromise
}
export async function signOut(): Promise<void> {
  const csrf = csrfCookie()
  try { await api("/api/auth/logout", { method: "POST", credentials: "include", headers: csrf ? { "X-CSRF-Token": csrf } : {} }) }
  finally { setAccessToken(null) }
}
export function getOwnProfile(): Promise<OwnProfile> { return api<OwnProfile>("/api/me/profile") }
export function updateOwnProfile(role: "student" | "tutor", payload: Record<string, unknown>): Promise<OwnProfile> {
  return api<OwnProfile>(`/api/me/profile/${role}`, { method: "PUT", body: JSON.stringify(payload) })
}
export function changePassword(current_password: string, new_password: string): Promise<{ message: string }> {
  return api("/api/me/password", { method: "POST", body: JSON.stringify({ current_password, new_password }) })
}
export function listAccountSessions(accountId: number): Promise<ActiveSession[]> { return api<ActiveSession[]>(`/api/auth/admin/accounts/${accountId}/sessions`) }
export function listSessions(): Promise<ActiveSession[]> { return api<ActiveSession[]>("/api/auth/sessions") }
export function revokeSession(id: number): Promise<void> { return api<void>(`/api/auth/sessions/${id}`, { method: "DELETE" }) }

export function revokeOtherSessions(): Promise<void> { return api<void>("/api/auth/sessions/others", { method: "DELETE" }) }
export function revokeAllSessions(): Promise<void> { return api<void>("/api/auth/sessions/all", { method: "DELETE" }) }

export function requestPasswordReset(email: string): Promise<{ message: string }> {
  return api("/api/auth/password-reset-requests", { method: "POST", body: JSON.stringify({ email }) })
}
export function completePasswordReset(token: string, new_password: string, confirm_password: string): Promise<{ message: string }> {
  return api("/api/auth/password-reset", { method: "POST", body: JSON.stringify({ token, new_password, confirm_password }) })
}

export function requestEmailVerification(email: string): Promise<{ message: string }> {
  return api<{ message: string }>("/api/auth/email-verification-requests", {
    method: "POST",
    body: JSON.stringify({ email }),
  })
}
export function verifyEmail(token: string): Promise<{ message: string }> {
  return api<{ message: string }>("/api/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  })
}
