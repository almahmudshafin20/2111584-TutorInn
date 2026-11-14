import { api } from "./api"
import type { Profile, ProfileType, Student, Tutor } from "../types/domain"

export function listProfiles(kind: ProfileType, query = ""): Promise<Profile[]> {
  const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ""
  return api<Profile[]>(`/api/${kind}s${suffix}`)
}

export function getProfile(kind: ProfileType, id: number): Promise<Profile> {
  return api<Profile>(`/api/${kind}s/${id}`)
}

export function createProfile(kind: ProfileType, payload: Record<string, unknown>): Promise<Profile> {
  return api<Profile>(`/api/${kind}s`, { method: "POST", body: JSON.stringify(payload) })
}

export function updateProfile(kind: ProfileType, id: number, payload: Record<string, unknown>): Promise<Profile> {
  return api<Profile>(`/api/${kind}s/${id}`, { method: "PUT", body: JSON.stringify(payload) })
}

export function deleteProfile(kind: ProfileType, id: number): Promise<void> {
  return api<void>(`/api/${kind}s/${id}`, { method: "DELETE" })
}

export async function listAllProfiles(): Promise<Profile[]> {
  const [students, tutors] = await Promise.all([
    api<Student[]>("/api/students"),
    api<Tutor[]>("/api/tutors"),
  ])
  return [...students, ...tutors]
}

export function getApprovedMatches<T>(): Promise<T[]> {
  return api<T[]>("/api/profiles/approved-matches")
}
