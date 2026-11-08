import HomePage from "./pages/HomePage"
import AboutPage from "./pages/AboutPage"
import TaskDetailsPage from "./pages/TaskDetailsPage"
import LearningPostsPage from "./pages/LearningPostsPage"
import RequestDetailsPage from "./pages/RequestDetailsPage"
import ProfileManager from "./pages/ProfileManager"
import DetailPage from "./pages/DetailPage"

export default function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/"
  if (path === "/") return <HomePage />
  if (path === "/about") return <AboutPage />
  if (path === "/task-details") return window.location.search ? <RequestDetailsPage /> : <TaskDetailsPage />
  if (path === "/posts") return <LearningPostsPage />
  if (path === "/tutors") return <ProfileManager kind="tutor" />
  if (path === "/students") return <ProfileManager kind="student" />
  const tutorMatch = path.match(/^\/tutors\/(\d+)$/)
  if (tutorMatch) return <DetailPage kind="tutor" id={Number(tutorMatch[1])} />
  const studentMatch = path.match(/^\/students\/(\d+)$/)
  if (studentMatch) return <DetailPage kind="student" id={Number(studentMatch[1])} />
  return <div className="page"><section className="empty-state"><h1>Page not found</h1><p>The page you're looking for doesn't exist.</p><a className="button primary" href="/">Back home</a></section></div>
}
