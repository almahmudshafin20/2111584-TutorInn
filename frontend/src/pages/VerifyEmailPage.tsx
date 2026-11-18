import { useEffect, useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { requestEmailVerification, completeEmailVerification } from "../api/auth"
import { useAuth } from "../context/AuthContext"

export default function VerifyEmailPage() {
  const { account } = useAuth()
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? ""
  const [email, setEmail] = useState(account?.email ?? "")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  useEffect(() => {
    if (!token) return
    setBusy(true)
    void completeEmailVerification(token).then(result => { setNotice(result.message); window.history.replaceState({}, "", "/verify-email") })
      .catch(reason => setError(reason instanceof Error ? reason.message : "Verification failed."))
      .finally(() => setBusy(false))
  }, [token])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("")
    try { const result = await requestEmailVerification(email); setNotice(result.message) }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not request verification.") }
    finally { setBusy(false) }
  }
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">EMAIL SECURITY</p><h1>Verify your email</h1><p>Password-reset links are sent only to email addresses verified for the matching TutorInn account.</p></section><section className="panel auth-panel">{busy && token ? <p className="muted">Checking your verification link…</p> : <form className="profile-form" onSubmit={submit}><label className="field">Account email<input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" /></label><button className="button primary" disabled={busy}>{busy ? "Sending…" : "Send verification link"}</button></form>}{error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}<p className="auth-footnote"><a className="text-link" href="/login">Back to login</a></p></section></AppLayout>
}
