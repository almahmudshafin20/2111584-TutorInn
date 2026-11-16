import { useEffect, useRef, useState } from "react"
import { AppLayout as Layout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import {
  bulkDeleteAdminTasks, bulkSetAdminUserStatus, deleteAdminGroup, exportAdminCsv, getAdminActivity, getAdminGroups, purgeAdminActivity,
  getAdminOverview, getAdminRequests, getAdminSecurity, getAdminTasks, getAdminTutors, getAdminUser, getAdminUsers,
  reviewAdminTutor, setAdminUserStatus, type AdminActivity, type AdminGroup, type AdminOverview, type AdminTask,
  type AdminTutor, type AdminUser,
} from "../api/admin"

type Tab = "overview" | "students" | "tutors" | "requests" | "tasks" | "activity" | "security" | "settings"
const tabs: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" }, { id: "students", label: "Students" },
  { id: "tutors", label: "Tutors" }, { id: "requests", label: "Tutoring requests" }, { id: "tasks", label: "Tasks & groups" },
  { id: "activity", label: "Activity" }, { id: "security", label: "Security" }, { id: "settings", label: "Settings" },
]
const pageSize = 20
type ReasonDialog = { title: string; description: string; placeholder: string; confirmLabel: string; required: boolean; onSubmit: (reason: string) => Promise<void> }

