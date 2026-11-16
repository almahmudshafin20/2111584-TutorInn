import { useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import { PasswordField } from "../components/PasswordField"

const REMEMBERED_EMAIL_KEY = "tutorinn-remembered-email"
function readRememberedEmail() {
  try { return window.localStorage.getItem(REMEMBERED_EMAIL_KEY) ?? "" } catch { return "" }
}
function saveRememberedEmail(email: string, remember: boolean) {
  try {
    if (remember) window.localStorage.setItem(REMEMBERED_EMAIL_KEY, email.trim())
    else window.localStorage.removeItem(REMEMBERED_EMAIL_KEY)
  } catch { /* Remember-email is optional when browser storage is unavailable. */ }
}

export default function LoginPage() {
  const { login } = useAuth()
  const initialRememberedEmail = readRememberedEmail()
  const [email, setEmail] = useState(initialRememberedEmail)
  const [rememberEmail, setRememberEmail] = useState(Boolean(initialRememberedEmail))
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError("")
    try {
      await login(email, password)
      saveRememberedEmail(email, rememberEmail)
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
            <p>Use the email and password for your TutorInn account. We will take you to the workspace for your account role.</p>
          </div>
          <form className="profile-form auth-form" onSubmit={submit}>
            <label className="field">Email address
              <input type="email" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" />
            </label>
            <PasswordField label="Password" autoComplete="current-password" required value={password} onChange={setPassword} placeholder="Enter your password" />
            <label className="remember-email">
              <input type="checkbox" checked={rememberEmail} onChange={event => {
                setRememberEmail(event.target.checked)
                if (!event.target.checked) saveRememberedEmail("", false)
              }} />
              <span><strong>Remember my email on this device</strong><small>Only your email is saved. Your password is never stored.</small></span>
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
