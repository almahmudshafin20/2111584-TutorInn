import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import { getContentReports, reviewContentReport, type ContentReport } from "../api/moderation"

export default function AdminReportsPage() {
  const { account, loading } = useAuth()
  const [items, setItems] = useState<ContentReport[]>([])
  const [status, setStatus] = useState("pending")
  const [search, setSearch] = useState("")
  const [note, setNote] = useState<Record<number, string>>({})
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState(false)
  async function load() { setBusy(true); setError(""); try { const result = await getContentReports({ status, q: search, limit: 100 }); setItems(result.items) } catch (e) { setError(e instanceof Error ? e.message : "Could not load reports.") } finally { setBusy(false) } }
  useEffect(() => { if (account?.role === "admin") void load() }, [account?.id, account?.role, status])
  if (loading) return <AppLayout><p>Checking your account…</p></AppLayout>
  if (!account || account.role !== "admin") return <AppLayout><section className="page-intro"><h1>Admin access required</h1><a href="/login" className="button primary">Sign in</a></section></AppLayout>
  async function update(item: ContentReport, next: string) {
    const reason = (note[item.id] ?? "").trim()
    if (reason.length < 5) { setError("Add an Admin review note of at least 5 characters before changing a report."); return }
    setBusy(true); setError("")
    try { await reviewContentReport(item.id, next, reason); setNotice(`Report #${item.id} updated to ${next.replace("_", " ")}.`); setNote(current => ({ ...current, [item.id]: "" })); await load() }
    catch (e) { setError(e instanceof Error ? e.message : "Could not update report.") } finally { setBusy(false) }
  }
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">ADMIN MODERATION</p><h1>Community reports</h1><p>Review reports about Student and Tutor profiles, tutoring offers and tutoring requests.</p><div className="actions"><a className="button secondary" href="/admin">Admin dashboard</a><a className="button secondary" href="/admin/subjects">Manage subjects</a></div></section>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel"><div className="admin-toolbar"><label className="field">Report status<select value={status} onChange={e => setStatus(e.target.value)}><option value="pending">Pending</option><option value="in_review">In review</option><option value="resolved">Resolved</option><option value="dismissed">Dismissed</option><option value="">All reports</option></select></label><label className="field">Search<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Reason or report details" /></label><button className="button secondary" onClick={() => void load()} disabled={busy}>Search / refresh</button></div>
      {busy && <p className="muted">Loading reports…</p>}
      {items.length === 0 && !busy ? <div className="empty-state">No reports in this view.</div> : items.map(item => <article className="profile-card" key={item.id}><div className="profile-info"><div className="admin-toolbar-actions"><strong>Report #{item.id} · {item.target_type.replaceAll("_", " ")}</strong><span>{item.status.replace("_", " ")}</span></div><p><strong>Target:</strong> {item.target_label} (#{item.target_id})</p><p><strong>Reported by:</strong> {item.reporter_email} · {new Date(item.created_at).toLocaleString()}</p><p><strong>Reason:</strong> {item.reason}</p><p>{item.description || "No additional details supplied."}</p>{item.review_note && <p><strong>Previous review note:</strong> {item.review_note}</p>}
        {item.status !== "resolved" && item.status !== "dismissed" && <><label className="field">Admin review note<textarea rows={2} minLength={5} maxLength={1000} value={note[item.id] ?? ""} onChange={e => setNote(current => ({ ...current, [item.id]: e.target.value }))} placeholder="Record the investigation outcome (minimum 5 characters)" /></label><div className="actions"><button className="button secondary" disabled={busy} onClick={() => void update(item, "in_review")}>Mark in review</button><button className="button primary" disabled={busy} onClick={() => void update(item, "resolved")}>Resolve</button><button className="button secondary danger-text" disabled={busy} onClick={() => void update(item, "dismissed")}>Dismiss</button></div></>}
      </div></article>)}
    </section>
  </AppLayout>
}