export default function AdminReviewPage() {
  const { account, loading: authLoading } = useAuth()
  const params = new URLSearchParams(window.location.search)
  const [tab, setTab] = useState<Tab>((tabs.some(item => item.id === params.get("tab")) ? params.get("tab") : "overview") as Tab)
  const [search, setSearch] = useState(params.get("q") ?? "")
  const [searchDraft, setSearchDraft] = useState(params.get("q") ?? "")
  const [overviewActivity, setOverviewActivity] = useState<AdminActivity[]>([])
  const loadSequence = useRef(0)
  const [status, setStatus] = useState(params.get("status") ?? "")
  const [page, setPage] = useState(Math.max(0, Number(params.get("page") ?? 0) || 0))
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [tutors, setTutors] = useState<AdminTutor[]>([])
  const [tasks, setTasks] = useState<AdminTask[]>([])
  const [groups, setGroups] = useState<AdminGroup[]>([])
  const [selectedTasks, setSelectedTasks] = useState<number[]>([])
  const [rows, setRows] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [security, setSecurity] = useState<{ hours: number; min_events: number; incident_count: number; by_ip: { ip_address: string; count: number }[]; by_account: { account_id: number; count: number }[]; events: AdminActivity[] } | null>(null)
  const [securityHours, setSecurityHours] = useState(24)
  const [securityThreshold, setSecurityThreshold] = useState(3)
  const [selected, setSelected] = useState<number[]>([])
  const [detail, setDetail] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [reasonDialog, setReasonDialog] = useState<ReasonDialog | null>(null)
  const [reasonInput, setReasonInput] = useState("")
  const [dialogBusy, setDialogBusy] = useState(false)\n  const [purgeBefore, setPurgeBefore] = useState("")

  useEffect(() => {
    const next = new URLSearchParams()
    next.set("tab", tab)
    if (search) next.set("q", search)
    if (status) next.set("status", status)
    if (page) next.set("page", String(page))
    window.history.replaceState({}, "", window.location.pathname + "?" + next.toString())
  }, [tab, search, status, page])

  async function load() {
    if (!account || account.role !== "admin") return
    const sequence = ++loadSequence.current
    setBusy(true); setError("")
    try {
      const offset = page * pageSize
      if (tab === "overview") {
        const [summary, activity] = await Promise.all([getAdminOverview(), getAdminActivity({ offset: 0, limit: 6 })])
        if (sequence !== loadSequence.current) return
        setOverview(summary); setOverviewActivity(activity.items)
      }
      if (tab === "students") {
        const result = await getAdminUsers({ role: "student", status, q: search, offset, limit: pageSize })
        if (sequence !== loadSequence.current) return
        setUsers(result.items); setTotal(result.total)
      }
      if (tab === "tutors") {
        const result = await getAdminTutors({ verification_status: status, q: search, offset, limit: pageSize })
        if (sequence !== loadSequence.current) return
        setTutors(result.items); setTotal(result.total)
      }
      if (tab === "requests") {
        const result = await getAdminRequests({ status, q: search, offset, limit: pageSize })
        if (sequence !== loadSequence.current) return
        if (sequence !== loadSequence.current) return
        setRows(result.items); setTotal(result.total)
      }
      if (tab === "tasks") {
        const [taskResult, groupResult] = await Promise.all([getAdminTasks(offset, pageSize), getAdminGroups()])
        if (sequence !== loadSequence.current) return
        setTasks(taskResult.items); setTotal(taskResult.total); setGroups(groupResult)
      }
      if (tab === "activity") {
        const result = await getAdminActivity({ event_type: status, q: search, offset, limit: pageSize })
        setRows(result.items); setTotal(result.total)
      }
      if (tab === "security") { const report = await getAdminSecurity(securityHours, securityThreshold); if (sequence !== loadSequence.current) return; setSecurity(report) }
    } catch (cause) {
      if (sequence === loadSequence.current) setError(cause instanceof Error ? cause.message : "Could not load this Admin view.")
    } finally { if (sequence === loadSequence.current) setBusy(false) }
  }
  useEffect(() => { const timer = window.setTimeout(() => { setSearch(searchDraft); setPage(0) }, 280); return () => window.clearTimeout(timer) }, [searchDraft])
  useEffect(() => { void load(); return () => { loadSequence.current += 1 } }, [account?.id, account?.role, tab, search, status, page, securityHours, securityThreshold])

  function askForReason(dialog: ReasonDialog) { setReasonInput(""); setReasonDialog(dialog) }
  async function submitReason() {
    if (!reasonDialog || (reasonDialog.required && reasonInput.trim().length < 5)) return
    setDialogBusy(true)
    try { await reasonDialog.onSubmit(reasonInput.trim()); setReasonDialog(null); setReasonInput("") }
    catch (cause) { setError(cause instanceof Error ? cause.message : "The requested action failed.") }
    finally { setDialogBusy(false) }
  }
  async function moderate(user: AdminUser, nextStatus: string) {
    askForReason({ title: `Change account status`, description: `You are changing ${user.email} to “${nextStatus}”. This action will be recorded in the Admin audit trail.`, placeholder: "Explain the reason for this moderation action", confirmLabel: "Update account", required: true,
      onSubmit: async reason => { await setAdminUserStatus(user.id, nextStatus, reason); setNotice(`Account ${user.email} updated.`); setDetail(null); await load() } })
  }
  async function bulkModerate(nextStatus: string) {
    if (!selected.length || !window.confirm(`Change the status of ${selected.length} selected accounts?`)) return
    const ids = [...selected]
    askForReason({ title: `Bulk account moderation`, description: `The status of ${ids.length} selected accounts will be changed to “${nextStatus}”. Each result will be reported separately.`, placeholder: "Enter the reason for this bulk action", confirmLabel: "Apply to selected", required: true,
      onSubmit: async reason => { const result = await bulkSetAdminUserStatus(ids, nextStatus, reason); setNotice(`Bulk action complete: ${result.succeeded} succeeded, ${result.failed} failed.`); setSelected([]); await load() } })
  }
  async function inspectUser(id: number) {
    try { setDetail(await getAdminUser(id)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load account details.") }
  }
  async function verifyTutor(tutor: AdminTutor, nextStatus: string) {
    askForReason({ title: `Tutor qualification review`, description: `Set ${tutor.full_name}’s verification status to “${nextStatus}”. Add an optional note for the review record.`, placeholder: "Optional reviewer note", confirmLabel: `Set ${nextStatus}`, required: false,
      onSubmit: async note => { await reviewAdminTutor(tutor.id, nextStatus, note); setNotice(`${tutor.full_name}: verification set to ${nextStatus}.`); await load() } })
  }
  async function deleteSelectedTasks() {
    if (!selectedTasks.length || !window.confirm(`Permanently delete ${selectedTasks.length} selected personal tasks?`)) return
    const ids = [...selectedTasks]
    askForReason({ title: "Delete selected tasks", description: `This permanently deletes ${ids.length} selected personal tasks. The action will be recorded.`, placeholder: "Reason for deleting these tasks", confirmLabel: "Delete tasks", required: true,
      onSubmit: async reason => { const result = await bulkDeleteAdminTasks(ids, reason); setNotice(`Task deletion: ${result.succeeded} succeeded, ${result.failed} failed.`); setSelectedTasks([]); await load() } })
  }
  async function removeGroup(group: AdminGroup) {
    const confirmed = window.confirm(`Delete “${group.name}”? This removes ${group.member_count} memberships, ${group.task_count} group tasks and their assignments.`)
    if (!confirmed) return
    askForReason({ title: `Delete learning group`, description: `“${group.name}” has ${group.member_count} members and ${group.task_count} tasks. Its assignments will also be deleted.`, placeholder: "Reason for deleting this group", confirmLabel: "Delete group", required: true,
      onSubmit: async reason => { const result = await deleteAdminGroup(group.id, reason); setNotice(`Group deleted. Removed ${result.members_removed} memberships, ${result.tasks_removed} tasks and ${result.assignments_removed} assignments.`); await load() } })
  }
  async function download(kind: "users" | "tasks" | "activity") {
    try {
      const csv = await exportAdminCsv(kind)
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }))
      const link = document.createElement("a"); link.href = url; link.download = `tutorinn-${kind}.csv`; link.click()
      URL.revokeObjectURL(url)
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Export failed.") }
  }

  if (authLoading) return <Layout><section className="page-intro"><h1>Admin workspace</h1><p>Checking your account…</p></section></Layout>
  if (!account || account.role !== "admin") return <Layout><section className="page-intro"><p className="eyebrow">RESTRICTED AREA</p><h1>Admin access required</h1><p>Sign in with an authorized Admin account to manage TutorInn.</p><a className="button primary" href="/login">Sign in</a></section></Layout>

  const pages = Math.max(1, Math.ceil(total / pageSize))
  const metrics = overview ? [
    ["Students", overview.students], ["Tutors", overview.tutors], ["Tutoring requests", overview.tutoring_requests],
    ["Active accounts", overview.active_accounts], ["Banned accounts", overview.banned_accounts],
    ["Suspended accounts", overview.suspended_accounts], ["Pending tutor reviews", overview.pending_tutor_reviews],
  ] : []
  return <Layout>
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-heading"><span className="admin-sidebar-mark">T</span><div><strong>TutorInn</strong><small>ADMIN WORKSPACE</small></div></div>
        <p className="admin-nav-label">WORKSPACE</p>
        <nav className="admin-tabs" aria-label="Admin sections">{tabs.map((item, index) =>
          <button key={item.id} aria-current={tab === item.id ? "page" : undefined} className={tab === item.id ? "admin-nav-item active" : "admin-nav-item"} onClick={() => { setTab(item.id); setPage(0); setStatus(""); setSelected([]); setDetail(null) }}>
            <span className="admin-nav-icon" aria-hidden="true">{["▦","♙","✦","▤","☷","▧","◈","⚙"][index]}</span><span>{item.label}</span>{item.id === "tutors" && overview?.pending_tutor_reviews ? <em>{overview.pending_tutor_reviews}</em> : null}
          </button>
        )}</nav>
        <div className="admin-sidebar-note"><span className="admin-online-dot" /> Admin controls active <small>Actions are recorded in the audit trail.</small></div>
      </aside>
      <div className="admin-main">
        <header className="admin-page-heading">
          <div><p className="eyebrow">TUTORINN / ADMINISTRATION</p><h1>{tabs.find(item => item.id === tab)?.label ?? "Admin workspace"}</h1><p>Manage your tutoring platform, review activity and keep the community safe.</p></div>
          <button className="button secondary admin-refresh" onClick={() => void load()} disabled={busy}><span aria-hidden="true">↻</span> Refresh</button>
        </header>
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    {tab !== "overview" && tab !== "security" && tab !== "settings" && <section className="panel admin-toolbar">
      <label className="field">Search<input value={searchDraft} onChange={e => setSearchDraft(e.target.value)} placeholder="Search by name, email or subject" /></label>
      <label className="field">{tab === "students" ? "Account status" : tab === "tutors" ? "Verification" : tab === "requests" ? "Request status" : "Event type"}
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(0) }}>
          <option value="">All</option>
          {(tab === "students" ? ["active", "banned", "suspended"] : tab === "tutors" ? ["pending", "approved", "rejected"] : tab === "requests" ? ["Pending", "Accepted", "Completed", "Rejected"] : []).map(value => <option key={value} value={value}>{value}</option>)}
        </select>
      </label>
      <button className="button secondary" onClick={() => { setSearch(""); setSearchDraft(""); setStatus(""); setPage(0) }}>Clear filters</button>
    </section>}
    {busy && <p className="muted">Loading…</p>}
    {tab === "overview" && <>
      <section className="admin-overview-intro"><div><span className="admin-overview-kicker">PLATFORM SNAPSHOT</span><h2>Your platform at a glance</h2><p>Live totals from TutorInn accounts and tutoring activity.</p></div><span className="admin-updated"><i /> Data from the platform database</span></section>
      <section className="admin-metrics">{metrics.map(([label, value], index) =>
        <article className="panel admin-metric" key={label}><span className="admin-metric-icon">{["♙","✦","▤","●","⊘","◌","✓"][index]}</span><span className="admin-metric-label">{label}</span><strong>{Number(value).toLocaleString()}</strong><small>{index === 6 ? "Tutor profiles awaiting review" : index === 4 ? "Accounts blocked by moderation" : index === 5 ? "Accounts temporarily restricted" : index === 3 ? "Accounts in good standing" : index === 2 ? "Learning requests posted" : index === 0 ? "Registered learner profiles" : "Registered tutor profiles"}</small></article>)}</section>
      <section className="admin-overview-grid">
        <article className="panel admin-overview-panel"><div className="admin-panel-heading"><div><h2>Recent platform activity</h2><p>Latest recorded events across TutorInn</p></div><button className="small-button" onClick={() => setTab("activity")}>View activity →</button></div>
          {overviewActivity.length ? <div className="admin-recent-list">{overviewActivity.map(item => <div className="admin-recent-item" key={item.id}><span className="admin-event-dot" /><div><strong>{item.event_type.replaceAll("_"," ")}</strong><small>{item.target || (item.account_id ? `Account #${item.account_id}` : "System event")}</small></div><time>{new Date(item.created_at).toLocaleString()}</time></div>)}</div> : <div className="admin-empty-inline">No platform activity has been recorded yet.</div>}
        </article>
        <article className="panel admin-overview-panel"><div className="admin-panel-heading"><div><h2>Admin shortcuts</h2><p>Jump directly to common tasks</p></div></div>
          <div className="admin-shortcuts"><button onClick={() => setTab("students")}><span>♙</span><div><strong>Manage students</strong><small>Review accounts and moderation status</small></div><b>→</b></button>
            <button onClick={() => setTab("tutors")}><span>✦</span><div><strong>Review tutors</strong><small>Approve or reject tutor qualifications</small></div><b>→</b></button>
            <button onClick={() => setTab("requests")}><span>▤</span><div><strong>View tutoring requests</strong><small>Monitor learning requests and status</small></div><b>→</b></button>
            <button onClick={() => setTab("security")}><span>◈</span><div><strong>Security monitoring</strong><small>Investigate suspicious activity</small></div><b>→</b></button></div>
        </article>
      </section>
    </>}
    {tab === "students" && <section className="panel">
      <div className="admin-toolbar-actions"><h2>Student accounts <span className="muted">({total})</span></h2>
        <div className="actions"><button className="button secondary" onClick={() => void download("users")}>Export users CSV</button>
          <button className="button secondary" disabled={!selected.length} onClick={() => void bulkModerate("banned")}>Ban selected</button>
          <button className="button secondary" disabled={!selected.length} onClick={() => void bulkModerate("active")}>Unban selected</button></div></div>
      {users.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Select</th><th>Student</th><th>Email</th><th>Status</th><th>Actions</th></tr></thead><tbody>{users.map(user =>
        <tr key={user.id}><td><input type="checkbox" aria-label={`Select ${user.email}`} checked={selected.includes(user.id)} onChange={e => setSelected(current => e.target.checked ? [...current, user.id] : current.filter(id => id !== user.id))} /></td>
          <td>{user.profile?.full_name ?? "—"}</td><td>{user.email}</td><td>{user.status}</td><td><button className="small-button" onClick={() => void inspectUser(user.id)}>Details</button>
            {user.status === "active" ? <button className="small-button danger-text" onClick={() => void moderate(user, "banned")}>Ban</button> : <button className="small-button" onClick={() => void moderate(user, "active")}>Unban / reactivate</button>}</td></tr>)}</tbody></table></div> : <div className="empty-state">No student accounts found.</div>}
    </section>}
    {tab === "tutors" && <section className="panel"><div className="admin-toolbar-actions"><h2>Tutor qualification review <span className="muted">({total})</span></h2><button className="button secondary" onClick={() => void download("users")}>Export users CSV</button></div>
      {tutors.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Tutor</th><th>Subjects</th><th>Experience</th><th>Account</th><th>Verification</th><th>Review</th></tr></thead><tbody>{tutors.map(tutor =>
        <tr key={tutor.id}><td><strong>{tutor.full_name}</strong><small>{tutor.email}</small></td><td>{tutor.subjects.join(", ")}</td><td>{tutor.experience_years} years</td><td>{tutor.account_status}</td><td>{tutor.verification_status}</td><td><div className="actions">{tutor.account_id && <button className="small-button danger-text" onClick={() => void moderate({ id: tutor.account_id!, email: tutor.email, role: "tutor", status: tutor.account_status, created_at: "", updated_at: "", profile: null }, tutor.account_status === "active" ? "suspended" : "active")}>{tutor.account_status === "active" ? "Suspend" : "Reactivate"}</button>}<button className="small-button" onClick={() => void verifyTutor(tutor, "approved")}>Approve</button><button className="small-button danger-text" onClick={() => void verifyTutor(tutor, "rejected")}>Reject</button><button className="small-button" onClick={() => void verifyTutor(tutor, "pending")}>Pending</button></div></td></tr>)}</tbody></table></div> : <div className="empty-state">No tutor profiles match these filters.</div>}
    </section>}
    {tab === "requests" && <section className="panel"><div className="admin-toolbar-actions"><h2>Tutoring requests <span className="muted">({total})</span></h2></div>
      {rows.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>ID</th><th>Type</th><th>Author</th><th>Subjects</th><th>Level</th><th>Status</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td>#{row.id}</td><td>{row.type}</td><td>{row.author}</td><td>{row.subjects.join(", ")}</td><td>{row.level}</td><td>{row.status}</td></tr>)}</tbody></table></div> : <div className="empty-state">No tutoring requests found.</div>}
    </section>}
    {tab === "tasks" && <><section className="panel"><div className="admin-toolbar-actions"><h2>Personal learning tasks</h2><div className="actions"><button className="button secondary" onClick={() => void download("tasks")}>Export tasks & assignments CSV</button><button className="button secondary danger-text" disabled={!selectedTasks.length} onClick={() => void deleteSelectedTasks()}>Delete selected</button></div></div>{tasks.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Select</th><th>Task</th><th>Owner account</th><th>Due</th><th>Status</th></tr></thead><tbody>{tasks.map(task => <tr key={task.id}><td><input type="checkbox" aria-label={`Select task ${task.id}`} checked={selectedTasks.includes(task.id)} onChange={e => setSelectedTasks(current => e.target.checked ? [...current, task.id] : current.filter(id => id !== task.id))} /></td><td>{task.title}</td><td>{task.owner_account_id}</td><td>{task.due_date ?? "—"}</td><td>{task.completed ? "Completed" : "Open"}</td></tr>)}</tbody></table></div> : <div className="empty-state">No personal tasks found.</div>}</section><section className="panel"><h2>Learning groups</h2>{groups.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Group</th><th>Owner</th><th>Members</th><th>Tasks</th><th>Action</th></tr></thead><tbody>{groups.map(group => <tr key={group.id}><td>{group.name}</td><td>{group.owner_account_id}</td><td>{group.member_count}</td><td>{group.task_count}</td><td><button className="small-button danger-text" onClick={() => void removeGroup(group)}>Delete group</button></td></tr>)}</tbody></table></div> : <div className="empty-state">No learning groups found.</div>}</section></>}
    {tab === "activity" && <section className="panel"><div className="admin-toolbar-actions"><h2>Activity and audit trail <span className="muted">({total})</span></h2><button className="button secondary" onClick={() => void download("activity")}>Export activity CSV</button></div>
      {rows.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Event</th><th>Account</th><th>Target</th><th>IP</th><th>Time</th><th>Details</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td>{row.event_type}</td><td>{row.account_id ?? "—"}</td><td>{row.target || "—"}</td><td>{row.ip_address || "—"}</td><td>{row.created_at}</td><td>{row.details}</td></tr>)}</tbody></table></div> : <div className="empty-state">No activity records found.</div>}
    </section>}
    {tab === "security" && <section className="panel"><div className="admin-toolbar-actions"><div><h2>Security incidents</h2><p className="muted">Investigation signals for the selected time window</p></div><span>{security?.incident_count ?? 0} recent incidents</span></div>
      <div className="admin-security-filters"><label className="field">Time window<select value={securityHours} onChange={e => setSecurityHours(Number(e.target.value))}><option value={1}>Last hour</option><option value={24}>Last 24 hours</option><option value={72}>Last 3 days</option><option value={168}>Last 7 days</option><option value={720}>Last 30 days</option></select></label><label className="field">Minimum events<select value={securityThreshold} onChange={e => setSecurityThreshold(Number(e.target.value))}><option value={1}>1 or more</option><option value={3}>3 or more</option><option value={5}>5 or more</option><option value={10}>10 or more</option></select></label></div>
      <p className="muted">IP addresses are signals for investigation, not proof of identity. Do not automatically ban accounts that share an address.</p><div className="admin-security-summaries"><div><h3>Repeated source IPs</h3>{security?.by_ip.length ? security.by_ip.map(item => <p key={item.ip_address}>{item.ip_address}: {item.count} events</p>) : <p>No IP reached this threshold.</p>}</div><div><h3>Accounts with incidents</h3>{security?.by_account.length ? security.by_account.map(item => <p key={item.account_id}>Account {item.account_id}: {item.count} events</p>) : <p>No account reached this threshold.</p>}</div></div>
      {security?.events.map(event => <article className="profile-card" key={event.id}><div className="profile-info"><strong>{event.event_type}</strong><p>Account {event.account_id ?? "unknown"} · IP {event.ip_address || "unavailable"} · {event.created_at}</p></div></article>)}
      <button className="button secondary" onClick={() => void download("activity")}>Export activity CSV</button>
    </section>}
    {tab === "settings" && <section className="panel admin-settings-panel">
      <div className="admin-panel-heading"><div><h2>Administration settings</h2><p>Safe platform controls and retention operations</p></div></div>
      <div className="admin-settings-note"><strong>Environment and secrets</strong><p>Platform secrets and deployment configuration are intentionally not exposed in the Admin dashboard. Manage secrets through the hosting provider's protected environment settings.</p></div>
      <div className="admin-settings-note admin-retention-control"><strong>Activity retention cleanup</strong><p>Remove only successful-login activity older than 90 days. Security incidents, moderation history and Admin audit records are always preserved.</p>
        <label className="field">Remove successful-login events before<input type="datetime-local" value={purgeBefore} onChange={event => setPurgeBefore(event.target.value)} /></label>
        <button className="button secondary" disabled={!purgeBefore} onClick={() => {
          const before = new Date(purgeBefore)
          if (!Number.isFinite(before.getTime())) { setError("Choose a valid retention cutoff."); return }
          askForReason({ title: "Clean up old login activity", description: `Only successful-login events before ${before.toLocaleString()} will be removed. This cutoff must be at least 90 days old. Security, moderation and Admin audit events are preserved.`, placeholder: "Reason for this retention cleanup", confirmLabel: "Confirm cleanup", required: true,
            onSubmit: async reason => { const result = await purgeAdminActivity(before.toISOString(), reason); setNotice(`Retention cleanup complete: ${result.removed} successful-login events removed. ${result.preserved}`); setPurgeBefore(""); await load() } })
        }}>Review cleanup</button>
      </div>
    </section>}
    {tab !== "overview" && tab !== "security" && tab !== "settings" && <div className="pagination-actions"><button className="button secondary" disabled={page === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>Previous</button><span className="muted">Page {page + 1} of {pages}</span><button className="button secondary" disabled={page + 1 >= pages} onClick={() => setPage(value => value + 1)}>Next</button></div>}
    {reasonDialog && <div className="admin-modal-backdrop" role="presentation" onClick={() => !dialogBusy && setReasonDialog(null)}>
      <section className="admin-reason-modal panel" role="dialog" aria-modal="true" aria-labelledby="admin-reason-title" onClick={event => event.stopPropagation()}>
        <div className="admin-modal-symbol" aria-hidden="true">!</div><h2 id="admin-reason-title">{reasonDialog.title}</h2><p>{reasonDialog.description}</p>
        <label className="field">Reason / review note<textarea autoFocus rows={4} maxLength={1000} value={reasonInput} onChange={event => setReasonInput(event.target.value)} placeholder={reasonDialog.placeholder} /></label>
        {reasonDialog.required && <small className="admin-modal-hint">At least 5 characters are required. This will be stored in the audit trail.</small>}
        <div className="admin-modal-actions"><button className="button secondary" disabled={dialogBusy} onClick={() => setReasonDialog(null)}>Cancel</button><button className="button primary" disabled={dialogBusy || (reasonDialog.required && reasonInput.trim().length < 5)} onClick={() => void submitReason()}>{dialogBusy ? "Saving…" : reasonDialog.confirmLabel}</button></div>
      </section>
    </div>}
    {detail && <div className="admin-drawer-backdrop" role="presentation" onClick={() => setDetail(null)}><aside className="admin-drawer panel" role="dialog" aria-modal="true" aria-label="Account details" onClick={event => event.stopPropagation()}>
      <div className="admin-toolbar-actions"><h2>Account details</h2><button className="small-button" onClick={() => setDetail(null)}>Close</button></div>
      <p><strong>{detail.profile?.full_name ?? detail.email}</strong></p><p>{detail.email}</p><p>Role: {detail.role} · Status: {detail.status}</p><p>Created: {detail.created_at}</p>
      <h3>Recent activity</h3>{detail.recent_activity?.map((item: any, index: number) => <p key={index}>{item.event_type} · {item.created_at}<small>{item.details}</small></p>)}
      {detail.role !== "admin" && <div className="actions"><button className="button secondary" onClick={() => void moderate(detail, "suspended")}>Suspend</button><button className="button secondary" onClick={() => void moderate(detail, "active")}>Reactivate</button><button className="button secondary danger-text" onClick={() => void moderate(detail, "banned")}>Ban</button></div>}
    </aside></div>}
        </div>
      </div>
  </Layout>
}
