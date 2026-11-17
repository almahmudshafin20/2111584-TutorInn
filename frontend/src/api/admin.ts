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
  trends: Record<"students" | "tutors" | "tutoring_requests", { last_7_days: number; previous_7_days: number; change: number }>
}
export type AdminActivity = {
  id: number; event_type: string; account_id: number | null; target: string
  ip_address: string; user_agent?: string; created_at: string; details: string
}
const query = (values: Record<string, string | number | undefined>) => {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)) })
  return params.toString()
}
export const getAdminOverview = () => api<AdminOverview>("/api/admin/overview")
export const getAdminUsers = (filters: { role?: string; status?: string; q?: string; created_from?: string; created_to?: string; offset?: number; limit?: number }) =>
  api<AdminPage<AdminUser>>("/api/admin/users?" + query(filters))
export type AdminSession = { id: number; created_at: string; last_used_at: string; expires_at: string; user_agent: string; ip_address: string }
export const getAdminUser = (id: number) => api<AdminUser & { recent_activity: AdminActivity[]; active_sessions: AdminSession[] }>(`/api/admin/users/${id}`)
export const grantAdminRole = (id: number, reason: string) => api<AdminUser>(`/api/admin/users/${id}/admin-role`, { method: "POST", body: JSON.stringify({ reason }) })
export const revokeAdminRole = (id: number, reason: string) => api<AdminUser>(`/api/admin/users/${id}/admin-role`, { method: "DELETE", body: JSON.stringify({ reason }) })
export const revokeAdminAccountSession = (accountId: number, sessionId: number) =>
  api<{ revoked: boolean; session_id: number }>(`/api/admin/users/${accountId}/sessions/${sessionId}`, { method: "DELETE" })
export const setAdminUserStatus = (id: number, status: string, reason: string) =>
  api<AdminUser>(`/api/admin/users/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, reason }) })
export const bulkSetAdminUserStatus = (account_ids: number[], status: string, reason: string) =>
  api<{ results: { account_id: number; success: boolean; error?: string }[]; succeeded: number; failed: number }>(
    "/api/admin/users/bulk-status", { method: "POST", body: JSON.stringify({ account_ids, status, reason }) })
export const getAdminTutors = (filters: { verification_status?: string; account_status?: string; q?: string; created_from?: string; created_to?: string; offset?: number; limit?: number }) =>
  api<AdminPage<AdminTutor>>("/api/admin/tutors?" + query(filters))
export const reviewAdminTutor = (id: number, status: string, note: string) =>
  api<{ tutor_id: number; status: string; reviewed_at: string; note: string }>(
    `/api/admin/tutors/${id}/verification`, { method: "PATCH", body: JSON.stringify({ status, note }) })
export const getAdminRequests = (filters: { status?: string; q?: string; owner_account_id?: number; created_from?: string; created_to?: string; offset?: number; limit?: number }) =>
  api<AdminPage<{ id: number; type: string; author: string; subjects: string[]; level: string; status: string }>>(
    "/api/admin/requests?" + query(filters))
export const getAdminActivity = (filters: { event_type?: string; q?: string; account_id?: number; created_from?: string; created_to?: string; offset?: number; limit?: number }) =>
  api<AdminPage<AdminActivity>>("/api/admin/activity?" + query(filters))
export const getAdminSecurity = (hours = 24, minEvents = 3, filters: { event_type?: string; q?: string; account_id?: number; offset?: number; limit?: number } = {}) => api<{ hours: number; min_events: number; incident_count: number; total: number; offset: number; limit: number; by_ip: { ip_address: string; count: number; last_seen: string; distinct_accounts: number; event_types: string[] }[]; registrations_by_ip: { ip_address: string; registrations: number; last_seen: string; distinct_accounts: number }[]; by_account: { account_id: number; email: string; status: string; count: number; last_seen: string; distinct_source_ips: number; event_types: string[] }[]; by_attempted_email: { email: string; count: number; last_seen: string }[]; events: AdminActivity[]; hostile_events: AdminActivity[] }>(`/api/admin/security?hours=${hours}&min_events=${minEvents}&` + query(filters))
export const exportAdminCsv = (kind: "users" | "tasks" | "activity", filters: { q?: string; role?: string; status?: string; account_id?: number; scope?: string; owner_account_id?: number; created_from?: string; created_to?: string; limit?: number } = {}) =>
  api<string>(`/api/admin/export/${kind}?` + query(filters))

export type AdminTask = { id: number; owner_account_id: number; title: string; category: string | null; due_date: string | null; completed: boolean; created_at: string }
export type AdminGroup = { id: number; name: string; owner_account_id: number; owner_email: string; member_count: number; task_count: number; assignment_count: number; created_at: string; status: string }
export type AdminGroupTask = { id: number; title: string; group_id: number; group_name: string; created_by_email: string; assigned_students: { account_id: number; email: string; completed: boolean }[]; assignment_count: number; completed_count: number; status: string; due_date: string | null; created_at: string }
export const getAdminTasks = (filters: { q?: string; status?: string; owner_account_id?: number; created_from?: string; created_to?: string; offset?: number; limit?: number } = {}) =>
  api<AdminPage<AdminTask>>("/api/admin/tasks?" + query(filters))
export const getAdminGroups = (filters: { q?: string; owner_account_id?: number; created_from?: string; created_to?: string; offset?: number; limit?: number } = {}) =>
  api<AdminPage<AdminGroup>>("/api/admin/groups?" + query(filters))
export const getAdminGroupTasks = (filters: { q?: string; owner_account_id?: number; created_from?: string; created_to?: string; offset?: number; limit?: number } = {}) =>
  api<AdminPage<AdminGroupTask>>("/api/admin/group-tasks?" + query(filters))
export const bulkDeleteAdminGroupTasks = (task_ids: number[], reason: string) =>
  api<{ results: { task_id: number; success: boolean; error?: string; assignments_removed?: number }[]; succeeded: number; failed: number }>(
    "/api/admin/group-tasks/bulk", { method: "DELETE", body: JSON.stringify({ task_ids, reason, confirm: true }) })
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

export type AdminDeletionRequest = { id: number; account_email: string; account_role: "student" | "tutor"; reason: string; status: "pending" | "approved" | "rejected"; requested_at: string; reviewed_at: string | null; reviewed_by_account_id: number | null }
export const getAdminDeletionRequests = (status = "pending") => api<AdminPage<AdminDeletionRequest>>("/api/admin/account-deletion-requests?" + query({ status, limit: 100 }))
export const reviewAdminDeletionRequest = (id: number, status: "approved" | "rejected", review_note: string) =>
  api<{ id: number; status: string; deleted?: boolean; account_status?: string }>("/api/admin/account-deletion-requests/" + id, { method: "PATCH", body: JSON.stringify({ status, review_note }) })
