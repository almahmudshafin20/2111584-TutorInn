import { useCallback, useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { listPasswordResetRequests, resendPasswordResetEmail, reviewPasswordResetRequest } from "../api/admin"
import type { PasswordResetRequest } from "../types/auth"

export default function PasswordResetRequestsPage() {
  const [requests, setRequests] = useState<PasswordResetRequest[]>([])
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      setRequests(await listPasswordResetRequests())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load password reset requests.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function review(id: number, decision: "approve" | "reject") {
    setBusyId(id)
    setError("")
    setNotice("")
    try {
      const result = await reviewPasswordResetRequest(id, decision)
      setNotice(decision === "approve"
        ? `Request approved. Email delivery status: ${result.delivery_status}.`
        : "Password reset request rejected.")
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not review this request.")
    } finally {
      setBusyId(null)
    }
  }

  async function resend(id: number) {
    setBusyId(id)
    setError("")
    setNotice("")
    try {
      const result = await resendPasswordResetEmail(id)
      setNotice(`A fresh reset link was generated. Email delivery status: ${result.delivery_status}.`)
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not resend the reset email.")
    } finally {
      setBusyId(null)
    }
  }

  return <AppLayout><section>
    <header className="page-intro compact">
      <p className="eyebrow">ACCOUNT SECURITY</p>
      <h1>Password reset requests</h1>
      <p>Review requests from Students and Tutors. Reset tokens and passwords are never shown to reviewers.</p>
    </header>
    {notice && <p role="status" className="success-message">{notice}</p>}
    {error && <p role="alert" className="error-message">{error}</p>}
    {loading ? <p role="status" className="muted">Loading requests…</p> : requests.length === 0
      ? <section className="empty-state"><h2>No pending requests</h2><p>New requests will appear here for authorized review.</p></section>
      : <div className="request-list">{requests.map(item => <article className="request-card" key={item.id}>
        <div><h2>{item.email}</h2><p>Requested {new Date(item.requested_at).toLocaleString()}</p><p>Status: {item.status} · Delivery: {item.delivery_status}</p></div>
        <div className="request-actions">
          {item.status === "pending" && <>
            <button className="button primary" type="button" disabled={busyId === item.id} onClick={() => void review(item.id, "approve")}>Approve</button>
            <button className="button secondary" type="button" disabled={busyId === item.id} onClick={() => void review(item.id, "reject")}>Reject</button>
          </>}
          {item.status === "approved" && item.delivery_status !== "sent" && <button className="button secondary" type="button" disabled={busyId === item.id} onClick={() => void resend(item.id)}>Resend link</button>}
        </div>
      </article>)}</div>}
  </section></AppLayout>
}
