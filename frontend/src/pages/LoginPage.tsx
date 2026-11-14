import { useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState(""), [password, setPassword] = useState(""), [error, setError] = useState(""), [busy, setBusy] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); setError(""); try { await login(email, password); window.location.assign("/dashboard") } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not sign in.") } finally { setBusy(false) } }
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">WELCOME BACK</p><h1>Sign in to TutorInn</h1><p>Access your tutoring dashboard and manage your account securely.</p></section><section className="panel auth-panel"><form className="profile-form" onSubmit={submit}><label className="field">Email address<input type="email" autoComplete="email" required value={email} onChange={event => setEmail(event.target.value)} /></label><label className="field">Password<input type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} /></label>{error && <div className="alert error" role="alert">{error}</div>}<button className="button primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button></form><p className="auth-footnote">New to TutorInn? <a className="text-link" href="/register">Create an account</a></p></section></AppLayout>
}
