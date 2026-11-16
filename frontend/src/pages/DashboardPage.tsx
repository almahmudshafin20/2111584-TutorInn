
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import StudentDashboardPage from "./StudentDashboardPage"
import TutorDashboardPage from "./TutorDashboardPage"
export default function DashboardPage() {
  const { account, loading } = useAuth()
  if (loading) return <AppLayout><p className="muted">Checking your session…</p></AppLayout>
  if (!account) return <AppLayout><section className="empty-state auth-required"><h1>Sign in required</h1><p>Please sign in to access your dashboard.</p><a className="button primary" href="/login">Sign in</a></section></AppLayout>
  if (account.role === "student") return <StudentDashboardPage />
  if (account.role === "tutor") return <TutorDashboardPage />
  return <AppLayout><section className="empty-state auth-required"><h1>Admin workspace</h1><p>Admin management is part of a later Beta milestone. Your Admin account is authenticated.</p></section></AppLayout>
}
