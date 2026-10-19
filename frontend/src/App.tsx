import { FormEvent, useEffect, useMemo, useState } from "react"

type Student = {
  id: number
  full_name: string
  email: string
  education_level: string
  preferred_subjects: string
}

type Tutor = {
  id: number
  full_name: string
  email: string
  subject: string
  teaching_level: string
  experience_years: number
  hourly_rate: number
  bio: string
}

type Profile = Student | Tutor
type Field = { name: string; label: string; type?: string; required?: boolean; placeholder?: string }

const studentFields: Field[] = [
  { name: "full_name", label: "Full name", required: true, placeholder: "e.g. Ayesha Rahman" },
  { name: "email", label: "Email", type: "email", required: true, placeholder: "you@example.com" },
  { name: "education_level", label: "Education level", required: true, placeholder: "e.g. HSC, University" },
  { name: "preferred_subjects", label: "Preferred subjects", placeholder: "e.g. Mathematics, Physics" },
]

const tutorFields: Field[] = [
  { name: "full_name", label: "Full name", required: true, placeholder: "e.g. Rahim Ahmed" },
  { name: "email", label: "Email", type: "email", required: true, placeholder: "you@example.com" },
  { name: "subject", label: "Subject", required: true, placeholder: "e.g. Mathematics" },
  { name: "teaching_level", label: "Teaching level", required: true, placeholder: "e.g. Secondary, HSC" },
  { name: "experience_years", label: "Experience (years)", type: "number", required: true, placeholder: "3" },
  { name: "hourly_rate", label: "Hourly rate (৳)", type: "number", required: true, placeholder: "500" },
  { name: "bio", label: "Short bio", type: "textarea", placeholder: "Briefly describe your teaching experience." },
]

const emptyStudent = { full_name: "", email: "", education_level: "", preferred_subjects: "" }
const emptyTutor = { full_name: "", email: "", subject: "", teaching_level: "", experience_years: "0", hourly_rate: "500", bio: "" }

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: { ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
  })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      message = typeof body.detail === "string" ? body.detail : message
    } catch {
      // Keep the status message when the response is not JSON.
    }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function Header() {
  return (
    <header className="site-header">
      <a className="brand" href="/">TutorInn<span>.</span></a>
      <nav aria-label="Main navigation">
        <a href="/">Home</a>
        <a href="/tutors">Find Tutors</a>
        <a href="/students">Students</a>
        <a href="/about">About</a>
        <a href="/task-details">Task Details</a>
      </nav>
    </header>
  )
}

function Footer() {
  return <footer className="site-footer">TutorInn · A simple place to connect learners and tutors.</footer>
}

function Layout({ children }: { children: React.ReactNode }) {
  return <><Header /><main className="page">{children}</main><Footer /></>
}

function HomePage() {
  return (
    <Layout>
      <section className="hero">
        <p className="eyebrow">LEARN WITH CONFIDENCE</p>
        <h1>Find the right tutor.<br /><span>Reach your next goal.</span></h1>
        <p className="hero-copy">TutorInn helps students discover tutors by subject and level, while tutors can manage their teaching profiles in one simple place.</p>
        <div className="actions">
          <a className="button primary" href="/tutors">Explore tutors</a>
          <a className="button secondary" href="/students">Student profiles</a>
        </div>
      </section>
      <section className="section">
        <div className="section-heading"><p className="eyebrow">HOW IT WORKS</p><h2>Everything you need to get started</h2></div>
        <div className="feature-grid">
          <article className="feature-card"><span className="feature-icon">⌕</span><h3>Discover tutors</h3><p>Search by tutor name, subject, or teaching level and open a profile for more details.</p></article>
          <article className="feature-card"><span className="feature-icon">◎</span><h3>Manage profiles</h3><p>Keep student and tutor information organized with simple create, view, edit, and delete actions.</p></article>
          <article className="feature-card"><span className="feature-icon">✓</span><h3>Built for learning</h3><p>A focused student project using React, TypeScript, FastAPI, and a database.</p></article>
        </div>
      </section>
    </Layout>
  )
}

function AboutPage() {
  return <Layout>
    <section className="page-intro"><p className="eyebrow">ABOUT TUTORINN</p><h1>Learning starts with the right connection.</h1><p>TutorInn is a simple tutoring platform concept designed to help students find suitable tutors and help tutors present their teaching experience.</p></section>
    <section className="content-panel"><h2>Our goal</h2><p>Make tutor discovery and profile management clear and accessible. Students can browse tutor information, while both students and tutors have profile management screens for the project MVP.</p><h2>How it is built</h2><p>The frontend uses React and TypeScript. FastAPI provides REST endpoints, and SQLAlchemy connects the API to a persistent database configured through <code>DATABASE_URL</code>.</p><a className="text-link" href="/tutors">Start exploring tutors →</a></section>
  </Layout>
}

