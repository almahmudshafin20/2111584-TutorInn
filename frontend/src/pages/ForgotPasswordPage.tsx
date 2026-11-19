import { useState, type FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { requestPasswordReset } from "../api/auth"

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [notice, setNotice] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError("")
    setNotice("")
    try {
      const result = await requestPasswordReset(email)
      setNotice(result.message)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not submit the request.")
    } finally {
      setLoading(false)
    }
  }

  return <AppLayout><section className="auth-shell auth-shell-recovery"><div className="auth-content">
    <div className="auth-form-heading"><p className="eyebrow">ACCOUNT RECOVERY</p><h1>Forgot your password?</h1>
      <p>Enter the email address associated with your TutorInn account. Your request will be reviewed before a reset link can be sent.</p></div>
    <form className="profile-form auth-form" onSubmit={submit}>
      <label className="field" htmlFor="reset-request-email">Email address
        <input id="reset-request-email" type="email" autoComplete="email" required maxLength={255} value={email} onChange={event => setEmail(event.target.value)} />
      </label>
      <button className="button primary auth-submit" type="submit" disabled={loading}>{loading ? "Submitting…" : "Submit request"}</button>
    </form>
    {notice && <p role="status" className="alert success">{notice}</p>}
    {error && <p role="alert" className="alert error">{error}</p>}
    <p className="auth-footnote"><a className="text-link" href="/login">Back to sign in</a></p>
  </div></section></AppLayout>
}
