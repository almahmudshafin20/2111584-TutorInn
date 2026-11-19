import { useEffect } from "react"
import HomePage from "./pages/HomePage"
import AboutPage from "./pages/AboutPage"
import ProfileManager from "./pages/ProfileManager"
import DetailPage from "./pages/DetailPage"
import AdminReviewPage from "./pages/AdminReviewPage"
import RequestDetailsPage from "./pages/RequestDetailsPage"
import { AppLayout as Layout } from "./layouts/AppLayout"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"
import DashboardPage from "./pages/DashboardPage"
import MyProfilePage from "./pages/MyProfilePage"
import ForgotPasswordPage from "./pages/ForgotPasswordPage"
import ResetPasswordPage from "./pages/ResetPasswordPage"
import PasswordResetRequestsPage from "./pages/PasswordResetRequestsPage"
import { useAuth } from "./context/AuthContext"
import type { AccountRole } from "./types/auth"

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


function RequireAccount({ children, roles }: { children: React.ReactNode; roles?: AccountRole[] }) {
  const { account, loading } = useAuth()
  if (loading) return <Layout><p className="muted" role="status">Checking your session…</p></Layout>
  if (!account) return <RouteRedirect to="/login" title="Sign in required" description="Please sign in to continue." />
  if (roles && !roles.includes(account.role)) return <Layout><section className="empty-state auth-required"><h1>Access restricted</h1><p>Your account role does not have permission to open this page.</p><a className="button primary" href="/dashboard">Go to your workspace</a></section></Layout>
  return <>{children}</>
}

export default function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/"
  if (path === "/") return <HomePage />
  if (path === "/about") return <AboutPage />
  if (path === "/login") return <LoginPage />
  if (path === "/register") return <RegisterPage />
  if (path === "/forgot-password") return <ForgotPasswordPage />
  if (path === "/reset-password") return <ResetPasswordPage />
  if (path === "/dashboard") return <RequireAccount><DashboardPage /></RequireAccount>
  if (path === "/profile") return <RequireAccount roles={["student", "tutor"]}><MyProfilePage /></RequireAccount>
  if (path === "/posts") return <RouteRedirect to="/dashboard" title="Your workspace has moved" description="Tutoring requests and responses are now managed from your authenticated Student or Tutor dashboard." />
  if (path === "/students" || path.startsWith("/students/")) return <RouteRedirect to="/register?role=student" title="Create your Student account" description="Student profiles are now managed through secure, authenticated accounts rather than the old demo profile directory." />
  if (path === "/task-details") return window.location.search ? <RequireAccount roles={["student", "tutor"]}><RequestDetailsPage /></RequireAccount> : <RouteRedirect to="/dashboard" title="Your responses are in your dashboard" description="Response history is now part of your authenticated Student or Tutor workspace." />
  if (path === "/admin") return <RequireAccount roles={["admin"]}><AdminReviewPage /></RequireAccount>
  if (path === "/admin/password-resets") return <RequireAccount roles={["admin", "moderator"]}><PasswordResetRequestsPage /></RequireAccount>
  if (path === "/tutors") return <ProfileManager kind="tutor" readOnly />
  const tutor = path.match(/^\/tutors\/(\d+)$/)
  if (tutor) return <DetailPage kind="tutor" id={Number(tutor[1])} />
  return <Layout><section className="empty-state"><h1>Page not found</h1><a className="button primary" href="/">Back home</a></section></Layout>
}