function TaskDetailsPage() {
  return <Layout>
    <section className="page-intro"><p className="eyebrow">PROJECT TASK DETAILS</p><h1>Mid Project Assessment MVP</h1><p>The main goal is to demonstrate complete CRUD functionality for both Students and Tutors through a frontend, REST API, and database.</p></section>
    <section className="content-panel"><h2>Core requirements</h2><ul className="check-list"><li>Create, list, view, update, and delete student profiles.</li><li>Create, list, view, update, and delete tutor profiles.</li><li>Send real requests from React to FastAPI.</li><li>Persist records in the configured database.</li><li>Keep Home, About, and Task Details as separate pages.</li><li>Demonstrate requests and responses using browser DevTools or Postman.</li></ul><h2>Technology</h2><div className="tag-list"><span>React</span><span>TypeScript</span><span>FastAPI</span><span>SQLAlchemy</span><span>PostgreSQL / Supabase</span></div><p className="notice">This assessment build does not yet include login or ownership-based authorization. Configure a persistent PostgreSQL/Supabase DATABASE_URL for deployment; local development uses SQLite.</p></section>
  </Layout>
}

function ProfileManager({ kind }: { kind: "student" | "tutor" }) {
  const isTutor = kind === "tutor"
  const endpoint = `/api/${kind}s`
  const fields = isTutor ? tutorFields : studentFields
  const blank = isTutor ? emptyTutor : emptyStudent
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [form, setForm] = useState<Record<string, string>>(blank)
  const [editId, setEditId] = useState<number | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  async function loadProfiles(term = search) {
    setLoading(true)
    setError("")
    try {
      const query = term.trim() ? `?q=${encodeURIComponent(term.trim())}` : ""
      setProfiles(await api<Profile[]>(endpoint + query))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load profiles.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadProfiles("") }, [endpoint])

  const visibleFields = fields
  const heading = isTutor ? "Tutor profiles" : "Student profiles"
  const subtitle = isTutor
    ? "Find tutors by name or subject, view details, and manage tutor profiles."
    : "Create and manage student records for the TutorInn MVP."

  function resetForm() {
    setForm(blank)
    setEditId(null)
  }

  function startEdit(profile: Profile) {
    const values: Record<string, string> = {}
    for (const field of visibleFields) values[field.name] = String((profile as unknown as Record<string, unknown>)[field.name] ?? "")
    setForm(values)
    setEditId(profile.id)
    setNotice("")
    setError("")
    document.getElementById("profile-form")?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError("")
    setNotice("")
    const payload: Record<string, string | number> = { ...form }
    if (isTutor) {
      payload.experience_years = Number(form.experience_years)
      payload.hourly_rate = Number(form.hourly_rate)
    }
    try {
      if (editId === null) {
        await api<Profile>(endpoint, { method: "POST", body: JSON.stringify(payload) })
        setNotice(`${isTutor ? "Tutor" : "Student"} profile created successfully.`)
      } else {
        await api<Profile>(`${endpoint}/${editId}`, { method: "PUT", body: JSON.stringify(payload) })
        setNotice(`${isTutor ? "Tutor" : "Student"} profile updated successfully.`)
      }
      resetForm()
      await loadProfiles()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile.")
    } finally {
      setSaving(false)
    }
  }

  async function deleteProfile(profile: Profile) {
    if (!window.confirm(`Delete the profile for ${profile.full_name}? This cannot be undone.`)) return
    setError("")
    setNotice("")
    try {
      await api<void>(`${endpoint}/${profile.id}`, { method: "DELETE" })
      setNotice("Profile deleted.")
      if (editId === profile.id) resetForm()
      await loadProfiles()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete profile.")
    }
  }

  const tutorProfiles = useMemo(() => profiles as Tutor[], [profiles])
  const studentProfiles = useMemo(() => profiles as Student[], [profiles])

  return <Layout>
    <section className="page-intro compact"><p className="eyebrow">{isTutor ? "TUTOR DIRECTORY" : "STUDENT MANAGEMENT"}</p><h1>{heading}</h1><p>{subtitle}</p></section>
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    <section className="manager-grid">
      <div className="panel list-panel">
        <div className="panel-heading"><div><h2>{isTutor ? "Browse tutors" : "All students"}</h2><p>{profiles.length} profile{profiles.length === 1 ? "" : "s"}</p></div></div>
        <form className="search-form" onSubmit={e => { e.preventDefault(); void loadProfiles(search) }}>
          <input aria-label={isTutor ? "Search tutors" : "Search students"} value={search} onChange={e => setSearch(e.target.value)} placeholder={isTutor ? "Search name, subject or bio" : "Search name or subject"} />
          <button className="button primary" type="submit">Search</button>
          {search && <button className="button secondary" type="button" onClick={() => { setSearch(""); void loadProfiles("") }}>Clear</button>}
        </form>
        {loading ? <p className="muted">Loading profiles…</p> : profiles.length === 0 ? <div className="empty-state"><h3>No profiles yet</h3><p>Create the first profile using the form.</p></div> : <div className="profile-list">
          {isTutor ? tutorProfiles.map(profile => <article className="profile-card" key={profile.id}>
            <div className="avatar">{profile.full_name.trim().charAt(0).toUpperCase()}</div>
            <div className="profile-info"><h3><a href={`/tutors/${profile.id}`}>{profile.full_name}</a></h3><p>{profile.subject} · {profile.teaching_level}</p><p className="muted">{profile.experience_years} year{profile.experience_years === 1 ? "" : "s"} experience · ৳{profile.hourly_rate}/hour</p><div className="card-actions"><a className="text-link" href={`/tutors/${profile.id}`}>View details</a><button type="button" className="small-button" onClick={() => startEdit(profile)}>Edit</button><button type="button" className="small-button danger-text" onClick={() => void deleteProfile(profile)}>Delete</button></div></div>
          </article>) : studentProfiles.map(profile => <article className="profile-card" key={profile.id}>
            <div className="avatar student-avatar">{profile.full_name.trim().charAt(0).toUpperCase()}</div>
            <div className="profile-info"><h3><a href={`/students/${profile.id}`}>{profile.full_name}</a></h3><p>{profile.education_level}</p><p className="muted">{profile.preferred_subjects || "No preferred subjects listed"}</p><div className="card-actions"><a className="text-link" href={`/students/${profile.id}`}>View details</a><button type="button" className="small-button" onClick={() => startEdit(profile)}>Edit</button><button type="button" className="small-button danger-text" onClick={() => void deleteProfile(profile)}>Delete</button></div></div>
          </article>)}
        </div>}
      </div>
      <aside className="panel form-panel" id="profile-form">
        <h2>{editId === null ? `Create ${isTutor ? "tutor" : "student"} profile` : "Edit profile"}</h2>
        <p className="muted">{editId === null ? "Fill in the details below to add a profile." : `Editing profile #${editId}.`}</p>
        <form className="profile-form" onSubmit={submitForm}>
          {visibleFields.map(field => <label className="field" key={field.name}>{field.label}{field.type === "textarea" ? <textarea value={form[field.name] ?? ""} onChange={e => setForm({ ...form, [field.name]: e.target.value })} placeholder={field.placeholder} rows={4} maxLength={2000} /> : <input type={field.type ?? "text"} value={form[field.name] ?? ""} onChange={e => setForm({ ...form, [field.name]: e.target.value })} placeholder={field.placeholder} required={field.required} min={field.name === "experience_years" ? 0 : field.name === "hourly_rate" ? 1 : undefined} max={field.name === "experience_years" ? 60 : undefined} step={field.name === "hourly_rate" ? "0.01" : "1"} />}</label>)}
          <div className="actions"><button className="button primary" type="submit" disabled={saving}>{saving ? "Saving…" : editId === null ? "Create profile" : "Save changes"}</button>{editId !== null && <button className="button secondary" type="button" onClick={resetForm}>Cancel</button>}</div>
        </form>
      </aside>
    </section>
  </Layout>
}

