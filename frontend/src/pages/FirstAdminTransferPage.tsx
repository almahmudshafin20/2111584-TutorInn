import { useEffect, useState, type FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import {
  acceptFirstAdminTransfer, cancelFirstAdminTransfer, declineFirstAdminTransfer, getFirstAdminTransfer,
  startFirstAdminTransfer, type FirstAdminTransferState,
} from "../api/firstAdminTransfer"

export default function FirstAdminTransferPage() {
  const { account, loading: authLoading } = useAuth()
  const [state, setState] = useState<FirstAdminTransferState | null>(null)
  const [recipient, setRecipient] = useState("")
  const [confirmRecipient, setConfirmRecipient] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  async function load() {
    setBusy(true); setError("")
    try { setState(await getFirstAdminTransfer()) }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load the transfer status.") }
    finally { setBusy(false) }
  }
  useEffect(() => { if (account?.role === "admin") void load() }, [account])

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setNotice("")
    try {
      await action()
      setNotice(success)
      setPassword("")
      await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The action could not be completed.") }
    finally { setBusy(false) }
  }

  function start(event: FormEvent) {
    event.preventDefault()
    if (!window.confirm("Transfer the First Admin role to the recipient? This is the platform's highest-privilege authority. You will stay an ordinary Admin, and the recipient must accept within 24 hours.")) return
    void run(() => startFirstAdminTransfer(recipient, confirmRecipient, password), "Transfer requested. The recipient must accept it within 24 hours.")
  }

  if (authLoading) return <AppLayout><p className="muted">Checking access…</p></AppLayout>
  if (!account) return <AppLayout><section className="empty-state auth-required"><h1>Sign in required</h1><a className="button primary" href="/login">Sign in</a></section></AppLayout>
  if (account.role !== "admin") return <AppLayout><section className="empty-state auth-required"><h1>Admin access required</h1><p>Only Admin accounts can view First Admin ownership transfers.</p></section></AppLayout>

  const pending = state?.pending ?? null
  const isRecipient = pending !== null && pending.recipient_email === account.email
  const isInitiator = pending !== null && pending.initiator_email === account.email

  return (
    <AppLayout>
      <section className="page-intro compact">
        <p className="eyebrow">PLATFORM OWNERSHIP</p>
        <h1>First Admin ownership transfer</h1>
        <p>
          The First Admin holds the platform's highest-privilege authority, including activity cleanup and granting Admin access.
          A transfer moves that authority to another existing Admin account. It is not an ordinary Admin role change.
        </p>
        <p className="muted">The recipient must accept within 24 hours. When accepted, you remain an ordinary Admin and all active sessions for both accounts are signed out.</p>
        <div className="actions"><a className="button secondary" href="/admin">Admin workspace</a><button className="button secondary" onClick={() => void load()} disabled={busy}>Refresh</button></div>
      </section>
      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}
      {busy && <p className="muted">Loading…</p>}

      {pending && (
        <section className="panel">
          <h2>Pending transfer</h2>
          <p>From <strong>{pending.initiator_email}</strong> to <strong>{pending.recipient_email}</strong>.</p>
          <p className="muted">Expires: {new Date(pending.expires_at).toLocaleString()}</p>
          {isRecipient && (
            <div className="actions">
              <button className="button primary" disabled={busy} onClick={() => {
                if (window.confirm("Accept the First Admin role? This transfers the platform's highest-privilege authority to your account.")) void run(acceptFirstAdminTransfer, "You are now the First Admin. Please sign in again.")
              }}>Accept First Admin role</button>
              <button className="button secondary" disabled={busy} onClick={() => void run(declineFirstAdminTransfer, "Transfer declined.")}>Decline</button>
            </div>
          )}
          {isInitiator && (
            <div className="actions">
              <button className="button secondary" disabled={busy} onClick={() => void run(cancelFirstAdminTransfer, "Transfer cancelled.")}>Cancel transfer</button>
            </div>
          )}
          {!isRecipient && !isInitiator && <p className="muted">Only the initiating First Admin or the named recipient can act on this transfer.</p>}
        </section>
      )}

      {state?.can_start && (
        <section className="panel">
          <h2>Start a transfer</h2>
          <form className="form-stack" onSubmit={start}>
            <label>Recipient Admin email
              <input type="email" value={recipient} onChange={event => setRecipient(event.target.value)} required autoComplete="off" />
            </label>
            <label>Type the recipient email again
              <input type="email" value={confirmRecipient} onChange={event => setConfirmRecipient(event.target.value)} required autoComplete="off" />
            </label>
            <label>Your password (re-confirmation)
              <input type="password" value={password} onChange={event => setPassword(event.target.value)} required autoComplete="current-password" />
            </label>
            <button className="button primary" type="submit" disabled={busy}>Request transfer</button>
          </form>
          <p className="muted">Passwords are never displayed or stored in this page.</p>
        </section>
      )}
      {state && !state.can_start && !pending && <p className="muted">Only the current First Admin can start a transfer.</p>}
    </AppLayout>
  )
}
