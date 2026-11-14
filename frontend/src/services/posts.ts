import { api } from "./api"
import type { LearningPost } from "../types/domain"

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

export function createPostNumberMap(posts: LearningPost[]): Record<number, number> {
  return Object.fromEntries(posts.map((post, index) => [post.id, index + 1]))
}
