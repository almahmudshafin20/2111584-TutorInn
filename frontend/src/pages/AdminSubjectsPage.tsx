import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import { createManagedSubject, deleteManagedSubject, getManagedSubjects, updateManagedSubject, type ManagedSubject } from "../api/moderation"

export default function AdminSubjectsPage() {
  const { account, loading } = useAuth()
  const [items, setItems] = useState<ManagedSubject[]>([])
  const [name, setName] = useState("")
  const [editing, setEditing] = useState<number | null>(null)
  const [draft, setDraft] = useState("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState(false)
  async function load() { setBusy(true); setError(""); try { setItems(await getManagedSubjects()) } catch (e) { setError(e instanceof Error ? e.message : "Could not load subjects.") } finally { setBusy(false) } }
  useEffect(() => { if (account?.role === "admin") void load() }, [account?.id, account?.role])
  if (loading) return <AppLayout><p>Checking your account…</p></AppLayout>
  if (!account || account.role !== "admin") return <AppLayout><section className="page-intro"><h1>Admin access required</h1><a href="/login" className="button primary">Sign in</a></section></AppLayout>
  async function add(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); setError(""); try { await createManagedSubject(name.trim()); setName(""); setNotice("Subject created."); await load() } catch (e) { setError(e instanceof Error ? e.message : "Could not create subject.") } finally { setBusy(false) } }
  async function save(item: ManagedSubject) { setBusy(true); setError(""); try { await updateManagedSubject(item.id, { name: draft.trim() }); setEditing(null); setNotice("Subject updated."); await load() } catch (e) { setError(e instanceof Error ? e.message : "Could not update subject.") } finally { setBusy(false) } }
  async function toggle(item: ManagedSubject) { setBusy(true); setError(""); try { await updateManagedSubject(item.id, { active: !item.active }); setNotice(`Subject ${item.active ? "deactivated" : "activated"}.`); await load() } catch (e) { setError(e instanceof Error ? e.message : "Could not update subject.") } finally { setBusy(false) } }
  async function remove(item: ManagedSubject) { if (!window.confirm(`Delete “${item.name}”? Subjects used by profiles or listings cannot be deleted; deactivate them instead.`)) return; setBusy(true); setError(""); try { await deleteManagedSubject(item.id); setNotice("Subject deleted."); await load() } catch (e) { setError(e instanceof Error ? e.message : "Could not delete subject.") } finally { setBusy(false) } }
  const activeItems = items.filter(item => item.active)
  const inactiveItems = items.filter(item => !item.active)
  const renderSubject = (item: ManagedSubject) => (<article className="profile-card" key={item.id}><div className="profile-info">{editing === item.id ? <div className="search-form"><input autoFocus maxLength={80} value={draft} onChange={e => setDraft(e.target.value)} /><button className="small-button" disabled={busy || draft.trim().length < 2} onClick={() => void save(item)}>Save</button><button className="small-button" onClick={() => setEditing(null)}>Cancel</button></div> : <strong>{item.name}</strong>}<p>{item.active ? "Active — available for profile selection" : "Inactive — hidden from new profile selections"}</p></div><div className="actions"><button className="small-button" disabled={busy} onClick={() => { setEditing(item.id); setDraft(item.name) }}>Rename</button><button className="small-button" disabled={busy} onClick={() => void toggle(item)}>{item.active ? "Deactivate" : "Activate"}</button><button className="small-button danger-text" disabled={busy} onClick={() => void remove(item)}>Delete</button></div></article>)
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">ADMIN CATALOGUE</p><h1>Subject management</h1><p>Maintain the active subjects available to Student and Tutor profile forms. Deactivate a subject to stop new selections while preserving existing profile data. Deactivated subjects move to their own section below, where you can activate them again.</p><div className="actions"><a className="button secondary" href="/admin">Admin dashboard</a><a className="button secondary" href="/admin/reports">Review reports</a></div></section>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel"><h2>Add a subject</h2><form className="search-form" onSubmit={add}><input required minLength={2} maxLength={80} value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Mathematics" /><button className="button primary" disabled={busy || name.trim().length < 2}>Add subject</button></form></section>
    <section className="panel"><div className="admin-toolbar-actions"><h2>Active subjects ({activeItems.length})</h2><button className="button secondary" disabled={busy} onClick={() => void load()}>Refresh</button></div>
      {activeItems.map(renderSubject)}
      {!activeItems.length && items.length > 0 && <div className="empty-state">All subjects are deactivated. Activate one below to make it available again.</div>}
      {!items.length && !busy && <div className="empty-state">No subjects yet. Add the first catalogue entry above.</div>}
    </section>
    {inactiveItems.length > 0 && <section className="panel" aria-labelledby="deactivated-subjects-heading"><div className="admin-toolbar-actions"><h2 id="deactivated-subjects-heading">Deactivated subjects ({inactiveItems.length})</h2></div><p className="muted">Hidden from new profile selections. Existing profile data is kept, and you can activate a subject here at any time.</p>
      {inactiveItems.map(renderSubject)}
    </section>}
  </AppLayout>
}
