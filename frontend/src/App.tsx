import { useEffect, useMemo, useState } from "react"
import type { FormEvent, ReactNode } from "react"
import { useTheme } from "./context/ThemeContext"

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
  const { theme, toggleTheme } = useTheme()
  const nextTheme = theme === "dark" ? "light" : "dark"

  return (
    <header className="site-header">
      <a className="brand" href="/">TutorInn<span>.</span></a>
      <nav aria-label="Main navigation">
        <a href="/">Home</a>
        <a href="/tutors">Find Tutors</a>
        <a href="/students">Students</a>
        <a href="/about">About</a>
        <a href="/tutor-posts">Tutor Posts</a>
        <a href="/student-requests">Student Requests</a>
        <a href="/task-details">Task Details</a>
      </nav>
      <button
        className="theme-toggle"
        type="button"
        onClick={toggleTheme}
        aria-label={`Switch to ${nextTheme} theme`}
        title={`Switch to ${nextTheme} theme`}
      >
        <span aria-hidden="true">{theme === "dark" ? "☀" : "☾"}</span>
        <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
      </button>
    </header>
  )
}

function Footer() {
  return <footer className="site-footer">TutorInn · A simple place to connect learners and tutors.</footer>
}

function Layout({ children }: { children: ReactNode }) {
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
    <a className="text-link back-link" href="/">← Back to Home</a>
    <section className="page-intro compact">
      <p className="eyebrow">CURRENT PROJECT TASK</p>
      <h1>Student & Tutor CRUD MVP</h1>
      <p>Complete profile management for TutorInn, connecting the React interface with FastAPI REST APIs and the project database.</p>
    </section>

    <section className="detail-card task-detail-card">
      <div className="task-detail-header">
        <div className="task-icon" aria-hidden="true">✓</div>
        <div>
          <p className="eyebrow">TUTORINN · MVP</p>
          <h2>Student & Tutor Profile Management</h2>
        </div>
      </div>

      <div className="task-meta-grid">
        <div><span>Status</span><strong className="task-status">In Progress</strong></div>
        <div><span>Priority</span><strong>High</strong></div>
        <div><span>Scope</span><strong>Student + Tutor</strong></div>
        <div><span>Feature area</span><strong>Core MVP</strong></div>
      </div>

      <div className="task-description">
        <h2>Description</h2>
        <p>Build a working profile-management flow so TutorInn can create, view, update, and delete student and tutor records. The interface should use the real FastAPI endpoints and persist records through the configured database.</p>
      </div>

      <div className="task-section">
        <h2>Work included</h2>
        <ul className="check-list">
          <li>Student profile creation, list view, single-profile view, editing, and deletion.</li>
          <li>Tutor profile creation, list/search, single-profile view, editing, and deletion.</li>
          <li>FastAPI REST endpoints with validation and useful error responses.</li>
          <li>SQLAlchemy database models with PostgreSQL/Supabase deployment support.</li>
          <li>Separate Home, About, and Task Details pages within the TutorInn interface.</li>
        </ul>
      </div>

      <div className="task-section">
        <h2>Technology</h2>
        <div className="tag-list">
          <span>React</span>
          <span>TypeScript</span>
          <span>FastAPI</span>
          <span>SQLAlchemy</span>
          <span>PostgreSQL / Supabase</span>
        </div>
      </div>

      <div className="task-section task-note">
        <h2>Current progress</h2>
        <p>The CRUD implementation is in the current feature branch. Local API verification has passed; live Vercel and production database verification is the remaining step before this MVP is considered fully verified.</p>
      </div>
    </section>
  </Layout>
}



type LearningPost = {
  id: number; post_type: "tutor" | "student"; author_name: string; subject: string; level: string;
  experience: string; availability: string; location: string; fee: number; description: string;
  status: "Pending" | "Completed" | "Withdrawn"; student_confirmed: boolean; tutor_confirmed: boolean;
}
const emptyPost = { author_name: "", subject: "", level: "", experience: "", availability: "", location: "", fee: "500", description: "" }

