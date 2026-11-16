import { api } from "./api"
import type { InterestResponse, LearningPost } from "../types/domain"

// Display numbers are derived from the current newest-first post list.
// Database IDs remain stable and are always used for API requests and relationships.
export async function loadAllPosts(): Promise<LearningPost[]> {
  const pageSize = 20
  const all: LearningPost[] = []
  for (let offset = 0; offset <= 180; offset += pageSize) {
    const page = await api<LearningPost[]>(`/api/posts?offset=${offset}&limit=${pageSize}`)
    all.push(...page)
    if (page.length < pageSize) break
  }
  return all
}

export function listPosts(filter: "all" | "tutor" | "student" = "all"): Promise<LearningPost[]> {
  return api<LearningPost[]>(`/api/posts?offset=0&limit=20${filter === "all" ? "" : `&post_type=${filter}`}`)
}

export function getPost(id: number): Promise<LearningPost> {
  return api<LearningPost>(`/api/posts/${id}`)
}

export function createPost(payload: Record<string, unknown>): Promise<LearningPost> {
  return api<LearningPost>("/api/posts", { method: "POST", body: JSON.stringify(payload) })
}

export function updatePost(id: number, payload: Record<string, unknown>): Promise<LearningPost> {
  return api<LearningPost>(`/api/posts/${id}`, { method: "PUT", body: JSON.stringify(payload) })
}

export function deletePost(id: number): Promise<void> {
  return api<void>(`/api/posts/${id}`, { method: "DELETE" })
}

export function listMyResponses(): Promise<InterestResponse[]> {
  return api<InterestResponse[]>("/api/responses")
}

export function savePostResponse(id: number, response: "Interested" | "Not Interested"): Promise<InterestResponse> {
  return api<InterestResponse>(`/api/posts/${id}/response`, {
    method: "POST",
    body: JSON.stringify({ response }),
  })
}

export function createPostNumberMap(posts: LearningPost[]): Record<number, number> {
  return Object.fromEntries(posts.map((post, index) => [post.id, index + 1]))
}
