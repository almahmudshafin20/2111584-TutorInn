import { api } from "./api"

export type ReportTarget = "profile" | "tutoring_post" | "tutoring_request"
export type ContentReport = {
  id: number; reporter_account_id: number; reporter_email: string
  target_type: ReportTarget; target_id: number; target_label: string
  reason: string; description: string; status: "pending" | "in_review" | "resolved" | "dismissed"
  review_note: string; reviewed_by_account_id: number | null; reviewed_at: string | null; created_at: string
}
export type ManagedSubject = { id: number; name: string; active: boolean; created_at: string }
type Page<T> = { items: T[]; total: number; offset: number; limit: number }

export const submitContentReport = (target_type: ReportTarget, target_id: number, reason: string, description: string, target_role?: "student" | "tutor") =>
  api<{ id: number; status: string; created_at: string }>("/api/reports", {
    method: "POST", body: JSON.stringify({ target_type, target_id, reason, description, target_role }),
  })
export const getContentReports = (filters: { status?: string; q?: string; offset?: number; limit?: number }) => {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => { if (value !== undefined && value !== "") query.set(key, String(value)) })
  return api<Page<ContentReport>>("/api/admin/reports?" + query.toString())
}
export const reviewContentReport = (id: number, status: string, review_note: string) =>
  api<ContentReport>(`/api/admin/reports/${id}`, { method: "PATCH", body: JSON.stringify({ status, review_note }) })
export const getManagedSubjects = () => api<ManagedSubject[]>("/api/admin/subjects")
export const createManagedSubject = (name: string) =>
  api<ManagedSubject>("/api/admin/subjects", { method: "POST", body: JSON.stringify({ name }) })
export const updateManagedSubject = (id: number, payload: { name?: string; active?: boolean }) =>
  api<ManagedSubject>(`/api/admin/subjects/${id}`, { method: "PATCH", body: JSON.stringify(payload) })
export const deleteManagedSubject = (id: number) =>
  api<{ deleted: boolean; subject_id: number }>(`/api/admin/subjects/${id}`, { method: "DELETE" })
