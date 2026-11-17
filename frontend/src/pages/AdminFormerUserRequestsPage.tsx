import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import { getAdminFormerUserRemovalRequests, reviewAdminFormerUserRemovalRequest, type AdminFormerUserRemoval } from "../api/admin"

export default function AdminFormerUserRequestsPage() {
  const { account, loading: authLoading } = useAuth()
  const [items, setItems] = useState<AdminFormerUserRemoval[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  async function load() {
    setLoading(true); setError("")
    try { const result = await getAdminFormerUserRemovalRequests(); setItems(result.items) }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load former-user requests.") }
    finally { setLoading(false) }
  }
  useEffect(() => { if (account?.role === "admin") void load(); else setLoading(false) }, [account])
  async function review(item: AdminFormerUserRemoval, status: "approved" | "rejected") {
    const note = window.prompt("Optional Admin review note (up to 1000 characters):", "")
    if (note === null) return
    if (!window.confirm(status === "approved"
      ? "Permanently remove the selected retained content? This cannot be undone."
      : "Reject this removal request?")) return
    setBusy(true); setError(""); setNotice("")
    try {
      const result = await reviewAdminFormerUserRemovalRequest(item.id, status, note)
      setNotice(status === "approved" ? `Approved. ${result.removed_items} selected item(s) removed.` : "Request rejected.")
      await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not review this request.") }
    finally { setBusy(false) }
  }
  if (authLoading) return <AppLayout><p className="muted">Checking your session…</p></AppLayout>
  if (!account) return <AppLayout><section className="empty-state auth-required"><h1>Sign in required</h1><a className="button primary" href="/login">Sign in</a></section></AppLayout>
  if (account.role !== "admin") return <AppLayout><section className="empty-state auth-required"><h1>Admin access required</h1></section></AppLayout>
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">ADMINISTRATION</p><h1>Former-user content removal</h1><p>Review one-time verified requests to remove content retained after account deletion.</p><div className="actions"><a className="button secondary" href="/admin/deletions">Back to account deletion</a><button className="button secondary" onClick={() => void load()}>Refresh</button></div></section>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel dashboard-panel"><h2>Pending requests</h2>
      {loading ? <p className="muted">Loading…</p> : items.length === 0 ? <p className="muted">No pending former-user requests.</p> :
        <div className="profile-list">{items.map(item => <article className="profile-card" key={item.id}><div className="profile-info">
          <h3>Former account: {item.account_email}</h3><p>Request #{item.id} · Deletion #{item.deletion_request_id} · {new Date(item.requested_at).toLocaleString()}</p>
          <p>Selected for removal: {item.selected_content.map(value => value.content_type + " #" + value.content_id).join(", ")}</p>
          <p>Retained items: {item.available_retained_content.length}</p>
        </div><div className="actions"><button className="button secondary" disabled={busy} onClick={() => void review(item, "rejected")}>Reject</button><button className="button secondary danger-text" disabled={busy} onClick={() => void review(item, "approved")}>Approve removal</button></div></article>)}</div>}
    </section>
  </AppLayout>
}
