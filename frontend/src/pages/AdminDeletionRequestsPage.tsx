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
    let deletionOption: "anonymize" | "complete" | undefined
    if (status === "approved") {
      const chosen = window.prompt(
        "Choose the final method for " + item.account_email + ". User requested: " +
        (item.requested_option === "complete" ? "Complete removal" : "Anonymize") +
        ". Enter 1 for Anonymize or 2 for Complete removal.",
        item.requested_option === "complete" ? "2" : "1",
      )
      if (chosen === null) return
      if (chosen !== "1" && chosen !== "2") { setError("Enter 1 for Anonymize or 2 for Complete removal."); return }
      deletionOption = chosen === "1" ? "anonymize" : "complete"
    }
    const action = status === "approved"
      ? (deletionOption === "anonymize" ? "anonymize the account and retain eligible shared content" : "permanently remove the account and its associated content")
      : "reject the request and reactivate the account"
    if (!window.confirm("Confirm: " + action + "? The final method will be recorded in the deletion receipt.")) return
    const note = window.prompt("Optional Admin review note (up to 1000 characters):", "")
    if (note === null) return
    setBusy(true); setError(""); setNotice("")
    try {
      await reviewAdminDeletionRequest(item.id, status, note, deletionOption)
      setNotice(status === "approved"
        ? (deletionOption === "anonymize" ? "Account anonymized. Eligible shared learning content was retained." : "Account and associated content permanently deleted.")
        : "Request rejected; account reactivated.")
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not review this request.")
    } finally { setBusy(false) }
  }
  if (authLoading) return <AppLayout><p className="muted">Checking your session…</p></AppLayout>
  if (!account) return <AppLayout><section className="empty-state auth-required"><h1>Sign in required</h1><a className="button primary" href="/login">Sign in</a></section></AppLayout>
  if (account.role !== "admin") return <AppLayout><section className="empty-state auth-required"><h1>Admin access required</h1><p>This page is available only to Admin accounts.</p><a className="button primary" href="/dashboard">Back to workspace</a></section></AppLayout>
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">ADMINISTRATION</p><h1>Account deletion requests</h1><p>Review requests from Students and Tutors. Approval permanently removes their accounts and associated content where possible.</p><div className="actions"><a className="button secondary" href="/admin">Back to Admin dashboard</a><button className="button secondary" onClick={() => void load()}>Refresh</button></div></section>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel dashboard-panel"><div className="panel-heading"><div><h2>Pending requests</h2><p className="muted">{items.length} request(s) loaded</p></div></div>
      {loading ? <p className="muted">Loading requests…</p> : items.length === 0 ? <p className="muted">There are no pending account deletion requests.</p> : <div className="profile-list">{items.map(item => <article className="profile-card" key={item.id}><div className="profile-info"><h3>{item.account_email}</h3><p>Role: {item.account_role} · Requested: {new Date(item.requested_at).toLocaleString()}</p><p>Requested method: <strong>{item.requested_option === "complete" ? "Complete removal" : "Anonymize"}</strong></p><p>Request reason: {item.reason || "No reason supplied."}</p><p className="muted">Request #{item.id}</p></div><div className="actions"><button className="button secondary" disabled={busy} onClick={() => void review(item, "rejected")}>Reject and reactivate</button><button className="button secondary danger-text" disabled={busy} onClick={() => void review(item, "approved")}>Approve and choose method</button></div></article>)}</div>}
    </section>
  </AppLayout>
}
