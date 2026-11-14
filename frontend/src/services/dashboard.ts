
import { api } from "./api"
import type { StudentDashboard, TutorDashboard, LearningRequest, TutorResponse, TutorProfile } from "../types/auth"
export function loadDashboard(): Promise<StudentDashboard | TutorDashboard> { return api<StudentDashboard | TutorDashboard>("/api/dashboard") }
export function createTutoringRequest(payload: Record<string, unknown>): Promise<LearningRequest> { return api<LearningRequest>("/api/requests", { method: "POST", body: JSON.stringify(payload) }) }
export function updateTutoringRequest(id: number, payload: Record<string, unknown>): Promise<LearningRequest> { return api<LearningRequest>(`/api/requests/${id}`, { method: "PUT", body: JSON.stringify(payload) }) }
export function deleteTutoringRequest(id: number): Promise<void> { return api<void>(`/api/requests/${id}`, { method: "DELETE" }) }
export function respondToRequest(id: number, response: "Interested" | "Not Interested"): Promise<TutorResponse> { return api<TutorResponse>(`/api/requests/${id}/responses`, { method: "POST", body: JSON.stringify({ response }) }) }
export type TutorSearch = { subject?: string; level?: string; min_experience?: string; availability?: string }
export function discoverTutors(filters: TutorSearch): Promise<TutorProfile[]> {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => { if (value?.trim()) params.set(key, value.trim()) })
  return api<TutorProfile[]>(`/api/tutors${params.size ? `?${params.toString()}` : ""}`)
}
