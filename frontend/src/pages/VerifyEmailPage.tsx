import { useEffect, useState, type FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { requestEmailVerification, verifyEmail } from "../api/auth"

export default function VerifyEmailPage() {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") || ""
  const [email, setEmail] = useState("")
  const [notice, setNotice] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(Boolean(token))

  useEffect(() => {
    if (!token) return
    let active = true
    void verifyEmail(token).then(result => {
      if (!active) return
      setNotice(result.message)
      window.history.replaceState(null, "", "/verify-email")
    }).catch(reason => {
      if (active) setError(reason instanceof Error ? reason.message : "Could not verify this email address.")
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [token])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError("")
    setNotice("")
    try {
      const result = await requestEmailVerification(email)
      setNotice(result.message)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not request a verification email.")
    } finally {
      setLoading(false)
    }
  }

  return <AppLayout><section className="auth-shell auth-shell-recovery"><div className="auth-content">
    <div className="auth-form-heading"><p className="eyebrow">ACCOUNT SECURITY</p><h1>Verify your email</h1>
      <p>Confirm that you own the email address on your TutorInn account. Verification links expire after 30 minutes.</p></div>
    {loading ? <p role="status" className="muted">Verifying your email…</p> : !token && <form className="profile-form auth-form" onSubmit={submit}>
      <label className="field" htmlFor="verify-email-address">Email address
        <input id="verify-email-address" type="email" autoComplete="email" required maxLength={255} value={email} onChange={event => setEmail(event.target.value)} />
      </label>
      <button className="button primary auth-submit" type="submit" disabled={loading}>{loading ? "Sending…" : "Send verification link"}</button>
    </form>}
    {notice && <p role="status" className="alert success">{notice}</p>}
    {error && <p role="alert" className="alert error">{error}</p>}
    <p className="auth-footnote"><a className="text-link" href="/login">Back to sign in</a></p>
  </div></section></AppLayout>
}
