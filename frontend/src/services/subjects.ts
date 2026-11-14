import { api } from "./api"

export function listSubjects(): Promise<string[]> {
  return api<string[]>("/api/subjects")
}
