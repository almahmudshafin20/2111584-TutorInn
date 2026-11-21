import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import { listPasswordResetRequests, reviewPasswordResetRequest, type PasswordResetRequestRow } from "../api/auth"

export default function PasswordResetRequestsPage() {
  const { account, loading: authLoading } = useAuth()
  const [items, setItems] = useState<PasswordResetRequestRow[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  async function load() {
    setBusy(true); setError("")
    try { const result = await listPasswordResetRequests("all"); setItems(result.items) }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load requests.") }
    finally { setBusy(false) }
  }
  useEffect(() => { if (account && ["admin", "moderator"].includes(account.role)) void load() }, [account])
  async function review(item: PasswordResetRequestRow, status: "approved" | "rejected") {
    const note = window.prompt("Optional review note (do not enter any password or token):", "")
    if (note === null) return
    if (!window.confirm(status === "approved" ? "Approve and send a secure reset link to the user's verified email?" : "Reject this password-reset request?")) return
    setBusy(true); setError(""); setNotice("")
    try {
      const result = await reviewPasswordResetRequest(item.id, status, note)
      setNotice(status === "approved" ? (result.delivery_status === "sent" ? "Approved; reset email sent." : "Approved; email delivery status: " + result.delivery_status) : "Request rejected.")
      await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not review request.") }
    finally { setBusy(false) }
  }
  if (authLoading) return <AppLayout><p className="muted">Checking access…</p></AppLayout>
  if (!account) return <AppLayout><section className="empty-state auth-required"><h1>Sign in required</h1><a className="button primary" href="/login">Sign in</a></section></AppLayout>
  if (!["admin", "moderator"].includes(account.role)) return <AppLayout><section className="empty-state auth-required"><h1>Reviewer access required</h1><p>Only First Admin, Admin and Moderator accounts can review password-reset requests.</p></section></AppLayout>
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">ACCOUNT SECURITY</p><h1>Password-reset requests</h1><p>Review Student and Tutor requests. Approval sends a one-time link to the verified account email. Passwords and raw reset tokens are never displayed here.</p><div className="actions"><a className="button secondary" href="/admin">Admin workspace</a><button className="button secondary" onClick={() => void load()} disabled={busy}>Refresh</button></div></section>{error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}{busy && <p className="muted">Loading…</p>}<section className="panel"><div className="profile-list">{items.length === 0 ? <div className="empty-state"><h3>No password-reset requests</h3><p>New requests will appear here.</p></div> : items.map(item => <article className="profile-card" key={item.id}><div className="profile-info"><h3>{item.account_email}</h3><p>{item.account_role} · Request #{item.id} · {item.status}</p><p className="muted">Requested: {new Date(item.requested_at).toLocaleString()}</p>{item.reviewed_at && <p className="muted">Reviewed: {new Date(item.reviewed_at).toLocaleString()} by {item.reviewer_email ?? "unknown reviewer"}</p>}{item.review_note && <p>Review note: {item.review_note}</p>}{item.status === "pending" && <div className="actions"><button className="button primary" disabled={busy} onClick={() => void review(item, "approved")}>Approve</button><button className="button secondary" disabled={busy} onClick={() => void review(item, "rejected")}>Reject</button></div>}</div></article>)}</div></section></AppLayout>
}
