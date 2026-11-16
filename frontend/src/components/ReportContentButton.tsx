import { useState } from "react"
import { useAuth } from "../context/AuthContext"
import { submitContentReport, type ReportTarget } from "../api/moderation"

export function ReportContentButton({ targetType, targetId }: { targetType: ReportTarget; targetId: number }) {
  const { account } = useAuth()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState("inappropriate")
  const [description, setDescription] = useState("")
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState("")
  if (!account || !["student", "tutor"].includes(account.role)) return null
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true); setMessage("")
    try {
      await submitContentReport(targetType, targetId, reason, description.trim())
      setMessage("Report submitted. Our Admin team will review it.")
      setOpen(false); setDescription("")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not submit report.")
    } finally { setBusy(false) }
  }
  return <div className="report-content-control">
    {!open ? <button type="button" className="small-button danger-text" onClick={() => setOpen(true)}>Report {targetType === "profile" ? "profile" : "content"}</button> :
      <form className="panel" onSubmit={submit}>
        <h3>Report this {targetType === "profile" ? "profile" : "listing"}</h3>
        <label className="field">Reason<select value={reason} onChange={event => setReason(event.target.value)}>
          <option value="inappropriate">Inappropriate content</option><option value="harassment">Harassment or abuse</option>
          <option value="spam">Spam or scam</option><option value="misleading">Misleading information</option>
          <option value="impersonation">Impersonation</option><option value="other">Other</option>
        </select></label>
        <label className="field">Additional details (optional)<textarea rows={3} maxLength={2000} value={description} onChange={event => setDescription(event.target.value)} placeholder="Describe the issue…" /></label>
        <div className="actions"><button className="button primary" disabled={busy}>{busy ? "Submitting…" : "Submit report"}</button><button type="button" className="button secondary" disabled={busy} onClick={() => setOpen(false)}>Cancel</button></div>
      </form>}
    {message && <p className="muted" role="status">{message}</p>}
  </div>
}
