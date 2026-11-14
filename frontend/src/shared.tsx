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

export { api, getAdminHeaders } from "./services/api"
export { selectedProfile, saveSelectedProfile } from "./services/session"
export { loadAllPosts, createPostNumberMap } from "./services/posts"
export { useSelectedProfile } from "./hooks/useSelectedProfile"
export { SubjectPicker } from "./components/SubjectPicker"
export { AppLayout as Layout } from "./layouts/AppLayout"
