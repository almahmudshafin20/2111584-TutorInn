
import { useEffect, useState } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import type { TutorDashboard } from "../types/auth"
import { loadDashboard, respondToRequest } from "../services/dashboard"
export default function TutorDashboardPage() {
  const { account } = useAuth()
  const [data, setData] = useState<TutorDashboard | null>(null)
  const [error, setError] = useState(""), [notice, setNotice] = useState(""), [busy, setBusy] = useState(false), [loading, setLoading] = useState(true)
  async function load() { setLoading(true); setError(""); try { const result = await loadDashboard(); if (result.role !== "tutor") throw new Error("This dashboard is only available to Tutor accounts."); setData(result) } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load your dashboard.") } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  async function respond(id: number, response: "Interested" | "Not Interested") { setBusy(true); setError(""); setNotice(""); try { await respondToRequest(id, response); setNotice(response === "Interested" ? "Your interest was sent to the Student." : "You marked this request as not interested."); await load() } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not send your response.") } finally { setBusy(false) } }
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">TUTOR WORKSPACE</p><h1>Welcome, {data?.profile.full_name ?? account?.email}</h1><p>Review Student tutoring requests and manage your responses.</p></section>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    {loading ? <p className="muted">Loading your dashboard…</p> : data && <>
      <section className="dashboard-stats"><article><strong>{data.requests.length}</strong><span>Open Student requests</span></article><article><strong>{data.responses.length}</strong><span>Your responses</span></article><article><strong>{data.profile.experience_years}</strong><span>Years experience</span></article></section>
      <section className="panel dashboard-panel"><h2>Student tutoring requests</h2>{data.requests.length === 0 ? <div className="empty-state"><h3>No open requests right now</h3><p>Check back later for new opportunities.</p></div> : <div className="profile-list">{data.requests.map(request => { const response = data.responses.find(item => item.post_id === request.id); return <article className="profile-card" key={request.id}><div className="profile-info"><p className="eyebrow">STUDENT REQUEST #{request.id} · {request.status}</p><h3>{request.level}</h3><div className="tag-list">{request.subjects.map(subject => <span key={subject}>{subject}</span>)}</div><p>{request.experience || "No additional requirements"}</p><p className="muted">{request.availability || "Flexible"} · {request.location || "Location not specified"} · Budget ৳{request.fee}</p>{response && <p className="notice">Your response: {response.response} · {response.review_status}</p>}<div className="card-actions"><button className="button primary" disabled={busy} onClick={() => void respond(request.id, "Interested")}>{response?.response === "Interested" ? "Keep interested" : "Interested"}</button><button className="button secondary" disabled={busy} onClick={() => void respond(request.id, "Not Interested")}>{response?.response === "Not Interested" ? "Keep not interested" : "Not interested"}</button></div></div></article> })}</div>}</section>
      <section className="panel dashboard-panel"><h2>My responses</h2>{data.responses.length === 0 ? <p className="muted">Your responses will appear here.</p> : <div className="profile-list">{data.responses.map(item => <article className="profile-card" key={item.id}><div className="profile-info"><h3>Request #{item.post_id}</h3><p>{item.response} · {item.review_status}</p><p className="muted">Updated {new Date(item.updated_at).toLocaleDateString()}</p></div></article>)}</div>}</section>
    </>}
  </AppLayout>
}
