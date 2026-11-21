import { useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { requestPasswordReset } from "../api/auth"

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("")
    try { const result = await requestPasswordReset(email); setNotice(result.message) }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not submit the request.") }
    finally { setBusy(false) }
  }
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">ACCOUNT RECOVERY</p><h1>Forgot password?</h1><p>Submit a request for review. First Admin, Admin or Moderator must approve it before a secure reset link is sent to your verified email.</p></section><section className="panel auth-panel"><form className="profile-form" onSubmit={submit}><label className="field">Account email<input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" /></label>{error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}<button className="button primary" disabled={busy}>{busy ? "Submitting…" : "Submit reset request"}</button></form><p className="auth-footnote"><a className="text-link" href="/verify-email">Need to verify your email first?</a></p></section></AppLayout>
}
