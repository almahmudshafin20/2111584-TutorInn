import { useEffect, useRef, useState, type ReactNode } from "react"
import { AppLayout as Layout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import {
  bulkDeleteAdminGroupTasks, bulkDeleteAdminTasks, bulkRemoveAdminRequests, bulkSetAdminUserStatus, deleteAdminGroup, removeAdminRequest, exportAdminCsv, getAdminActivity, getAdminGroups, getAdminGroupTasks, grantAdminRole, purgeAdminActivity, revokeAdminAccountSession, revokeAdminRole,
  getAdminDecisions, getAdminOverview, getAdminRequests, getAdminSecurity, getAdminTasks, getAdminTutors, getAdminUser, getAdminUsers,
  reviewAdminTutor, setAdminUserStatus, type AdminActivity, type AdminGroup, type AdminOverview, type AdminTask,
  type AdminTutor, type AdminUser, type AdminGroupTask, type AdminDecisions, type AdminDecisionActor,
} from "../api/admin"
import { accountPositionLabel } from "../components/accountPositions"

type Tab = "overview" | "students" | "tutors" | "admins" | "moderators" | "requests" | "tasks" | "groups" | "activity" | "security" | "decisions" | "subjects" | "settings"
const tabs: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" }, { id: "students", label: "Students" },
  { id: "tutors", label: "Tutors" }, { id: "admins", label: "Admins" }, { id: "moderators", label: "Moderators" }, { id: "requests", label: "Tutoring requests" },
  { id: "tasks", label: "Learning tasks" }, { id: "groups", label: "Learning groups" },
  { id: "activity", label: "Activity" }, { id: "security", label: "Security" }, { id: "decisions", label: "Decisions" }, { id: "subjects", label: "Subjects" }, { id: "settings", label: "Settings" },
]
const pageSize = 20
type ReasonDialog = { title: string; description: string; placeholder: string; confirmLabel: string; required: boolean; onSubmit: (reason: string) => Promise<void> }

