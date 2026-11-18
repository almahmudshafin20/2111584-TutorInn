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

export type DeletionContentItem = { content_type: "learning_post" | "personal_task" | "learning_group" | "group_task" | "group_assignment"; content_id: number; label: string; description: string }
export type OwnDeletionRequest = {
  id: number; status: "pending"; reason: string; requested_at: string
  requested_option: "anonymize" | "complete"; final_option: "anonymize" | "complete" | null
  requested_content_action?: "account_only" | "delete_selected" | "delete_all" | "retain_all"
  requested_visibility?: "visible" | "hidden"; requested_anonymize_content?: boolean
} | null
export function getMyDeletionRequest(): Promise<OwnDeletionRequest> { return api<OwnDeletionRequest>("/api/me/deletion-request") }
export function getMyDeletionContent(): Promise<{ items: DeletionContentItem[] }> { return api("/api/me/deletion-content") }
export type AccountDeletionPreferences = {
  content_action: "account_only" | "delete_selected" | "delete_all"
  selected_content: { content_type: DeletionContentItem["content_type"]; content_id: number }[]
  visibility: "visible" | "hidden"
  anonymize_content: boolean
}
export function requestMyAccountDeletion(
  current_password: string, reason: string,
  preferences: AccountDeletionPreferences | "anonymize" | "complete",
): Promise<{ id: number; status: string; message: string }> {
  const choices = typeof preferences === "string"
    ? { deletion_option: preferences }
    : preferences
  return api("/api/me/deletion-request", {
    method: "POST", body: JSON.stringify({ current_password, reason, ...choices }),
  })
}


export type PasswordResetRequestRow = {
  id: number; account_id: number; account_email: string; account_role: "student" | "tutor";
  status: "pending" | "approved" | "rejected" | "completed"; requested_at: string; requested_ip: string;
  reviewed_at: string | null; reviewer_email: string | null; review_note: string;
}
export const requestPasswordReset = (email: string) => api<{ message: string }>("/api/auth/password-reset/request", { method: "POST", body: JSON.stringify({ email }) })
export const completePasswordReset = (token: string, new_password: string, confirm_password: string) => api<{ message: string }>("/api/auth/password-reset/complete", { method: "POST", body: JSON.stringify({ token, new_password, confirm_password }) })
export const requestEmailVerification = (email: string) => api<{ message: string }>("/api/auth/email-verification/request", { method: "POST", body: JSON.stringify({ email }) })
export const completeEmailVerification = (token: string) => api<{ message: string }>("/api/auth/email-verification/complete", { method: "POST", body: JSON.stringify({ token }) })
export const listPasswordResetRequests = (status = "pending") => api<{ items: PasswordResetRequestRow[]; total: number; offset: number; limit: number }>("/api/admin/password-reset-requests?status=" + encodeURIComponent(status))
export const reviewPasswordResetRequest = (id: number, status: "approved" | "rejected", review_note = "") => api<{ id: number; status: string; delivery_status: string }>(`/api/admin/password-reset-requests/${id}`, { method: "PATCH", body: JSON.stringify({ status, review_note }) })
