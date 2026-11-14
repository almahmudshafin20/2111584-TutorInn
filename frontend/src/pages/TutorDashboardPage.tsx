import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import type { TutorDashboard } from "../types/auth"
import { loadDashboard, respondToRequest } from "../services/dashboard"

function statusKey(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-")
}

export default function TutorDashboardPage() {
  const { account } = useAuth()
  const [data, setData] = useState<TutorDashboard | null>(null)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    setError("")
    try {
      const result = await loadDashboard()
      if (result.role !== "tutor") throw new Error("This dashboard is only available to Tutor accounts.")
      setData(result)
    } catch (reason) {
      setData(null)
      setError(reason instanceof Error ? reason.message : "Could not load your dashboard.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  async function respond(id: number, response: "Interested" | "Not Interested") {
    setBusy(true)
    setError("")
    setNotice("")
    try {
      await respondToRequest(id, response)
      setNotice(response === "Interested" ? "Your interest was sent to the Student." : "You marked this request as not interested.")
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send your response.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppLayout>
      <section className="page-intro compact dashboard-intro">
        <p className="eyebrow">TUTOR WORKSPACE</p>
        <h1>Welcome, {data?.profile.full_name ?? account?.email}</h1>
        <p>Review Student tutoring requests and manage your responses.</p>
      </section>

      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status" aria-live="polite">{notice}</div>}

      {loading ? (
        <div className="dashboard-loading" role="status" aria-live="polite">Loading your dashboard…</div>
      ) : data ? (
        <>
          <section className="dashboard-stats" aria-label="Tutor dashboard summary">
            <article><strong>{data.requests.length}</strong><span>Open Student requests</span></article>
            <article><strong>{data.responses.length}</strong><span>Your responses</span></article>
            <article><strong>{data.profile.experience_years}</strong><span>Years experience</span></article>
          </section>

          <section id="requests" className="panel dashboard-panel">
            <div className="panel-heading"><div><h2>Student tutoring requests</h2><p>Explore open learning needs and respond when there is a good match.</p></div></div>
            {data.requests.length === 0 ? (
              <div className="empty-state"><h3>No open requests right now</h3><p>New Student requests will appear here when they are published.</p></div>
            ) : (
              <div className="profile-list">
                {data.requests.map(request => {
                  const response = data.responses.find(item => item.post_id === request.id)
                  return (
                    <article className="profile-card dashboard-record" key={request.id}>
                      <div className="profile-info">
                        <div className="dashboard-card-top">
                          <p className="eyebrow">STUDENT REQUEST #{request.id}</p>
                          <span className={`status-pill status-${statusKey(request.status)}`}>{request.status}</span>
                        </div>
                        <h3>{request.level}</h3>
                        <div className="tag-list">{request.subjects.map(subject => <span key={subject}>{subject}</span>)}</div>
                        <p>{request.experience || "No additional requirements provided."}</p>
                        <p className="muted">{request.availability || "Flexible"} · {request.location || "Location not specified"} · Budget ৳{request.fee}</p>
                        {response && (
                          <div className="response-summary">
                            <span>Your response</span>
                            <strong>{response.response}</strong>
                            <span className={`status-pill status-${statusKey(response.review_status)}`}>{response.review_status}</span>
                          </div>
                        )}
                        <div className="card-actions response-actions">
                          <button className="button primary" aria-pressed={response?.response === "Interested"} disabled={busy || response?.response === "Interested"} onClick={() => void respond(request.id, "Interested")}>
                            {response?.response === "Interested" ? "Interested" : "I'm interested"}
                          </button>
                          <button className="button secondary" aria-pressed={response?.response === "Not Interested"} disabled={busy || response?.response === "Not Interested"} onClick={() => void respond(request.id, "Not Interested")}>
                            {response?.response === "Not Interested" ? "Not interested" : "Not interested"}
                          </button>
                        </div>
                      </div>
                    </article>
                  )
                })}
              </div>
            )}
          </section>

          <section className="panel dashboard-panel">
            <div className="panel-heading"><div><h2>My responses</h2><p>Track the responses you have sent to Students.</p></div></div>
            {data.responses.length === 0 ? (
              <div className="empty-state"><h3>No responses sent</h3><p>When you respond to a Student request, it will be listed here.</p></div>
            ) : (
              <div className="profile-list">
                {data.responses.map(item => (
                  <article className="profile-card dashboard-record" key={item.id}>
                    <div className="profile-info">
                      <div className="dashboard-card-top">
                        <h3>Request #{item.post_id}</h3>
                        <span className={`status-pill status-${statusKey(item.review_status)}`}>{item.review_status}</span>
                      </div>
                      <p>Your response: {item.response}</p>
                      <p className="muted">Updated {new Date(item.updated_at).toLocaleDateString()}</p>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </AppLayout>
  )
}
