import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import { getAdminDeletionRequests, issueAdminFormerUserLink, reviewAdminDeletionRequest, type AdminDeletionRequest } from "../api/admin"

export default function AdminDeletionRequestsPage() {
  const { account, loading: authLoading } = useAuth()
  const [items, setItems] = useState<AdminDeletionRequest[]>([])
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false)
  const [error, setError] = useState(""), [notice, setNotice] = useState("")
  async function load() { setLoading(true); setError(""); try { const result = await getAdminDeletionRequests("all"); setItems(result.items) } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load deletion requests.") } finally { setLoading(false) } }
  useEffect(() => { if (account?.role === "admin") void load(); else setLoading(false) }, [account])
  async function review(item: AdminDeletionRequest, status: "approved" | "rejected") {
    let choices: Parameters<typeof reviewAdminDeletionRequest>[3] = undefined
    if (status === "approved") {
      const requestedAction = item.requested_content_action === "delete_all" ? "3"
        : item.requested_content_action === "delete_selected" ? "2" : "1"
      const action = window.prompt(
        "Choose the Admin's final content action for " + item.account_email + ":\n" +
        "1 = Delete account only; retain all eligible content\n" +
        "2 = Delete selected content; retain the rest\n" +
        "3 = Delete account and all eligible content",
        requestedAction,
      )
      if (action === null) return
      if (!["1", "2", "3"].includes(action.trim())) { setError("Enter 1, 2 or 3 for the final content action."); return }
      const content_action = action.trim() === "1" ? "account_only" : action.trim() === "2" ? "delete_selected" : "delete_all"
      let selected_content: { content_type: "learning_post" | "personal_task" | "learning_group" | "group_task" | "group_assignment"; content_id: number }[] | undefined
      if (content_action === "delete_selected") {
        const available = item.available_content ?? []
        const defaultSelection = item.requested_content_ids.map(row => row.content_type + ":" + row.content_id).join(",")
        const raw = window.prompt(
          "Enter content to delete as type:id, separated by commas. Available: " +
          available.map(row => row.content_type + ":" + row.content_id).join(", "),
          defaultSelection,
        )
        if (raw === null) return
        const allowed = new Set(available.map(row => row.content_type + ":" + row.content_id))
        const allowedTypes = new Set<string>(["learning_post", "personal_task", "learning_group", "group_task", "group_assignment"])
        const rawItems = raw.split(",").map(value => value.trim()).filter(Boolean)
        const parsed: { content_type: "learning_post" | "personal_task" | "learning_group" | "group_task" | "group_assignment"; content_id: number }[] = []
        let invalidSelection = rawItems.length === 0
        for (const value of rawItems) {
          const [content_type, idText] = value.split(":")
          const content_id = Number(idText)
          if (!content_type || !allowedTypes.has(content_type) ||
              !Number.isInteger(content_id) || content_id <= 0 || !allowed.has(content_type + ":" + content_id)) {
            invalidSelection = true
          } else {
            parsed.push({ content_type: content_type as "learning_post" | "personal_task" | "learning_group" | "group_task" | "group_assignment", content_id })
          }
        }
        if (invalidSelection) {
          setError("The selected content list is empty or contains an item that is not owned by this account.")
          return
        }
        selected_content = parsed
      }
      const visibilityChoice = window.prompt("Retained content visibility: 1 = visible, 2 = hidden.", item.requested_visibility === "hidden" ? "2" : "1")
      if (visibilityChoice === null) return
      if (visibilityChoice !== "1" && visibilityChoice !== "2") { setError("Enter 1 for visible or 2 for hidden."); return }
      const anonymizeChoice = window.prompt("Anonymize author identity on retained content? Enter y or n.", item.requested_anonymize_content ? "y" : "n")
      if (anonymizeChoice === null) return
      if (!["y", "n"].includes(anonymizeChoice.trim().toLowerCase())) { setError("Enter y or n for anonymization."); return }
      choices = {
        content_action,
        selected_content,
        visibility: visibilityChoice === "2" ? "hidden" : "visible",
        anonymize_content: anonymizeChoice.trim().toLowerCase() === "y",
      }
    }
    const actionText = status === "approved"
      ? "approve using the Admin-selected account and content settings"
      : "reject the request and reactivate the account"
    if (!window.confirm("Confirm: " + actionText + "? The final choices will be recorded in the deletion receipt.")) return
    const note = window.prompt("Optional Admin review note (up to 1000 characters):", "")
    if (note === null) return
    setBusy(true); setError(""); setNotice("")
    try {
      const result = await reviewAdminDeletionRequest(item.id, status, note, choices)
      setNotice(status === "approved"
        ? "Account deletion approved with final content action: " + (result.final_content_action ?? "recorded") +
          ". " + (result.notification_status === "sent" ? "An outcome email was sent." : "Outcome email was not sent (" + (result.notification_status ?? "unknown") + "); configure SMTP and follow up.")
        : "Request rejected; account reactivated.")
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not review this request.")
    } finally { setBusy(false) }
  }
  async function issueFreshLink(item: AdminDeletionRequest) {
    if (!window.confirm("Issue a fresh 48-hour verification link to " + (item.former_user_email || "the former user") + "? Any older unused link will stop working.")) return
    setBusy(true); setError(""); setNotice("")
    try {
      const result = await issueAdminFormerUserLink(item.id)
      setNotice("Former-user verification link status: " + result.former_user_link_status + ".")
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not issue a fresh verification link.")
    } finally { setBusy(false) }
  }
  if (authLoading) return <AppLayout><p className="muted">Checking your session…</p></AppLayout>
  if (!account) return <AppLayout><section className="empty-state auth-required"><h1>Sign in required</h1><a className="button primary" href="/login">Sign in</a></section></AppLayout>
  if (account.role !== "admin") return <AppLayout><section className="empty-state auth-required"><h1>Admin access required</h1><p>This page is available only to Admin accounts.</p><a className="button primary" href="/dashboard">Back to workspace</a></section></AppLayout>
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">ADMINISTRATION</p><h1>Account deletion requests</h1><p>Review requests from Students and Tutors. Choose the final content scope, visibility and anonymization independently; the final decision may differ from the user preference.</p><div className="actions"><a className="button secondary" href="/admin">Back to Admin dashboard</a><a className="button secondary" href="/admin/former-user-content">Former-user content requests</a><button className="button secondary" onClick={() => void load()}>Refresh</button></div></section>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel dashboard-panel"><div className="panel-heading"><div><h2>Deletion request history</h2><p className="muted">{items.length} request(s) loaded</p></div></div>
      {loading ? <p className="muted">Loading requests…</p> : items.length === 0 ? <p className="muted">There are no pending account deletion requests.</p> : <div className="profile-list">{items.map(item => <article className="profile-card" key={item.id}><div className="profile-info"><h3>{item.former_user_email || item.account_email}</h3><p>Status: <strong>{item.status}</strong></p><p>Role: {item.account_role} · Requested: {new Date(item.requested_at).toLocaleString()}</p><p>Requested content action: <strong>{item.requested_content_action}</strong></p><p>Requested retained-content visibility: <strong>{item.requested_visibility}</strong> · Anonymize: <strong>{item.requested_anonymize_content ? "Yes" : "No"}</strong></p><p>Requested selected items: {item.requested_content_ids.map(row => row.content_type + " #" + row.content_id).join(", ") || "None"}</p><p>Request reason: {item.reason || "No reason supplied."}</p><p className="muted">Outcome email: {item.notification_status}</p><p className="muted">Former-user link: {item.former_user_link_status} · Retained items: {item.retained_content_count}</p><p className="muted">Request #{item.id}</p></div><div className="actions">{item.status === "pending" ? <><button className="button secondary" disabled={busy} onClick={() => void review(item, "rejected")}>Reject and reactivate</button><button className="button secondary danger-text" disabled={busy} onClick={() => void review(item, "approved")}>Approve and choose method</button></> : item.status === "approved" && item.retained_content_count > 0 ? <button className="button secondary" disabled={busy} onClick={() => void issueFreshLink(item)}>Issue fresh verification link</button> : null}</div></article>)}</div>}
    </section>
  </AppLayout>
}
