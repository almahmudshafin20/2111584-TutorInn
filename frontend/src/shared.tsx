// Backward-compatible exports for existing page modules.
// New code should import from the focused types, services, hooks, components, and layouts.
export {
  emptyPost,
  emptyStudent,
  emptyTutor,
} from "./types/domain"
export type {
  InterestResponse,
  LearningPost,
  Profile,
  ProfileType,
  SelectedProfile,
  Student,
  Tutor,
} from "./types/domain"

export { api } from "./api/api"
export { selectedProfile, saveSelectedProfile } from "./api/session"
export { loadAllPosts, createPostNumberMap } from "./api/posts"
export { useSelectedProfile } from "./hooks/useSelectedProfile"
export { SubjectPicker } from "./components/SubjectPicker"
export { AppLayout as Layout } from "./layouts/AppLayout"