export default function AdminReviewPage() {
  const { account, loading: authLoading } = useAuth()
  const params = new URLSearchParams(typeof window === "undefined" ? "" : window.location.search)
  const [tab, setTab] = useState<Tab>((tabs.some(item => item.id === params.get("tab")) ? params.get("tab") : "overview") as Tab)
  const [search, setSearch] = useState(params.get("q") ?? "")
  const [searchDraft, setSearchDraft] = useState(params.get("q") ?? "")
  const [overviewActivity, setOverviewActivity] = useState<AdminActivity[]>([])
  const loadSequence = useRef(0)
  const [status, setStatus] = useState(params.get("status") ?? "")
  const [createdFrom, setCreatedFrom] = useState(params.get("created_from") ?? "")
  const [createdTo, setCreatedTo] = useState(params.get("created_to") ?? "")
  const [ownerAccountId, setOwnerAccountId] = useState(params.get("owner_account_id") ?? "")
  const [postType, setPostType] = useState(params.get("post_type") ?? "")
  const [page, setPage] = useState(Math.max(0, Number(params.get("page") ?? 0) || 0))
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [tutors, setTutors] = useState<AdminTutor[]>([])
  const [decisions, setDecisions] = useState<AdminDecisions | null>(null)
  const [tasks, setTasks] = useState<AdminTask[]>([])
  const [groups, setGroups] = useState<AdminGroup[]>([])
  const [groupTasks, setGroupTasks] = useState<AdminGroupTask[]>([])
  const [selectedTasks, setSelectedTasks] = useState<number[]>([])
  const [selectedGroupTasks, setSelectedGroupTasks] = useState<number[]>([])
  const [selectedRequests, setSelectedRequests] = useState<number[]>([])
  const [liveActivity, setLiveActivity] = useState(false)
  const [rows, setRows] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [security, setSecurity] = useState<{ hours: number; min_events: number; incident_count: number; by_ip: { ip_address: string; count: number; last_seen: string; distinct_accounts: number; event_types: string[] }[]; registrations_by_ip: { ip_address: string; registrations: number; last_seen: string; distinct_accounts: number }[]; by_account: { account_id: number; email: string; status: string; count: number; last_seen: string; distinct_source_ips: number; event_types: string[] }[]; by_attempted_email: { email: string; count: number; last_seen: string }[]; events: AdminActivity[]; hostile_events: AdminActivity[]; total: number; offset: number; limit: number } | null>(null)
  const [securityHours, setSecurityHours] = useState(24)
  const [securityThreshold, setSecurityThreshold] = useState(3)
  const [selected, setSelected] = useState<number[]>([])
  const [detail, setDetail] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [reasonDialog, setReasonDialog] = useState<ReasonDialog | null>(null)
  const [reasonInput, setReasonInput] = useState("")
  const [dialogBusy, setDialogBusy] = useState(false)
  const [purgeBefore, setPurgeBefore] = useState("")

  useEffect(() => {
    const next = new URLSearchParams()
    next.set("tab", tab)
    if (search) next.set("q", search)
    if (status) next.set("status", status)
    if (createdFrom) next.set("created_from", createdFrom)
    if (createdTo) next.set("created_to", createdTo)
    if (ownerAccountId) next.set("owner_account_id", ownerAccountId)
    if (postType) next.set("post_type", postType)
    if (page) next.set("page", String(page))
    window.history.replaceState({}, "", window.location.pathname + "?" + next.toString())
  }, [tab, search, status, createdFrom, createdTo, ownerAccountId, postType, page])

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
      if (["students", "admins", "moderators"].includes(tab)) {
        const role = tab === "students" ? "student" : tab === "admins" ? "admin" : "moderator"
        const result = await getAdminUsers({ role, status, q: search, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize })
        if (sequence !== loadSequence.current) return
        setUsers(result.items); setTotal(result.total)
      }
      if (tab === "tutors") {
        const result = await getAdminTutors({ verification_status: status, q: search, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize })
        if (sequence !== loadSequence.current) return
        setTutors(result.items); setTotal(result.total)
      }
      if (tab === "requests") {
        const result = await getAdminRequests({ status, q: search, owner_account_id: ownerAccountId ? Number(ownerAccountId) : undefined, post_type: postType || undefined, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize })
        if (sequence !== loadSequence.current) return
        if (sequence !== loadSequence.current) return
        setRows(result.items); setTotal(result.total)
      }
      if (tab === "tasks") {
        const [result, groupTaskResult] = await Promise.all([
          getAdminTasks({ q: search, status, owner_account_id: ownerAccountId ? Number(ownerAccountId) : undefined, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize }),
          getAdminGroupTasks({ q: search, owner_account_id: ownerAccountId ? Number(ownerAccountId) : undefined, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize }),
        ])
        if (sequence !== loadSequence.current) return
        setTasks(result.items); setGroupTasks(groupTaskResult.items); setTotal(Math.max(result.total, groupTaskResult.total))
      }
      if (tab === "groups") {
        const result = await getAdminGroups({ q: search, owner_account_id: ownerAccountId ? Number(ownerAccountId) : undefined, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize })
        if (sequence !== loadSequence.current) return
        setGroups(result.items); setTotal(result.total)
      }
      if (tab === "activity") {
        const result = await getAdminActivity({ event_type: status, q: search, account_id: ownerAccountId ? Number(ownerAccountId) : undefined, created_from: createdFrom, created_to: createdTo, offset, limit: pageSize })
        setRows(result.items); setTotal(result.total)
      }
      if (tab === "decisions") { const result = await getAdminDecisions(); if (sequence !== loadSequence.current) return; setDecisions(result) }
      if (tab === "security") { const report = await getAdminSecurity(securityHours, securityThreshold, { event_type: status || undefined, q: search || undefined, account_id: ownerAccountId ? Number(ownerAccountId) : undefined, offset, limit: pageSize }); if (sequence !== loadSequence.current) return; setSecurity(report); setTotal(report.total) }
    } catch (cause) {
      if (sequence === loadSequence.current) setError(cause instanceof Error ? cause.message : "Could not load this Admin view.")
    } finally { if (sequence === loadSequence.current) setBusy(false) }
  }
  useEffect(() => { const timer = window.setTimeout(() => { setSearch(searchDraft); setPage(0) }, 280); return () => window.clearTimeout(timer) }, [searchDraft])
  useEffect(() => { void load(); return () => { loadSequence.current += 1 } }, [account?.id, account?.role, tab, search, status, createdFrom, createdTo, ownerAccountId, postType, page, securityHours, securityThreshold])
  useEffect(() => {
    if (tab !== "activity" || !liveActivity) return
    const interval = window.setInterval(() => { void load() }, 30000)
    return () => window.clearInterval(interval)
  }, [tab, liveActivity, account?.id, account?.role, search, status, page])

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
  async function changeAdminRole(target: AdminUser, grant: boolean) {
    askForReason({ title: grant ? "Grant Admin access" : "Revoke Admin access",
      description: grant ? `Grant Admin access to ${target.email}? Their existing Student/Tutor profile will be preserved.` : `Revoke Admin access from ${target.email}? Their original Student/Tutor account role will be restored.`,
      placeholder: "Reason for this privileged role change", confirmLabel: grant ? "Grant Admin access" : "Revoke Admin access", required: true,
      onSubmit: async reason => { if (grant) await grantAdminRole(target.id, reason); else await revokeAdminRole(target.id, reason); setNotice(`Admin access ${grant ? "granted to" : "revoked from"} ${target.email}.`); setDetail(await getAdminUser(target.id)); await load() } })
  }
  async function revokeAccountSession(target: AdminUser, sessionId: number) {
    if (!window.confirm("Revoke this active session? The user will need to sign in again on that device.")) return
    await revokeAdminAccountSession(target.id, sessionId)
    setNotice("The selected account session was revoked.")
    setDetail(await getAdminUser(target.id))
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
  function removeRequest(row: any) {
    askForReason({ title: "Remove tutoring request", description: `This permanently removes request #${row.id} and its interest responses. The action will be recorded in the Admin audit trail.`, placeholder: "Reason for removing this request", confirmLabel: "Remove request", required: true,
      onSubmit: async reason => { const result = await removeAdminRequest(row.id, reason); setNotice(`Request #${result.post_id} removed.`); setSelectedRequests(current => current.filter(id => id !== row.id)); await load() } })
  }
  async function removeSelectedRequests() {
    if (!selectedRequests.length || !window.confirm(`Permanently remove ${selectedRequests.length} selected tutoring requests?`)) return
    const ids = [...selectedRequests]
    askForReason({ title: "Remove selected tutoring requests", description: `This permanently removes ${ids.length} selected requests and their interest responses. The action will be recorded.`, placeholder: "Reason for removing these requests", confirmLabel: "Remove requests", required: true,
      onSubmit: async reason => { const result = await bulkRemoveAdminRequests(ids, reason); setNotice(`Request removal: ${result.succeeded} succeeded, ${result.failed} failed.`); setSelectedRequests([]); await load() } })
  }
  async function deleteSelectedGroupTasks() {
    if (!selectedGroupTasks.length || !window.confirm(`Permanently delete ${selectedGroupTasks.length} selected group tasks and their student assignments?`)) return
    const ids = [...selectedGroupTasks]
    askForReason({ title: "Delete selected group tasks", description: `This permanently deletes ${ids.length} selected group tasks and removes their assignments. Each deletion is recorded in the Admin audit trail.`, placeholder: "Reason for deleting these group tasks", confirmLabel: "Delete group tasks", required: true,
      onSubmit: async reason => { const result = await bulkDeleteAdminGroupTasks(ids, reason); setNotice(`Group-task deletion: ${result.succeeded} succeeded, ${result.failed} failed.`); setSelectedGroupTasks([]); await load() } })
  }
  async function removeGroup(group: AdminGroup) {
    const confirmed = window.confirm(`Delete “${group.name}”? This removes ${group.member_count} memberships, ${group.task_count} group tasks and their assignments.`)
    if (!confirmed) return
    askForReason({ title: `Delete learning group`, description: `“${group.name}” has ${group.member_count} members and ${group.task_count} tasks. Its assignments will also be deleted.`, placeholder: "Reason for deleting this group", confirmLabel: "Delete group", required: true,
      onSubmit: async reason => { const result = await deleteAdminGroup(group.id, reason); setNotice(`Group deleted. Removed ${result.members_removed} memberships, ${result.tasks_removed} tasks and ${result.assignments_removed} assignments.`); await load() } })
  }
  async function download(kind: "users" | "posts" | "tasks" | "activity") {
    try {
      const csv = await exportAdminCsv(kind, { q: search, status: kind === "activity" || kind === "posts" ? status : kind === "tasks" ? status : undefined, role: kind === "users" ? (tab === "tutors" ? "tutor" : tab === "students" ? "student" : undefined) : undefined, owner_account_id: kind === "tasks" && ownerAccountId ? Number(ownerAccountId) : undefined, account_id: (kind === "activity" || kind === "posts") && ownerAccountId ? Number(ownerAccountId) : undefined, created_from: createdFrom || undefined, created_to: createdTo || undefined })
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }))
      const link = document.createElement("a"); link.href = url; link.download = `tutorinn-${kind}.csv`; link.click()
      URL.revokeObjectURL(url)
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Export failed.") }
  }

  if (authLoading) return <Layout><section className="page-intro"><h1>Admin workspace</h1><p>Checking your account…</p></section></Layout>
  if (!account || account.role !== "admin") return <Layout><section className="page-intro"><p className="eyebrow">RESTRICTED AREA</p><h1>Admin access required</h1><p>Sign in with an authorized Admin account to manage TutorInn.</p><a className="button primary" href="/login">Sign in</a></section></Layout>

  const pages = Math.max(1, Math.ceil(total / pageSize))
  const metrics = overview ? [
    { label: "Total users", value: overview.total_accounts, icon: "●", caption: "All Student and Tutor accounts (Admins excluded)" },
    { label: "Students", value: overview.students, icon: "♙", caption: "Registered learner profiles" },
    { label: "Tutors", value: overview.tutors, icon: "✦", caption: "Registered tutor profiles" },
    { label: "Tutoring requests", value: overview.tutoring_requests, icon: "▤", caption: "Learning requests posted" },
    { label: "Learning groups", value: overview.groups, icon: "○", caption: "Groups created on the platform" },
    { label: "Main-resource records", value: overview.main_resource_records, icon: "◌", caption: "Records in the core platform tables" },
    { label: "New users (7 days)", value: overview.new_users_last_7_days, icon: "⌫", caption: "Accounts created in the last 7 days" },
    { label: "Active accounts", value: overview.active_accounts, icon: "✓", caption: "Accounts currently active" },
    { label: "Banned accounts", value: overview.banned_accounts, icon: "⊘", caption: "Accounts banned by moderation" },
    { label: "Suspended accounts", value: overview.suspended_accounts, icon: "⊘", caption: "Accounts temporarily suspended" },
    { label: "Deletion requests pending", value: overview.deletion_pending_accounts, icon: "◌", caption: "Account deletion requests awaiting review" },
    { label: "Pending tutor reviews", value: overview.pending_tutor_reviews, icon: "◌", caption: "Tutor profiles awaiting verification" },
    { label: "Open Student requests", value: overview.open_student_requests, icon: "▤", caption: "Student requests no Tutor has accepted yet" },
    { label: "Accepted Student requests", value: overview.accepted_student_requests, icon: "✓", caption: "Student requests with an accepted Tutor" },
    { label: "Active Students", value: overview.student_status.active, icon: "♙", caption: `Banned ${overview.student_status.banned} · Suspended ${overview.student_status.suspended}` },
    { label: "Complete Student profiles", value: overview.student_profiles_complete, icon: "✦", caption: `of ${overview.student_profiles_total} have a subject and education level` },
  ] : []
  return <Layout>
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-heading"><span className="admin-sidebar-mark">T</span><div><strong>TutorInn</strong><small>ADMIN WORKSPACE</small></div></div>
        <p className="admin-nav-label">WORKSPACE</p>
        <nav className="admin-tabs" aria-label="Admin sections">{tabs.map((item, index) =>
          <button key={item.id} aria-current={tab === item.id ? "page" : undefined} className={tab === item.id ? "admin-nav-item active" : "admin-nav-item"} onClick={() => { if (item.id === "subjects") { window.location.assign("/admin/subjects"); return } setTab(item.id); setPage(0); setStatus(""); setSelected([]); setDetail(null) }}>
            <span className="admin-nav-icon" aria-hidden="true">{["▦","♙","✦","♜","◉","▤","▣","☷","▧","◈","✓","◫","⚙"][index]}</span><span>{item.label}</span>{item.id === "tutors" && overview?.pending_tutor_reviews ? <em>{overview.pending_tutor_reviews}</em> : null}
          </button>
        )}</nav>
        <div className="admin-sidebar-note"><span className="admin-online-dot" /> Admin controls active <small>Actions are recorded in the audit trail.</small></div>
      </aside>
      <div className="admin-main">
        <header className="admin-page-heading">
          <div><p className="eyebrow">TUTORINN / ADMINISTRATION</p><h1>{tabs.find(item => item.id === tab)?.label ?? "Admin workspace"}</h1><p>Manage your tutoring platform, review activity and keep the community safe.</p></div>
          <div className="actions"><a className="button secondary" href="/admin/password-resets">Password reset requests</a><a className="button secondary" href="/admin/first-admin-transfer">First Admin transfer</a><a className="button secondary" href="/admin/reports">Reports</a><a className="button secondary" href="/admin/subjects">Subjects</a><button className="button secondary admin-refresh" onClick={() => void load()} disabled={busy}><span aria-hidden="true">↻</span> Refresh</button></div>
        </header>
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    {tab !== "overview" && tab !== "security" && tab !== "settings" && tab !== "decisions" && <section className="panel admin-toolbar">
      <label className="field">Search<input value={searchDraft} onChange={e => setSearchDraft(e.target.value)} placeholder="Search by name, email or subject" /></label>
      <label className="field">Created from<input type="date" value={createdFrom} max={createdTo || undefined} onChange={e => { setCreatedFrom(e.target.value); setPage(0) }} /></label>
      <label className="field">Created to<input type="date" value={createdTo} min={createdFrom || undefined} onChange={e => { setCreatedTo(e.target.value); setPage(0) }} /></label>
      {["requests", "tasks", "groups", "activity"].includes(tab) && <label className="field">Owner / account ID<input type="number" min="1" value={ownerAccountId} onChange={e => { setOwnerAccountId(e.target.value); setPage(0) }} placeholder="Any account" /></label>}
      {tab === "requests" && <label className="field">Request type<select value={postType} onChange={e => { setPostType(e.target.value); setPage(0) }}><option value="">All requests</option><option value="student">Student requests</option><option value="tutor">Tutor requests</option></select></label>}
      <label className="field">{["students", "admins", "moderators"].includes(tab) ? "Account status" : tab === "tutors" ? "Verification" : tab === "requests" ? "Request status" : tab === "tasks" ? "Task status" : tab === "groups" ? "Group search" : "Event type"}
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(0) }}>
          <option value="">All</option>
          {(["students", "admins", "moderators"].includes(tab) ? ["active", "banned", "suspended", "deletion_pending"] : tab === "tutors" ? ["pending", "approved", "rejected"] : tab === "requests" ? ["Pending", "Accepted", "Completed", "Rejected"] : tab === "tasks" ? ["open", "completed"] : []).map(value => <option key={value} value={value}>{value}</option>)}
        </select>
      </label>
      <button className="button secondary" onClick={() => { setSearch(""); setSearchDraft(""); setStatus(""); setCreatedFrom(""); setCreatedTo(""); setOwnerAccountId(""); setPostType(""); setPage(0) }}>Clear filters</button>
    </section>}
    {busy && <p className="muted">Loading…</p>}
    {tab === "overview" && <>
      <section className="admin-overview-intro"><div><span className="admin-overview-kicker">PLATFORM SNAPSHOT</span><h2>Your platform at a glance</h2><p>Live totals from TutorInn accounts and tutoring activity.</p></div><span className="admin-updated"><i /> Data from the platform database</span></section>
      <section className="admin-metrics">{metrics.map(metric =>
        <article className="panel admin-metric" key={metric.label}><span className="admin-metric-icon">{metric.icon}</span><span className="admin-metric-label">{metric.label}</span><strong>{Number(metric.value).toLocaleString()}</strong><small>{metric.caption}</small></article>)}</section>
      {overview?.trends && <section className="admin-trend-grid" aria-label="Seven day platform trends">{(["students","tutors","tutoring_requests"] as const).map(key => <article className="panel admin-trend-card" key={key}><span>{key === "students" ? "New Student registrations" : key === "tutors" ? "New Tutor registrations" : "Tutoring requests"}</span><strong>{overview.trends[key].last_7_days}</strong><small>Previous 7 days: {overview.trends[key].previous_7_days} · Change: {overview.trends[key].change > 0 ? "+" : ""}{overview.trends[key].change}</small></article>)}</section>}
      <section className="admin-overview-grid">
        <article className="panel admin-overview-panel"><div className="admin-panel-heading"><div><h2>Recent platform activity</h2><p>Latest recorded events across TutorInn</p></div><button className="small-button" onClick={() => setTab("activity")}>View activity →</button></div>
          {overviewActivity.length ? <div className="admin-recent-list">{overviewActivity.map(item => <div className="admin-recent-item" key={item.id}><span className="admin-event-dot" /><div><strong>{item.event_type.replaceAll("_"," ")}</strong><small>{item.target || [item.account_label, item.account_email].filter(Boolean).join(" · ") || "System event"}</small></div><time>{new Date(item.created_at).toLocaleString()}</time></div>)}</div> : <div className="admin-empty-inline">No platform activity has been recorded yet.</div>}
        </article>
        <article className="panel admin-overview-panel"><div className="admin-panel-heading"><div><h2>Admin shortcuts</h2><p>Jump directly to common tasks</p></div></div>
          <div className="admin-shortcuts"><button onClick={() => setTab("students")}><span>♙</span><div><strong>Manage students</strong><small>Review accounts and moderation status</small></div><b>→</b></button>
            <button onClick={() => setTab("tutors")}><span>✦</span><div><strong>Review tutors</strong><small>Approve or reject tutor qualifications</small></div><b>→</b></button>
            <button onClick={() => setTab("requests")}><span>▤</span><div><strong>View tutoring requests</strong><small>Monitor learning requests and status</small></div><b>→</b></button>
            <button onClick={() => setTab("security")}><span>◈</span><div><strong>Security monitoring</strong><small>Investigate suspicious activity</small></div><b>→</b></button>
            <button onClick={() => setTab("decisions")}><span>✓</span><div><strong>Decisions</strong><small>Approved, rejected, pending and suspended, with the admin who acted</small></div><b>→</b></button></div>
        </article>
      </section>
    </>}
    {(tab === "admins" || tab === "moderators") && <section className="panel">
      <div className="admin-toolbar-actions"><h2>{tab === "admins" ? "Admin accounts" : "Moderator accounts"} <span className="muted">({total})</span></h2></div>
      {users.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Position</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead><tbody>{users.map((user, index) =>
        <tr key={user.id}><td>{accountPositionLabel(`${user.role.charAt(0).toUpperCase()}${user.role.slice(1)}`, page, pageSize, index)}</td><td>{user.email}{user.is_first_admin ? " · First Admin" : ""}</td><td>{user.role}</td><td>{user.status}</td><td><button className="small-button" onClick={() => void inspectUser(user.id)}>Details</button></td></tr>)}</tbody></table></div> : <div className="empty-state">No {tab} accounts found.</div>}
    </section>}
    {tab === "students" && <section className="panel">
      <div className="admin-toolbar-actions"><h2>Student accounts <span className="muted">({total})</span></h2>
        <div className="actions"><button className="button secondary" onClick={() => void download("users")}>Export users CSV</button>
          <button className="button secondary" disabled={!selected.length} onClick={() => void bulkModerate("banned")}>Ban selected</button>
          <button className="button secondary" disabled={!selected.length} onClick={() => void bulkModerate("active")}>Unban selected</button></div></div>
      {users.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Select</th><th>Position</th><th>Student</th><th>Subjects</th><th>Education</th><th>Email</th><th>Status</th><th>Actions</th></tr></thead><tbody>{users.map((user, index) =>
        <tr key={user.id}><td><input type="checkbox" aria-label={`Select ${user.email}`} checked={selected.includes(user.id)} onChange={e => setSelected(current => e.target.checked ? [...current, user.id] : current.filter(id => id !== user.id))} /></td><td>{accountPositionLabel("Student", page, pageSize, index)}</td>
          <td>{user.profile?.full_name ?? "—"}</td><td>{user.profile?.subjects?.join(", ") || "—"}</td><td>{user.profile?.education_level || "—"}</td><td>{user.email}</td><td>{user.status}</td><td><button className="small-button" onClick={() => void inspectUser(user.id)}>Details</button>
            {user.status === "active" ? <button className="small-button danger-text" onClick={() => void moderate(user, "banned")}>Ban</button> : <button className="small-button" onClick={() => void moderate(user, "active")}>Unban / reactivate</button>}</td></tr>)}</tbody></table></div> : <div className="empty-state">No student accounts found.</div>}
    </section>}
    {tab === "tutors" && <section className="panel"><div className="admin-toolbar-actions"><h2>Tutor qualification review <span className="muted">({total})</span></h2><button className="button secondary" onClick={() => void download("users")}>Export users CSV</button></div>
      {tutors.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Position</th><th>Tutor</th><th>Subjects</th><th>Experience</th><th>Account</th><th>Verification</th><th>Review</th></tr></thead><tbody>{tutors.map((tutor, index) =>
        <tr key={tutor.id}><td>{accountPositionLabel("Tutor", page, pageSize, index)}</td><td><strong>{tutor.full_name}</strong><small>{tutor.email}</small></td><td>{tutor.subjects.join(", ")}</td><td>{tutor.experience_years} years</td><td>{tutor.account_status}</td><td>{tutor.verification_status}</td><td><div className="actions">{tutor.account_id && <button className="small-button danger-text" onClick={() => void moderate({ id: tutor.account_id!, email: tutor.email, role: "tutor", status: tutor.account_status, created_at: "", updated_at: "", profile: null }, tutor.account_status === "active" ? "suspended" : "active")}>{tutor.account_status === "active" ? "Suspend" : "Reactivate"}</button>}<button className="small-button" onClick={() => void verifyTutor(tutor, "approved")}>Approve</button><button className="small-button danger-text" onClick={() => void verifyTutor(tutor, "rejected")}>Reject</button><button className="small-button" onClick={() => void verifyTutor(tutor, "pending")}>Pending</button></div></td></tr>)}</tbody></table></div> : <div className="empty-state">No tutor profiles match these filters.</div>}
    </section>}
    {tab === "requests" && <section className="panel"><div className="admin-toolbar-actions"><h2>Tutoring requests <span className="muted">({total})</span></h2><div className="actions"><button className="button secondary" onClick={() => void download("posts")}>Export main records CSV</button><button className="button secondary danger-text" disabled={!selectedRequests.length} onClick={() => void removeSelectedRequests()}>Remove selected</button></div></div>
      {rows.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Select</th><th>ID</th><th>Type</th><th>Author</th><th>Subjects</th><th>Level</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><input type="checkbox" aria-label={`Select request ${row.id}`} checked={selectedRequests.includes(row.id)} onChange={e => setSelectedRequests(current => e.target.checked ? [...current, row.id] : current.filter(id => id !== row.id))} /></td><td>#{row.id}</td><td>{row.type}</td><td>{row.author}</td><td>{row.subjects.join(", ")}</td><td>{row.level}</td><td>{row.status}</td><td><button className="small-button danger-text" onClick={() => removeRequest(row)}>Remove</button></td></tr>)}</tbody></table></div> : <div className="empty-state">No tutoring requests found.</div>}
    </section>}
    {tab === "tasks" && <><section className="panel"><div className="admin-toolbar-actions"><h2>Personal learning tasks <span className="muted">({total})</span></h2><div className="actions"><button className="button secondary" onClick={() => void download("tasks")}>Export tasks & assignments CSV</button><button className="button secondary danger-text" disabled={!selectedTasks.length} onClick={() => void deleteSelectedTasks()}>Delete selected</button></div></div>{tasks.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Select</th><th>Task</th><th>Owner account</th><th>Due</th><th>Status</th></tr></thead><tbody>{tasks.map(task => <tr key={task.id}><td><input type="checkbox" aria-label={`Select task ${task.id}`} checked={selectedTasks.includes(task.id)} onChange={e => setSelectedTasks(current => e.target.checked ? [...current, task.id] : current.filter(id => id !== task.id))} /></td><td>{task.title}</td><td>{task.owner_account_id}</td><td>{task.due_date ?? "—"}</td><td>{task.completed ? "Completed" : "Open"}</td></tr>)}</tbody></table></div> : <div className="empty-state">No personal tasks found.</div>}</section>
      <section className="panel"><div className="admin-toolbar-actions"><h2>Group learning tasks and assignments</h2><div className="actions"><span className="muted">{groupTasks.length} on this page</span><button className="button secondary danger-text" disabled={!selectedGroupTasks.length} onClick={() => void deleteSelectedGroupTasks()}>Delete selected group tasks</button></div></div>{groupTasks.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Select</th><th>Task</th><th>Group</th><th>Assigned students</th><th>Due date</th><th>Status</th></tr></thead><tbody>{groupTasks.map(task => <tr key={task.id}><td><input type="checkbox" aria-label={`Select group task ${task.id}`} checked={selectedGroupTasks.includes(task.id)} onChange={e => setSelectedGroupTasks(current => e.target.checked ? [...current, task.id] : current.filter(id => id !== task.id))} /></td><td>{task.title}</td><td>{task.group_name}</td><td>{task.assigned_students.length ? task.assigned_students.map(student => <span key={student.account_id}>{student.email}{student.completed ? " ✓" : ""}<br /></span>) : "No students assigned"}</td><td>{task.due_date ?? "—"}</td><td>{task.status} ({task.completed_count}/{task.assignment_count})</td></tr>)}</tbody></table></div> : <div className="empty-state">No group tasks found.</div>}</section></>}
    {tab === "groups" && <section className="panel"><div className="admin-toolbar-actions"><h2>Learning groups <span className="muted">({total})</span></h2></div>{groups.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Group</th><th>Owner</th><th>Members</th><th>Tasks</th><th>Assignments</th><th>Created</th><th>Status</th><th>Action</th></tr></thead><tbody>{groups.map(group => <tr key={group.id}><td>{group.name}</td><td>{group.owner_email}</td><td>{group.member_count}</td><td>{group.task_count}</td><td>{group.assignment_count}</td><td>{new Date(group.created_at).toLocaleDateString()}</td><td>{group.status}</td><td><button className="small-button danger-text" onClick={() => void removeGroup(group)}>Delete group</button></td></tr>)}</tbody></table></div> : <div className="empty-state">No learning groups found.</div>}</section>}
    {tab === "decisions" && (decisions ? <DecisionsPanel data={decisions} onOpenTab={setTab} /> : <div className="empty-state">Loading decisions…</div>)}
    {tab === "activity" && <section className="panel"><div className="admin-toolbar-actions"><h2>Activity and audit trail <span className="muted">({total})</span></h2><div className="actions"><label className="admin-live-refresh"><input type="checkbox" checked={liveActivity} onChange={event => setLiveActivity(event.target.checked)} /> Auto-refresh every 30 seconds</label><button className="button secondary" onClick={() => void download("activity")}>Export activity CSV</button></div></div>
      {rows.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Event</th><th>Account</th><th>Target</th><th>IP</th><th>Time</th><th>Details</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td>{row.event_type}</td><td>{row.account_id ?? "—"}</td><td>{row.target || "—"}</td><td>{row.ip_address || "—"}</td><td>{row.created_at}</td><td>{row.details}</td></tr>)}</tbody></table></div> : <div className="empty-state">No activity records found.</div>}
    </section>}
    {tab === "security" && <section className="panel"><div className="admin-toolbar-actions"><div><h2>Security incidents</h2><p className="muted">Investigation signals for the selected time window</p></div><span>{security?.incident_count ?? 0} recent incidents</span></div>
      <div className="admin-security-filters"><label className="field">Time window<select value={securityHours} onChange={e => setSecurityHours(Number(e.target.value))}><option value={1}>Last hour</option><option value={24}>Last 24 hours</option><option value={72}>Last 3 days</option><option value={168}>Last 7 days</option><option value={720}>Last 30 days</option></select></label><label className="field">Minimum events<select value={securityThreshold} onChange={e => setSecurityThreshold(Number(e.target.value))}><option value={1}>1 or more</option><option value={3}>3 or more</option><option value={5}>5 or more</option><option value={10}>10 or more</option></select></label><label className="field">Event type<select value={status} onChange={e => { setStatus(e.target.value); setPage(0) }}><option value="">All security events</option>{["login_failed","login_locked","login_succeeded","registration_succeeded","auth_rate_limited","access_denied","access_token_rejected","refresh_token_rejected","refresh_token_reuse","refresh_token_expired","refresh_succeeded","session_revoked","password_changed","blocked_inactive_account","refresh_blocked_inactive_account","account_status_changed","bulk_account_status_changed","account_deletion_requested","admin_account_deletion_approved","admin_account_deletion_rejected","account_session_revoked","admin_role_granted","admin_role_revoked"].map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label></div>
      <p className="muted">Search the page for an email, account ID, IP address, event type or browser string. IP addresses are investigation signals, not proof of identity; never ban every account sharing an address.</p>
      <div className="admin-security-summaries"><div><h3>Repeated source IPs</h3>{security?.by_ip.length ? security.by_ip.map(item => <p key={item.ip_address}>{item.ip_address}: {item.count} failures · {item.distinct_accounts} distinct accounts · {item.event_types.join(", ")} · last seen {item.last_seen}</p>) : <p>No IP reached this threshold.</p>}</div><div><h3>Account registrations by source IP</h3>{security?.registrations_by_ip.length ? security.registrations_by_ip.map(item => <p key={item.ip_address}>{item.ip_address}: {item.registrations} registrations · {item.distinct_accounts} distinct accounts (including anonymized deleted accounts) · last seen {item.last_seen}</p>) : <p>No registrations in this period.</p>}</div><div><h3>Accounts with incidents</h3>{security?.by_account.length ? security.by_account.map(item => <p key={item.account_id}><button className="small-button" onClick={() => void inspectUser(item.account_id)}>Account {item.account_id} · {item.email}</button> · {item.status} · {item.count} failures · {item.distinct_source_ips} source IPs · {item.event_types.join(", ")} · last seen {item.last_seen}</p>) : <p>No known account reached this threshold.</p>}</div><div><h3>Unattributed attempts</h3>{security?.by_attempted_email.length ? security.by_attempted_email.map(item => <p key={item.email}>{item.email}: {item.count} events · last seen {item.last_seen}</p>) : <p>No repeated attempted identifiers.</p>}</div></div>
      <h3>50 newest hostile events</h3><p className="muted">Recent failed authentication, rejected-token, access-denied and lockout signals. These are indicators for review, not proof of a person’s identity.</p>{security?.hostile_events.map(event => <article className="profile-card" key={`hostile-${event.id}`}><div className="profile-info"><strong>{event.event_type}</strong><p>Attempted account: {event.target || "not supplied"} · Account ID: {event.account_id ?? "unknown"} · IP: {event.ip_address || "unavailable"} · {event.created_at}</p>{event.user_agent && <small>Browser/device: {event.user_agent}</small>}{event.details && <small>Context: {event.details}</small>}{event.account_id !== null && <button className="small-button" onClick={() => void inspectUser(event.account_id!)}>Inspect account</button>}</div></article>)}
      <h3>Filtered security event history</h3>{security?.events.map(event => <article className="profile-card" key={event.id}><div className="profile-info"><strong>{event.event_type}</strong><p>Attempted account: {event.target || "not supplied"} · Account ID: {event.account_id ?? "unknown"} · IP: {event.ip_address || "unavailable"} · {event.created_at}</p>{event.user_agent && <small>Browser/device: {event.user_agent}</small>}{event.details && <small>Context: {event.details}</small>}<div className="actions">{event.account_id !== null && <button className="small-button" onClick={() => void inspectUser(event.account_id!)}>Inspect account</button>}<button className="small-button" onClick={() => { setSearch(event.ip_address || event.target || event.event_type); setSearchDraft(event.ip_address || event.target || event.event_type); setStatus(""); setPage(0); setTab("activity") }}>View related activity</button></div></div></article>)}
      <button className="button secondary" onClick={() => void download("activity")}>Export activity CSV</button>
      <div className="pagination-actions"><button className="button secondary" disabled={page === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>Previous</button><span className="muted">Page {page + 1} of {pages} · {security?.total ?? 0} events</span><button className="button secondary" disabled={page + 1 >= pages} onClick={() => setPage(value => value + 1)}>Next</button></div>
    </section>}
    {tab === "settings" && <section className="panel admin-settings-panel">
      <div className="admin-panel-heading"><div><h2>Administration settings</h2><p>Safe platform controls and retention operations</p></div></div>
      <div className="admin-settings-note"><strong>Account deletion requests</strong><p>Review Student and Tutor requests and approve or reject permanent account deletion.</p><a className="button secondary" href="/admin/deletions">Open deletion requests</a></div>
      <div className="admin-settings-note"><strong>Environment and secrets</strong><p>Platform secrets and deployment configuration are intentionally not exposed in the Admin dashboard. Manage secrets through the hosting provider's protected environment settings.</p></div>
      <div className="admin-settings-note admin-retention-control"><strong>Activity retention cleanup</strong><p>Remove only successful-login activity older than 90 days. Security incidents, moderation history and Admin audit records are always preserved.</p>
        <label className="field">Remove successful-login events before<input type="datetime-local" value={purgeBefore} onChange={event => setPurgeBefore(event.target.value)} /></label>
        <button className="button secondary" disabled={!purgeBefore} onClick={() => {
          const before = new Date(purgeBefore)
          if (!Number.isFinite(before.getTime())) { setError("Choose a valid retention cutoff."); return }
          askForReason({ title: "Clean up old login activity", description: `Only successful-login and expired rate-limit counter events before ${before.toLocaleString()} will be removed. This cutoff must meet the configured retention age. Security incidents, moderation and Admin audit events are preserved.`, placeholder: "Reason for this retention cleanup", confirmLabel: "Confirm cleanup", required: true,
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
      <h3>Account records</h3><p>Tutoring posts: {detail.records?.tutoring_posts?.length ?? 0} · Personal tasks: {detail.records?.personal_tasks ?? 0}</p>
      {detail.records?.tutoring_posts?.map((post: any) => <p key={post.id}>Post #{post.id} · {post.subject} · {post.status}</p>)}
      <h3>Learning groups</h3>{[...(detail.records?.owned_groups ?? []).map((group: any) => ({ ...group, relation: "Owner" })), ...(detail.records?.group_memberships ?? []).map((group: any) => ({ ...group, relation: "Member" }))].map((group: any) => <p key={`${group.relation}-${group.id}`}>{group.name} · {group.relation}</p>)}
      <h3>Active sessions and devices</h3>{detail.active_sessions?.length ? detail.active_sessions.map((session: any) => <article className="profile-card" key={session.id}><div className="profile-info"><strong>{session.user_agent || "Unknown device"}</strong><p>IP: {session.ip_address || "Unavailable"}</p><small>Last active: {session.last_used_at} · Expires: {session.expires_at}</small></div><button className="small-button danger-text" disabled={detail.id === account?.id} onClick={() => void revokeAccountSession(detail, session.id)}>Revoke session</button></article>) : <p className="muted">No active sessions.</p>}
      <h3>Recent activity</h3>{detail.recent_activity?.map((item: any, index: number) => <p key={index}>{item.event_type} · {item.created_at}<small>{item.details}</small></p>)}
      {detail.status === "deletion_pending" && <p className="muted">This account has a pending deletion request. Review it in <a href="/admin/deletions">Account deletion requests</a>; generic status changes are blocked.</p>}{detail.role !== "admin" && detail.status !== "deletion_pending" && <div className="actions"><button className="button secondary" onClick={() => void moderate(detail, "suspended")}>Suspend</button><button className="button secondary" onClick={() => void moderate(detail, "active")}>{detail.status === "banned" ? "Unban" : "Reactivate"}</button><button className="button secondary danger-text" onClick={() => void moderate(detail, "banned")}>Ban</button><button className="button secondary" onClick={() => void changeAdminRole(detail, true)}>Grant Admin access</button></div>}
      {detail.role === "admin" && detail.id !== account?.id && <button className="button secondary danger-text" onClick={() => void changeAdminRole(detail, false)}>Revoke Admin access</button>}
    </aside></div>}
        </div>
      </div>
  </Layout>
}


function DecisionsPanel({ data, onOpenTab }: { data: AdminDecisions; onOpenTab: (tab: Tab) => void }) {
  const tutorsWith = (status: string) => data.tutors.filter(item => item.status === status)
  const studentActions = data.account_actions.filter(item => item.target_role === "student")
  const otherActions = data.account_actions.filter(item => item.target_role !== "student")
  const who = (actor: AdminDecisionActor) => actor.label ? `${actor.label}${actor.email ? ` (${actor.email})` : ""}` : "Admin not recorded"
  const when = (value: string | null) => value ? new Date(value).toLocaleString() : "—"
  const accountName = (target: string) => target.includes(":") ? target.split(":").slice(1).join(":") : `Account #${target}`
  const Group = ({ title, count, emptyText, children }: { title: string; count: number; emptyText: string; children: ReactNode }) => (
    <section className="panel decision-group" aria-label={title}>
      <h2>{title} <span className="muted">({count})</span></h2>
      {count === 0 ? <div className="empty-state">{emptyText}</div> : <div className="admin-recent-list">{children}</div>}
    </section>
  )
  const Row = ({ name, detail, by, note, time }: { name: string; detail?: string; by: string; note?: string; time: string | null }) => (
    <div className="admin-recent-item"><span className="admin-event-dot" /><div><strong>{name}</strong>{detail && <small>{detail}</small>}<small>By {by}{note ? ` · ${note}` : ""}</small></div><time>{when(time)}</time></div>
  )
  return (
    <div className="decisions-view">
      <section className="panel"><h2>Decisions</h2><p className="muted">Who approved, rejected, left pending, suspended or banned each student and tutor, with the admin’s label and email. Actions themselves stay on their own pages.</p></section>

      <Group title="Tutors approved" count={tutorsWith("approved").length} emptyText="No tutor has been approved yet.">
        {tutorsWith("approved").map(item => <Row key={`a-${item.tutor_id}`} name={item.full_name} detail={item.email} by={who(item.actor)} note={item.review_note} time={item.reviewed_at} />)}
      </Group>
      <Group title="Tutors rejected" count={tutorsWith("rejected").length} emptyText="No tutor has been rejected.">
        {tutorsWith("rejected").map(item => <Row key={`r-${item.tutor_id}`} name={item.full_name} detail={item.email} by={who(item.actor)} note={item.review_note} time={item.reviewed_at} />)}
      </Group>
      <Group title="Tutors pending" count={tutorsWith("pending").length} emptyText="No tutor is waiting for review.">
        {tutorsWith("pending").map(item => <Row key={`p-${item.tutor_id}`} name={item.full_name} detail={item.email} by={item.actor.label ? who(item.actor) : "nobody yet"} time={item.reviewed_at} />)}
      </Group>

      <Group title="Student request responses" count={data.interest_decisions.length} emptyText="No Student request response has been approved or rejected since this log started.">
        {data.interest_decisions.map(item => <Row key={`i-${item.id}`} name={`Response on request #${item.target} — ${item.status}`} by={who(item.actor)} note={item.note} time={item.created_at} />)}
      </Group>

      <Group title="Student accounts (suspended, banned, reactivated)" count={studentActions.length} emptyText="No student account has been suspended, banned or reactivated.">
        {studentActions.map(item => <Row key={`s-${item.id}`} name={accountName(item.target)} detail={`${item.previous_status ? `${item.previous_status} → ` : ""}${item.status}`} by={who(item.actor)} note={item.note} time={item.created_at} />)}
      </Group>
      <Group title="Tutor and other accounts (suspended, banned, reactivated)" count={otherActions.length} emptyText="No tutor or other account has been suspended, banned or reactivated.">
        {otherActions.map(item => <Row key={`o-${item.id}`} name={accountName(item.target)} detail={`${item.previous_status ? `${item.previous_status} → ` : ""}${item.status}`} by={who(item.actor)} note={item.note} time={item.created_at} />)}
      </Group>

      <section className="panel decision-group" aria-label="Actions on other pages">
        <h2>Take action on other pages</h2>
        <div className="admin-shortcuts">
          <button onClick={() => onOpenTab("requests")}><span>▤</span><div><strong>Student request responses</strong><small>Approve or reject Tutor interest</small></div><b>→</b></button>
          <button onClick={() => onOpenTab("students")}><span>♙</span><div><strong>Students</strong><small>Suspend, ban or reactivate students</small></div><b>→</b></button>
          <button onClick={() => window.location.assign("/admin/deletions")}><span>◌</span><div><strong>Account deletion requests</strong><small>Two-step review with former-user links</small></div><b>→</b></button>
          <button onClick={() => window.location.assign("/admin/subjects")}><span>☷</span><div><strong>Subjects</strong><small>Activate or deactivate subjects</small></div><b>→</b></button>
        </div>
      </section>
    </div>
  )
}
