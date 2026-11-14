import { useEffect } from "react"
import HomePage from "./pages/HomePage"
import AboutPage from "./pages/AboutPage"
import ProfileManager from "./pages/ProfileManager"
import DetailPage from "./pages/DetailPage"
import TaskDetailsPage from "./pages/TaskDetailsPage"
import AdminReviewPage from "./pages/AdminReviewPage"
import RequestDetailsPage from "./pages/RequestDetailsPage"
import { AppLayout as Layout } from "./layouts/AppLayout"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"
import DashboardPage from "./pages/DashboardPage"
import MyProfilePage from "./pages/MyProfilePage"

function RouteRedirect({ to, title, description }: { to: string; title: string; description: string }) {
  useEffect(() => { window.location.replace(to) }, [to])
  return (
    <Layout>
      <section className="empty-state auth-required">
        <h1>{title}</h1>
        <p>{description}</p>
        <a className="button primary" href={to}>Continue</a>
      </section>
    </Layout>
  )
}

export default function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/"
  if (path === "/") return <HomePage />
  if (path === "/about") return <AboutPage />
  if (path === "/login") return <LoginPage />
  if (path === "/register") return <RegisterPage />
  if (path === "/dashboard") return <DashboardPage />
  if (path === "/profile") return <MyProfilePage />
  if (path === "/posts") return <RouteRedirect to="/dashboard" title="Your workspace has moved" description="Tutoring requests and responses are now managed from your authenticated Student or Tutor dashboard." />
  if (path === "/students" || path.startsWith("/students/")) return <RouteRedirect to="/register?role=student" title="Create your Student account" description="Student profiles are now managed through secure, authenticated accounts rather than the old demo profile directory." />
  if (path === "/task-details") return window.location.search ? <RequestDetailsPage /> : <TaskDetailsPage />
  if (path === "/admin") return <AdminReviewPage />
  if (path === "/tutors") return <ProfileManager kind="tutor" readOnly />
  const tutor = path.match(/^\/tutors\/(\d+)$/)
  if (tutor) return <DetailPage kind="tutor" id={Number(tutor[1])} />
  return <Layout><section className="empty-state"><h1>Page not found</h1><a className="button primary" href="/">Back home</a></section></Layout>
}
