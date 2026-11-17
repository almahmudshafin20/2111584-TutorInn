import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import { getAdminDeletionRequests, reviewAdminDeletionRequest, type AdminDeletionRequest } from "../api/admin"

export default function AdminDeletionRequestsPage() {
  const { account, loading: authLoading } = useAuth()
  const [items, setItems] = useState<AdminDeletionRequest[]>([])
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false)
  const [error, setError] = useState(""), [notice, setNotice] = useState("")
  async function load() { setLoading(true); setError(""); try { const result = await getAdminDeletionRequests(); setItems(result.items) } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load deletion requests.") } finally { setLoading(false) } }
  useEffect(() => { if (account?.role === "admin") void load(); else setLoading(false) }, [account])
  async function review(item: AdminDeletionRequest, status: "approved" | "rejected") {
    const action = status === "approved" ? "PERMANENTLY DELETE this account and all content owned or created by it" : "reject this request and reactivate the account"
    if (!window.confirm("Are you sure you want to " + action + "? This decision will be recorded in the audit history.")) return
    const note = window.prompt("Optional Admin review note (up to 1000 characters):", "")
    if (note === null) return
    setBusy(true); setError(""); setNotice("")
    try { await reviewAdminDeletionRequest(item.id, status, note); setNotice(status === "approved" ? "Account and associated content permanently deleted." : "Request rejected; account reactivated."); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not review this request.") }
    finally { setBusy(false) }
  }
  if (authLoading) return <AppLayout><p className="muted">Checking your session…</p></AppLayout>
  if (!account) return <AppLayout><section className="empty-state auth-required"><h1>Sign in required</h1><a className="button primary" href="/login">Sign in</a></section></AppLayout>
  if (account.role !== "admin") return <AppLayout><section className="empty-state auth-required"><h1>Admin access required</h1><p>This page is available only to Admin accounts.</p><a className="button primary" href="/dashboard">Back to workspace</a></section></AppLayout>
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">ADMINISTRATION</p><h1>Account deletion requests</h1><p>Review requests from Students and Tutors. Approval permanently removes their accounts and associated content where possible.</p><div className="actions"><a className="button secondary" href="/admin">Back to Admin dashboard</a><button className="button secondary" onClick={() => void load()}>Refresh</button></div></section>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel dashboard-panel"><div className="panel-heading"><div><h2>Pending requests</h2><p className="muted">{items.length} request(s) loaded</p></div></div>
      {loading ? <p className="muted">Loading requests…</p> : items.length === 0 ? <p className="muted">There are no pending account deletion requests.</p> : <div className="profile-list">{items.map(item => <article className="profile-card" key={item.id}><div className="profile-info"><h3>{item.account_email}</h3><p>Role: {item.account_role} · Requested: {new Date(item.requested_at).toLocaleString()}</p><p>Request reason: {item.reason || "No reason supplied."}</p><p className="muted">Request #{item.id}</p></div><div className="actions"><button className="button secondary" disabled={busy} onClick={() => void review(item, "rejected")}>Reject and reactivate</button><button className="button secondary danger-text" disabled={busy} onClick={() => void review(item, "approved")}>Approve permanent deletion</button></div></article>)}</div>}
    </section>
  </AppLayout>
}
