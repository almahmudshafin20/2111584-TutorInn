import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { api } from "../api/api"
import type { AdminDeletionContentSelection } from "../api/admin"

type Item = AdminDeletionContentSelection & { label: string; description: string; visibility: "visible" | "hidden" }
export default function FormerUserContentPage() {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? ""
  const [items, setItems] = useState<Item[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  useEffect(() => {
    if (!token) { setError("This verification link is missing or invalid."); setLoading(false); return }
    // Remove the one-time credential from the address bar/history before making any request.
    window.history.replaceState(null, "", window.location.pathname + window.location.search)
    void api<{ items: Item[] }>("/api/former-user/retained-content", { method: "POST", body: JSON.stringify({ token }) })
      .then(result => setItems(result.items))
      .catch(reason => setError(reason instanceof Error ? reason.message : "The verification link is invalid or expired."))
      .finally(() => setLoading(false))
  }, [token])
  function toggle(item: Item, checked: boolean) {
    const key = item.content_type + ":" + item.content_id
    setSelected(current => checked ? [...current, key] : current.filter(value => value !== key))
  }
  async function submit() {
    if (!selected.length) { setError("Select at least one retained item."); return }
    setBusy(true); setError(""); setNotice("")
    try {
      const selected_content = items.filter(item => selected.includes(item.content_type + ":" + item.content_id))
        .map(({ content_type, content_id }) => ({ content_type, content_id }))
      await api("/api/former-user/content-removal-requests", {
        method: "POST", body: JSON.stringify({ token, selected_content }),
      })
      setNotice("Your request has been submitted for Admin review. This one-time link can no longer be used.")
      setItems([]); setSelected([])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not submit your request.")
    } finally { setBusy(false) }
  }
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">FORMER USER</p><h1>Request removal of retained content</h1><p>Review content retained after your account deletion. Select the items you want TutorInn Admin to review for removal.</p></section>
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel dashboard-panel">
      {loading ? <p className="muted">Verifying your one-time link…</p> : items.length === 0 && !notice ? <p className="muted">No retained content is available for this link.</p> : null}
      {items.map(item => <label className="profile-card" key={item.content_type + ":" + item.content_id}>
        <input type="checkbox" checked={selected.includes(item.content_type + ":" + item.content_id)}
          onChange={event => toggle(item, event.target.checked)} />
        <span className="profile-info"><strong>{item.label}</strong><span>{item.description || "No description available."}</span><small>Visibility: {item.visibility}</small></span>
      </label>)}
      {items.length > 0 && <div className="actions"><button className="button primary" disabled={busy || selected.length === 0} onClick={() => void submit()}>{busy ? "Submitting…" : "Submit removal request"}</button></div>}
    </section>
  </AppLayout>
}
