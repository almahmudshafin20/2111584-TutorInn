import { useState, type FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { completePasswordReset } from "../api/auth"

export default function ResetPasswordPage() {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") || ""
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [notice, setNotice] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError("")
    setNotice("")
    try {
      const result = await completePasswordReset(token, newPassword, confirmPassword)
      setNotice(result.message)
      window.history.replaceState(null, "", "/reset-password")
      setNewPassword("")
      setConfirmPassword("")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not reset the password.")
    } finally {
      setLoading(false)
    }
  }

  return <AppLayout><section className="auth-shell auth-shell-recovery"><div className="auth-content">
    <div className="auth-form-heading"><p className="eyebrow">SECURE ACCOUNT RECOVERY</p><h1>Set a new password</h1></div>
    {!token ? <p role="alert" className="alert error">This reset link is missing its token. Request a new link.</p> : <form className="profile-form auth-form" onSubmit={submit}>
      <label className="field" htmlFor="new-password">New password
        <input id="new-password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={newPassword} onChange={event => setNewPassword(event.target.value)} />
      </label>
      <label className="field" htmlFor="confirm-password">Confirm new password
        <input id="confirm-password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} />
      </label>
      <button className="button primary auth-submit" type="submit" disabled={loading}>{loading ? "Saving…" : "Reset password"}</button>
    </form>}
    {notice && <p role="status" className="alert success">{notice} <a href="/login">Sign in</a></p>}
    {error && <p role="alert" className="alert error">{error}</p>}
    <p className="auth-footnote"><a className="text-link" href="/login">Back to sign in</a></p>
  </div></section></AppLayout>
}
