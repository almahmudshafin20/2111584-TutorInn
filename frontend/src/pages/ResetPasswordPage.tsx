import { useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { PasswordField } from "../components/PasswordField"
import { completePasswordReset } from "../api/auth"

export default function ResetPasswordPage() {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? ""
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("")
    try { const result = await completePasswordReset(token, password, confirm); setNotice(result.message); setPassword(""); setConfirm(""); window.history.replaceState({}, "", "/reset-password") }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not reset your password.") }
    finally { setBusy(false) }
  }
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">SECURE ACCOUNT RECOVERY</p><h1>Choose a new password</h1><p>You do not need your old password. This one-time link expires after 30 minutes.</p></section><section className="panel auth-panel">{!token ? <div className="alert error" role="alert">The reset token is missing. Open the complete link from your email.</div> : <form className="profile-form" onSubmit={submit}><PasswordField label="New password" autoComplete="new-password" required value={password} onChange={setPassword} placeholder="At least 12 characters" /><PasswordField label="Confirm new password" autoComplete="new-password" required value={confirm} onChange={setConfirm} placeholder="Enter the same password again" />{error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}<button className="button primary" disabled={busy}>{busy ? "Updating…" : "Set new password"}</button></form>}<p className="auth-footnote"><a className="text-link" href="/login">Back to login</a></p></section></AppLayout>
}