function LearningPostsPage({ kind }: { kind: "tutor" | "student" }) {
  const endpoint = "/api/posts";
  const [posts, setPosts] = useState<LearningPost[]>([]);
  const [form, setForm] = useState<Record<string,string>>(emptyPost);
  const [editId, setEditId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [actor, setActor] = useState<"student"|"tutor">(kind);
  async function load() {
    setLoading(true); setError("");
    try { setPosts(await api<LearningPost[]>(`${endpoint}?post_type=${kind}`)); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not load posts."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [kind]);
  function reset() { setForm(emptyPost); setEditId(null); }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setBusy(true); setError(""); setNotice("");
    const payload = { ...form, post_type: kind, fee: Number(form.fee) };
    try {
      await api(editId === null ? endpoint : `${endpoint}/${editId}`, { method: editId === null ? "POST" : "PUT", body: JSON.stringify(payload) });
      setNotice(editId === null ? "Post created." : "Post updated."); reset(); await load();
    } catch(err) { setError(err instanceof Error ? err.message : "Could not save post."); }
    finally { setBusy(false); }
  }
  async function action(id:number, actionName:"confirm"|"withdraw") {
    setError(""); setNotice("");
    try {
      const updated = await api<LearningPost>(`${endpoint}/${id}/${actionName}`, { method:"POST", body:JSON.stringify({ actor }) });
      setPosts(old => old.map(p => p.id === id ? updated : p));
      setNotice(actionName === "confirm" ? `Confirmation saved. Current status: ${updated.status}.` : "Request withdrawn.");
    } catch(err) { setError(err instanceof Error ? err.message : "Action failed."); }
  }
  return <Layout>
    <section className="page-intro compact"><p className="eyebrow">{kind === "tutor" ? "TEACHING OPPORTUNITIES" : "FIND A TUTOR"}</p><h1>{kind === "tutor" ? "Tutor Posts" : "Student Requests"}</h1><p>{kind === "tutor" ? "Share what you teach, your experience, schedule, location and expected fee." : "Describe the subject, learning level, goals, schedule, location and budget you need."}</p></section>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    <section className="manager-grid">
      <div className="panel list-panel"><div className="panel-heading"><div><h2>{kind === "tutor" ? "Teaching offers" : "Open learning requests"}</h2><p>{posts.length} post{posts.length === 1 ? "" : "s"}</p></div></div>
        {loading ? <p className="muted">Loading posts…</p> : posts.length === 0 ? <div className="empty-state"><h3>No posts yet</h3><p>Create a post using the form.</p></div> : <div className="profile-list">{posts.map(p => <article className="profile-card" key={p.id}><div className="avatar">{p.author_name.charAt(0).toUpperCase()}</div><div className="profile-info"><h3>{p.subject} · {p.level}</h3><p>Posted by {p.author_name}</p><p className="muted">{p.availability || "Schedule flexible"} · {p.location || "Location not specified"}</p><p>{p.description}</p><p><strong>৳{p.fee}</strong> · <span className={p.status === "Completed" ? "task-status" : ""}>{p.status}</span></p>{p.experience && <p className="muted">Experience / goals: {p.experience}</p>}
        <div className="card-actions"><button className="small-button" type="button" onClick={() => { setForm({author_name:p.author_name,subject:p.subject,level:p.level,experience:p.experience,availability:p.availability,location:p.location,fee:String(p.fee),description:p.description}); setEditId(p.id); }}>Edit</button><button className="small-button" type="button" onClick={() => void action(p.id,"confirm")}>I'm Interested / Confirm</button><button className="small-button danger-text" type="button" onClick={() => void action(p.id,"withdraw")}>Withdraw</button><button className="small-button danger-text" type="button" onClick={async () => { if (!window.confirm("Delete this post permanently?")) return; try { await api<void>(`/api/posts/${p.id}`, { method: "DELETE" }); setNotice("Post deleted."); await load(); } catch(err) { setError(err instanceof Error ? err.message : "Could not delete post."); } }}>Delete</button><a className="text-link" href={`/task-details?id=${p.id}`}>Task details</a></div>
        <p className="muted">Student: {p.student_confirmed ? "confirmed" : "waiting"} · Tutor: {p.tutor_confirmed ? "confirmed" : "waiting"}</p></div></article>)}</div>}
      </div>
      <aside className="panel form-panel"><h2>{editId === null ? `Create ${kind === "tutor" ? "tutor post" : "student request"}` : "Edit post"}</h2><form className="profile-form" onSubmit={submit}>
        {([{name:"author_name",label:"Your name"},{name:"subject",label:kind==="tutor"?"Subject you teach":"Subject needed"},{name:"level",label:"Teaching / learning level"},{name:"experience",label:kind==="tutor"?"Teaching experience":"Learning goals / requirements"},{name:"availability",label:"Preferred days and times"},{name:"location",label:"Teaching / learning location"},{name:"fee",label:kind==="tutor"?"Expected fee (৳)":"Budget (৳)",type:"number"},{name:"description",label:"Description",type:"textarea"}] as Field[]).map(f => <label className="field" key={f.name}>{f.label}{f.type==="textarea" ? <textarea required value={form[f.name]??""} rows={4} onChange={e=>setForm({...form,[f.name]:e.target.value})}/> : <input required={["author_name","subject","level","fee"].includes(f.name)} type={f.type??"text"} value={form[f.name]??""} min={f.type==="number"?0:undefined} onChange={e=>setForm({...form,[f.name]:e.target.value})}/>}</label>)}
        <label className="field">Confirming as<select value={actor} onChange={e=>setActor(e.target.value as "student"|"tutor")}><option value="student">Student</option><option value="tutor">Tutor</option></select></label>
        <div className="actions"><button className="button primary" disabled={busy} type="submit">{busy?"Saving…":editId===null?"Publish post":"Save changes"}</button>{editId!==null&&<button className="button secondary" type="button" onClick={reset}>Cancel</button>}</div>
      </form></aside>
    </section>
  </Layout>
}

function RequestDetailsPage() {
  const id = new URLSearchParams(window.location.search).get("id");
  const [post,setPost] = useState<LearningPost|null>(null); const [error,setError] = useState("");
  useEffect(()=>{ if(id) api<LearningPost>(`/api/posts/${id}`).then(setPost).catch(e=>setError(e instanceof Error?e.message:"Could not load request.")); else setError("Choose a task from Tutor Posts or Student Requests to view its details."); },[id]);
  return <Layout><a className="text-link back-link" href="/student-requests">← Back to requests</a>{error?<div className="alert error">{error}</div>:!post?<p className="muted">Loading request…</p>:<section className="detail-card"><p className="eyebrow">TUTORINN · REQUEST #{post.id}</p><h1>{post.subject} · {post.level}</h1><p className="task-status">{post.status}</p><p>{post.description}</p><div className="task-meta-grid"><div><span>Posted by</span><strong>{post.author_name}</strong></div><div><span>Availability</span><strong>{post.availability||"Flexible"}</strong></div><div><span>Location</span><strong>{post.location||"Not specified"}</strong></div><div><span>Fee / budget</span><strong>৳{post.fee}</strong></div></div><h2>Confirmation status</h2><p>Student: {post.student_confirmed?"Confirmed":"Pending"} · Tutor: {post.tutor_confirmed?"Confirmed":"Pending"}</p><p className="muted">A request becomes Completed only after both parties confirm.</p></section>}</Layout>
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
  if (path === "/task-details") return window.location.search ? <RequestDetailsPage /> : <TaskDetailsPage />
  if (path === "/tutor-posts") return <LearningPostsPage kind="tutor" />
  if (path === "/student-requests") return <LearningPostsPage kind="student" />
  if (path === "/tutors") return <ProfileManager kind="tutor" />
  if (path === "/students") return <ProfileManager kind="student" />
  const tutorMatch = path.match(/^\/tutors\/(\d+)$/)
  if (tutorMatch) return <DetailPage kind="tutor" id={Number(tutorMatch[1])} />
  const studentMatch = path.match(/^\/students\/(\d+)$/)
  if (studentMatch) return <DetailPage kind="student" id={Number(studentMatch[1])} />
  return <Layout><section className="empty-state"><h1>Page not found</h1><p>The page you're looking for doesn't exist.</p><a className="button primary" href="/">Back home</a></section></Layout>
}
