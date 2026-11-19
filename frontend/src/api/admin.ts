import { api, getAdminHeaders } from "./api"
import type { AdminCandidate } from "../types/domain"

export function listPendingAdminMatches(): Promise<AdminCandidate[]> {
  return api<AdminCandidate[]>("/api/admin/matches?review_status=Pending", { headers: getAdminHeaders() })
}

export function decideAdminMatch(id: number, decision: "approve" | "reject"): Promise<void> {
  return api<void>(`/api/responses/${id}/${decision}`, { method: "POST", headers: getAdminHeaders() })
}

export async function listPasswordResetRequests(): Promise<import("../types/auth").PasswordResetRequest[]> {
  return api<import("../types/auth").PasswordResetRequest[]>("/api/auth/admin/password-reset-requests")
}
export async function reviewPasswordResetRequest(id: number, decision: "approve" | "reject"): Promise<import("../types/auth").PasswordResetRequest> {
  return api<import("../types/auth").PasswordResetRequest>(`/api/auth/admin/password-reset-requests/${id}/review`, {
    method: "POST", body: JSON.stringify({ decision }),
  })
}
export async function resendPasswordResetEmail(id: number): Promise<import("../types/auth").PasswordResetRequest> {
  return api<import("../types/auth").PasswordResetRequest>(`/api/auth/admin/password-reset-requests/${id}/resend`, { method: "POST" })
}