function DetailPage({ kind, id }: { kind: "student" | "tutor"; id: number }) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [error, setError] = useState("")
  const isTutor = kind === "tutor"
  useEffect(() => {
    api<Profile>(`/api/${kind}s/${id}`).then(setProfile).catch(err => setError(err instanceof Error ? err.message : "Could not load profile."))
  }, [kind, id])
  return <Layout>
    <a className="text-link back-link" href={isTutor ? "/tutors" : "/students"}>← Back to {isTutor ? "tutors" : "students"}</a>
    {error ? <div className="alert error">{error}</div> : !profile ? <p className="muted">Loading profile…</p> : <section className="detail-card">
      <div className="detail-avatar">{profile.full_name.charAt(0).toUpperCase()}</div>
      <p className="eyebrow">{isTutor ? "TUTOR PROFILE" : "STUDENT PROFILE"} · #{profile.id}</p>
      <h1>{profile.full_name}</h1>
      <p className="detail-email">{profile.email}</p>
      {isTutor && "subject" in profile ? <><div className="tag-list"><span>{profile.subject}</span><span>{profile.teaching_level}</span></div><div className="detail-stats"><div><strong>{profile.experience_years}</strong><span>Years experience</span></div><div><strong>৳{profile.hourly_rate}</strong><span>Hourly rate</span></div></div><h2>About the tutor</h2><p>{profile.bio || "This tutor has not added a bio yet."}</p></> : "education_level" in profile ? <><h2>Education level</h2><p>{profile.education_level}</p><h2>Preferred subjects</h2><p>{profile.preferred_subjects || "No preferred subjects listed."}</p></> : null}
    </section>}
  </Layout>
}

export default function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/"
  if (path === "/") return <HomePage />
  if (path === "/about") return <AboutPage />
  if (path === "/task-details") return <TaskDetailsPage />
  if (path === "/tutors") return <ProfileManager kind="tutor" />
  if (path === "/students") return <ProfileManager kind="student" />
  const tutorMatch = path.match(/^\/tutors\/(\d+)$/)
  if (tutorMatch) return <DetailPage kind="tutor" id={Number(tutorMatch[1])} />
  const studentMatch = path.match(/^\/students\/(\d+)$/)
  if (studentMatch) return <DetailPage kind="student" id={Number(studentMatch[1])} />
  return <Layout><section className="empty-state"><h1>Page not found</h1><p>The page you're looking for doesn't exist.</p><a className="button primary" href="/">Back home</a></section></Layout>
}
