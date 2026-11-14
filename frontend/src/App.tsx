import HomePage from "./pages/HomePage"
import AboutPage from "./pages/AboutPage"
import ProfileManager from "./pages/ProfileManager"
import DetailPage from "./pages/DetailPage"
import LearningPostsPage from "./pages/LearningPostsPage"
import TaskDetailsPage from "./pages/TaskDetailsPage"
import AdminReviewPage from "./pages/AdminReviewPage"
import RequestDetailsPage from "./pages/RequestDetailsPage"
import { AppLayout as Layout } from "./layouts/AppLayout"

export default function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/"
  if (path === "/") return <HomePage />
  if (path === "/about") return <AboutPage />
  if (path === "/posts") return <LearningPostsPage />
  if (path === "/task-details") return window.location.search ? <RequestDetailsPage /> : <TaskDetailsPage />
  if (path === "/admin") return <AdminReviewPage />
  if (path === "/tutors") return <ProfileManager kind="tutor" />
  if (path === "/students") return <ProfileManager kind="student" />
  const tutor = path.match(/^\/tutors\/(\d+)$/); if (tutor) return <DetailPage kind="tutor" id={Number(tutor[1])} />
  const student = path.match(/^\/students\/(\d+)$/); if (student) return <DetailPage kind="student" id={Number(student[1])} />
  return <Layout><section className="empty-state"><h1>Page not found</h1><a className="button primary" href="/">Back home</a></section></Layout>
}
