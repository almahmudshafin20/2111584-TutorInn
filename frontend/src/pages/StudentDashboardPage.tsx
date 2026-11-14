import { useEffect, useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
import type { StudentDashboard, LearningRequest, TutorProfile } from "../types/auth"
import { loadDashboard, createTutoringRequest, updateTutoringRequest, deleteTutoringRequest, discoverTutors, acceptTutorResponse } from "../services/dashboard"

const blank = { subjects: "", level: "", experience: "", availability: "", location: "", fee: "500", description: "" }
const emptyFilters = { subject: "", level: "", min_experience: "", availability: "" }

function statusKey(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-")
}

export default function StudentDashboardPage() {
  const { account } = useAuth()
  const [data, setData] = useState<StudentDashboard | null>(null)
  const [tutors, setTutors] = useState<TutorProfile[]>([])
  const [filters, setFilters] = useState(emptyFilters)
  const [form, setForm] = useState(blank)
  const [editId, setEditId] = useState<number | null>(null)
  const [error, setError] = useState("")
  const [tutorError, setTutorError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [tutorLoading, setTutorLoading] = useState(true)

  async function load() {
    setLoading(true)
    setError("")
    try {
      const result = await loadDashboard()
      if (result.role !== "student") throw new Error("This dashboard is only available to Student accounts.")
      setData(result)
    } catch (reason) {
      setData(null)
      setError(reason instanceof Error ? reason.message : "Could not load your dashboard.")
    } finally {
      setLoading(false)
    }
  }

  async function loadTutors(nextFilters: typeof emptyFilters = filters) {
    setTutorLoading(true)
    setTutorError("")
    try {
      setTutors(await discoverTutors(nextFilters))
    } catch (reason) {
      setTutors([])
      setTutorError(reason instanceof Error ? reason.message : "Could not load tutors. Please try again.")
    } finally {
      setTutorLoading(false)
    }
  }

  useEffect(() => {
    void load()
    void loadTutors(emptyFilters)
  }, [])

  async function searchTutors(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await loadTutors(filters)
  }

  function editRequest(item: LearningRequest) {
    setEditId(item.id)
    setForm({
      subjects: item.subjects.join(", "),
      level: item.level,
      experience: item.experience,
      availability: item.availability,
      location: item.location,
      fee: String(item.fee),
      description: item.description,
    })
    document.getElementById("create-request")?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  function reset() {
    setForm(blank)
    setEditId(null)
  }

  async function saveRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const subjects = form.subjects.split(",").map(value => value.trim()).filter(Boolean)
    if (!subjects.length) {
      setError("Enter at least one subject.")
      return
    }
    setBusy(true)
    setError("")
    setNotice("")
    const payload = {
      post_type: "student",
      subjects,
      level: form.level,
      experience: form.experience,
      availability: form.availability,
      location: form.location,
      fee: Number(form.fee),
      description: form.description,
    }
    try {
      if (editId === null) await createTutoringRequest(payload)
      else await updateTutoringRequest(editId, payload)
      setNotice(editId === null ? "Tutoring request published." : "Tutoring request updated.")
      reset()
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save your request.")
    } finally {
      setBusy(false)
    }
  }

  async function removeRequest(id: number) {
    if (!window.confirm("Delete this tutoring request and its responses?")) return
    setBusy(true)
    setError("")
    setNotice("")
    try {
      await deleteTutoringRequest(id)
      setNotice("Request deleted.")
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete your request.")
    } finally {
      setBusy(false)
    }
  }

  async function acceptResponse(requestId: number, responseId: number) {
    if (!window.confirm("Accept this Tutor? Other interested responses to this request will be declined.")) return
    setBusy(true)
    setError("")
    setNotice("")
    try {
      await acceptTutorResponse(requestId, responseId)
      setNotice("Tutor accepted. Your request is now marked Accepted.")
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not accept this Tutor.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppLayout>
      <section className="page-intro compact dashboard-intro">
        <p className="eyebrow">STUDENT WORKSPACE</p>
        <h1>Welcome, {data?.profile.full_name ?? account?.email}</h1>
        <p>Manage your tutoring requests, review tutor responses and discover tutors who match your learning goals.</p>
      </section>

      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status" aria-live="polite">{notice}</div>}

      {loading ? (
        <div className="dashboard-loading" role="status" aria-live="polite">Loading your dashboard…</div>
      ) : data ? (
        <>
          <section className="dashboard-stats" aria-label="Student dashboard summary">
            <article><strong>{data.requests.length}</strong><span>Your requests</span></article>
            <article><strong>{data.incoming_responses.length}</strong><span>Tutor responses</span></article>
            <article><strong>{data.profile.subjects.length}</strong><span>Learning subjects</span></article>
          </section>

          <section id="my-requests" className="panel dashboard-panel">
            <div className="panel-heading">
              <div><h2>My tutoring requests</h2><p>Create, update or remove your own requests.</p></div>
              <a className="text-link" href="#create-request">Create request</a>
            </div>
            {data.requests.length === 0 ? (
              <div className="empty-state">
                <h3>Your learning journey starts here</h3>
                <p>Publish a tutoring request to tell Tutors what you want to learn.</p>
                <a className="button primary" href="#create-request">Create a request</a>
              </div>
            ) : (
              <div className="profile-list">
                {data.requests.map(item => (
                  <article className="profile-card dashboard-record" key={item.id}>
                    <div className="profile-info">
                      <div className="dashboard-card-top">
                        <p className="eyebrow">REQUEST #{item.id}</p>
                        <span className={`status-pill status-${statusKey(item.status)}`}>{item.status}</span>
                      </div>
                      <h3>{item.level}</h3>
                      <div className="tag-list">{item.subjects.map(subject => <span key={subject}>{subject}</span>)}</div>
                      <p>{item.experience || "No additional requirements"} · {item.availability || "Availability flexible"}</p>
                      <p className="muted">৳{item.fee} · {item.location || "Location not specified"}</p>
                      <div className="card-actions">
                        <button className="small-button" disabled={busy} onClick={() => editRequest(item)}>Edit request</button>
                        <button className="small-button danger-text" disabled={busy} onClick={() => void removeRequest(item.id)}>Delete</button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section id="my-responses" className="panel dashboard-panel">
            <div className="panel-heading"><div><h2>Tutor responses</h2><p>Review the Tutors who are interested in helping you.</p></div></div>
            {data.incoming_responses.length === 0 ? (
              <div className="empty-state"><h3>No responses yet</h3><p>Tutor responses to your requests will appear here.</p></div>
            ) : (
              <div className="profile-list">
                {data.incoming_responses.map(response => (
                  <article className="profile-card dashboard-record" key={response.id}>
                    <div className="profile-info">
                      <div className="dashboard-card-top">
                        <h3>{response.tutor_profile?.full_name ?? "Tutor profile unavailable"}</h3>
                        <span className={`status-pill status-${statusKey(response.review_status)}`}>{response.review_status}</span>
                      </div>
                      <p>Request #{response.post_id} · {response.response}</p>
                      {response.tutor_profile && (
                        <>
                          <div className="tag-list">{response.tutor_profile.subjects.map(subject => <span key={subject}>{subject}</span>)}</div>
                          <p>{response.tutor_profile.teaching_level} · {response.tutor_profile.experience_years} years experience</p>
                          <p className="muted">৳{response.tutor_profile.hourly_rate}/hour · {response.tutor_profile.availability || "Availability not listed"}</p>
                          <p>{response.tutor_profile.bio || "No tutor biography provided."}</p>
                        </>
                      )}
                      <p className="muted">Updated {new Date(response.updated_at).toLocaleDateString()}</p>
                      {response.response === "Interested" && response.review_status === "Pending" && (
                        <button className="button primary" disabled={busy} onClick={() => void acceptResponse(response.post_id, response.id)}>Accept this Tutor</button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section id="find-tutors" className="panel dashboard-panel">
            <div className="panel-heading"><div><h2>Discover tutors</h2><p>Find teaching support by subject, qualification, experience and availability.</p></div></div>
            <form className="dashboard-filters" onSubmit={searchTutors} aria-label="Filter tutor search">
              <label className="field">Subject<input value={filters.subject} onChange={event => setFilters({ ...filters, subject: event.target.value })} placeholder="Mathematics" /></label>
              <label className="field">Qualification / level<input value={filters.level} onChange={event => setFilters({ ...filters, level: event.target.value })} placeholder="HSC, University" /></label>
              <label className="field">Minimum experience (years)<input type="number" min="0" max="60" value={filters.min_experience} onChange={event => setFilters({ ...filters, min_experience: event.target.value })} /></label>
              <label className="field">Availability<input value={filters.availability} onChange={event => setFilters({ ...filters, availability: event.target.value })} placeholder="Weekends" /></label>
              <div className="actions">
                <button className="button primary" disabled={tutorLoading}>{tutorLoading ? "Searching…" : "Search tutors"}</button>
                <button type="button" className="button secondary" disabled={tutorLoading} onClick={() => { setFilters(emptyFilters); void loadTutors(emptyFilters) }}>Clear filters</button>
              </div>
            </form>
            <div aria-live="polite" aria-busy={tutorLoading}>
              {tutorLoading ? (
                <p className="dashboard-loading">Finding tutors…</p>
              ) : tutorError ? (
                <div className="alert error" role="alert">{tutorError} <button className="small-button" onClick={() => void loadTutors(filters)}>Try again</button></div>
              ) : tutors.length === 0 ? (
                <div className="empty-state"><h3>No tutors found</h3><p>Try a broader subject, qualification or availability, or check again later.</p></div>
              ) : (
                <div className="tutor-grid">
                  {tutors.map(tutor => (
                    <article className="tutor-card" key={tutor.id}>
                      <p className="eyebrow">TUTOR PROFILE</p>
                      <h3>{tutor.full_name}</h3>
                      <div className="tag-list">{tutor.subjects.map(subject => <span key={subject}>{subject}</span>)}</div>
                      <p>{tutor.teaching_level} · {tutor.experience_years} years experience</p>
                      <p className="muted">{tutor.availability || "Availability not listed"} · ৳{tutor.hourly_rate}/hour</p>
                      <p>{tutor.bio || "Tutor profile"}</p>
                      <a className="text-link tutor-profile-link" href={`/tutors/${tutor.id}`}>View tutor profile</a>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </section>

          <section id="create-request" className="panel dashboard-panel">
            <div className="panel-heading"><div><h2>{editId === null ? "Create a tutoring request" : "Edit tutoring request"}</h2><p>Share your learning needs so Tutors can respond.</p></div></div>
            <form className="profile-form" onSubmit={saveRequest}>
              <label className="field">Subjects (comma separated)<input required value={form.subjects} onChange={event => setForm({ ...form, subjects: event.target.value })} placeholder="Mathematics, Physics" /></label>
              <label className="field">Learning level<input required value={form.level} onChange={event => setForm({ ...form, level: event.target.value })} placeholder="HSC" /></label>
              <label className="field">Learning goals or requirements<textarea rows={3} value={form.experience} onChange={event => setForm({ ...form, experience: event.target.value })} /></label>
              <label className="field">Availability<input value={form.availability} onChange={event => setForm({ ...form, availability: event.target.value })} placeholder="Weekday evenings, weekends…" /></label>
              <label className="field">Location<input value={form.location} onChange={event => setForm({ ...form, location: event.target.value })} /></label>
              <label className="field">Budget (৳)<input type="number" min="0" max="1000000" required value={form.fee} onChange={event => setForm({ ...form, fee: event.target.value })} /></label>
              <label className="field">Additional details<textarea rows={3} value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} /></label>
              <div className="actions">
                <button className="button primary" disabled={busy}>{busy ? "Saving…" : editId === null ? "Publish request" : "Save changes"}</button>
                {editId !== null && <button type="button" className="button secondary" onClick={reset}>Cancel</button>}
              </div>
            </form>
          </section>
        </>
      ) : null}
    </AppLayout>
  )
}
