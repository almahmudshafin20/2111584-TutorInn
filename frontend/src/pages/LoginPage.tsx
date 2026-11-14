import { useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError("")
    try {
      await login(email, password)
      window.location.assign("/dashboard")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not sign in.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppLayout>
      <section className="auth-shell" aria-labelledby="login-title">
        <aside className="auth-aside">
          <span className="auth-mark" aria-hidden="true">T.</span>
          <p className="eyebrow">YOUR LEARNING SPACE</p>
          <h2>Make every learning connection count.</h2>
          <p>One trusted place for Students and Tutors to connect, plan and make progress.</p>
          <ul className="auth-benefits">
            <li><span aria-hidden="true">✓</span> Discover learning opportunities that fit your goals</li>
            <li><span aria-hidden="true">✓</span> Keep tutoring requests and responses organized</li>
            <li><span aria-hidden="true">✓</span> Manage your profile and account securely</li>
          </ul>
          <div className="auth-orbit auth-orbit-one" aria-hidden="true" />
          <div className="auth-orbit auth-orbit-two" aria-hidden="true" />
        </aside>
        <div className="auth-content">
          <div className="auth-form-heading">
            <p className="eyebrow">WELCOME BACK</p>
            <h1 id="login-title">Log in</h1>
            <p>Welcome back. Log in to continue to your TutorInn workspace.</p>
          </div>
          <form className="profile-form auth-form" onSubmit={submit}>
            <label className="field">Email address
              <input type="email" autoComplete="email" required value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" />
            </label>
            <label className="field">Password
              <input type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} placeholder="Enter your password" />
            </label>
            {error && <div className="alert error" role="alert">{error}</div>}
            <button className="button primary auth-submit" disabled={busy}>{busy ? "Logging in…" : "Log in"}</button>
          </form>
          <p className="auth-footnote">Don't have an account? <a className="text-link" href="/register">Create an account</a></p>
        </div>
      </section>
    </AppLayout>
  )
}
