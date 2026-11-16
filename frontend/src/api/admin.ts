import { api } from "./api"

export type AdminUser = {
  id: number; email: string; role: "student" | "tutor" | "admin"; status: string
  created_at: string; updated_at: string
  profile: null | { id: number; full_name: string; education_level?: string; subjects: string[]; teaching_level?: string; experience_years?: number; verification_status?: string }
}
export type AdminTutor = {
  id: number; account_id: number | null; account_status: string; full_name: string; email: string; phone_number: string; subjects: string[]
  teaching_level: string; experience_years: number; hourly_rate: number; bio: string
  verification_status: "pending" | "approved" | "rejected"; reviewed_at: string | null; reviewer_account_id?: number | null; review_note: string
}
export type AdminPage<T> = { items: T[]; total: number; offset: number; limit: number }
export type AdminOverview = {
  students: number; tutors: number; tutoring_requests: number; total_accounts: number
  active_accounts: number; banned_accounts: number; suspended_accounts: number; pending_tutor_reviews: number
}
export type AdminActivity = {
  id: number; event_type: string; account_id: number | null; target: string
  ip_address: string; created_at: string; details: string
}
const query = (values: Record<string, string | number | undefined>) => {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)) })
  return params.toString()
}
export const getAdminOverview = () => api<AdminOverview>("/api/admin/overview")
export const getAdminUsers = (filters: { role?: string; status?: string; q?: string; offset?: number; limit?: number }) =>
  api<AdminPage<AdminUser>>("/api/admin/users?" + query(filters))
export const getAdminUser = (id: number) => api<AdminUser & { recent_activity: AdminActivity[] }>(`/api/admin/users/${id}`)
export const setAdminUserStatus = (id: number, status: string, reason: string) =>
  api<AdminUser>(`/api/admin/users/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, reason }) })
export const bulkSetAdminUserStatus = (account_ids: number[], status: string, reason: string) =>
  api<{ results: { account_id: number; success: boolean; error?: string }[]; succeeded: number; failed: number }>(
    "/api/admin/users/bulk-status", { method: "POST", body: JSON.stringify({ account_ids, status, reason }) })
export const getAdminTutors = (filters: { verification_status?: string; q?: string; offset?: number; limit?: number }) =>
  api<AdminPage<AdminTutor>>("/api/admin/tutors?" + query(filters))
export const reviewAdminTutor = (id: number, status: string, note: string) =>
  api<{ tutor_id: number; status: string; reviewed_at: string; note: string }>(
    `/api/admin/tutors/${id}/verification`, { method: "PATCH", body: JSON.stringify({ status, note }) })
export const getAdminRequests = (filters: { status?: string; q?: string; offset?: number; limit?: number }) =>
  api<AdminPage<{ id: number; type: string; author: string; subjects: string[]; level: string; status: string }>>(
    "/api/admin/requests?" + query(filters))
export const getAdminActivity = (filters: { event_type?: string; q?: string; offset?: number; limit?: number }) =>
  api<AdminPage<AdminActivity>>("/api/admin/activity?" + query(filters))
export const getAdminSecurity = (hours = 24, minEvents = 3) => api<{ hours: number; min_events: number; incident_count: number; by_ip: { ip_address: string; count: number }[]; by_account: { account_id: number; count: number }[]; events: AdminActivity[] }>(`/api/admin/security?hours=${hours}&min_events=${minEvents}`)
export const exportAdminCsv = (kind: "users" | "tasks" | "activity") => api<string>(`/api/admin/export/${kind}`)

export type AdminTask = { id: number; owner_account_id: number; title: string; category: string | null; due_date: string | null; completed: boolean; created_at: string }
export type AdminGroup = { id: number; name: string; owner_account_id: number; member_count: number; task_count: number }
export const getAdminTasks = (offset = 0, limit = 25) => api<AdminPage<AdminTask>>(`/api/admin/tasks?offset=${offset}&limit=${limit}`)
export const getAdminGroups = () => api<AdminGroup[]>("/api/admin/groups")
export const bulkDeleteAdminTasks = (task_ids: number[], reason: string) =>
  api<{ results: { task_id: number; success: boolean; error?: string }[]; succeeded: number; failed: number }>(
    "/api/admin/tasks/bulk", { method: "DELETE", body: JSON.stringify({ task_ids, reason, confirm: true }) })
export const deleteAdminGroup = (id: number, reason: string) =>
  api<{ deleted: boolean; members_removed: number; tasks_removed: number; assignments_removed: number }>(
    `/api/admin/groups/${id}`, { method: "DELETE", body: JSON.stringify({ confirm: true, reason }) })

export const purgeAdminActivity = (before: string, reason: string) =>
  api<{ removed: number; preserved: string }>("/api/admin/activity/purge", {
    method: "DELETE", body: JSON.stringify({ before, reason, confirm: true }),
  })
