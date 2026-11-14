import { api, getAdminHeaders } from "./api"
import type { AdminCandidate } from "../types/domain"

export function listPendingAdminMatches(): Promise<AdminCandidate[]> {
  return api<AdminCandidate[]>("/api/admin/matches?review_status=Pending", { headers: getAdminHeaders() })
}

export function decideAdminMatch(id: number, decision: "approve" | "reject"): Promise<void> {
  return api<void>(`/api/responses/${id}/${decision}`, { method: "POST", headers: getAdminHeaders() })
}
