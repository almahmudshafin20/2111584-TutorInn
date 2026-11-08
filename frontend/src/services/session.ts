import type { CurrentRole, LearningPost } from "../types"

export function readCurrentRole(): CurrentRole {
  const role = window.localStorage.getItem("tutorinn-role")
  return role === "student" || role === "admin" ? role : "tutor"
}

export function isInterested(post: LearningPost, role: CurrentRole): boolean {
  if (role === "admin") return post.student_confirmed || post.tutor_confirmed
  return role === "student" ? post.student_confirmed : post.tutor_confirmed
}
