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
        <a href="/about">About</a>
        <a href="/posts">Tutoring Hub</a>
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

type LearningPost = {
  id: number; post_type: "tutor" | "student"; author_name: string; subject: string; level: string;
  experience: string; availability: string; location: string; fee: number; description: string;
  status: "Pending" | "Accepted" | "Completed" | "Withdrawn"; student_confirmed: boolean; tutor_confirmed: boolean;
}
const emptyPost = { author_name: "", subject: "", level: "", experience: "", availability: "", location: "", fee: "500", description: "" }

function TaskDetailsPage() {
  const [posts, setPosts] = useState<LearningPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    api<LearningPost[]>("/api/posts?offset=0&limit=20")
      .then(setPosts)
      .catch(e => setError(e instanceof Error ? e.message : "Could not load tasks."))
      .finally(() => setLoading(false));
  }, []);
  return <Layout>
    <section className="page-intro compact"><p className="eyebrow">TASK DETAILS</p><h1>Post progress and status</h1><p>See the current confirmation status for tutor offers and student requests. Open any post to view its full details.</p></section>
    {error && <div className="alert error" role="alert">{error}</div>}
    {loading ? <p className="muted">Loading tasks…</p> : posts.length === 0 ? <div className="empty-state"><h2>No tasks yet</h2><p>Publish a tutor offer or student request from Tutoring Hub to track acceptance here.</p><a className="button primary" href="/posts">Create a post</a></div> :
      <section className="panel list-panel">
        <div className="panel-heading"><div><h2>Recent tasks</h2><p>Track whether a tutor offer or student request has been accepted.</p></div></div>
        <div className="profile-list">{posts.map(post => <article className="profile-card" key={post.id}>
          <div className={post.post_type === "student" ? "avatar student-avatar" : "avatar"}>{post.author_name.charAt(0).toUpperCase()}</div>
          <div className="profile-info"><h3>{post.subject} · {post.level}</h3><p>{post.post_type === "tutor" ? "Tutor offer" : "Student request"} · Posted by {post.author_name}</p>
            <p><strong className={post.status === "Accepted" || post.status === "Completed" ? "task-status" : ""}>{post.status}</strong> · {post.post_type === "tutor" ? "Student acceptance" : "Tutor acceptance"}: {(post.post_type === "tutor" ? post.student_confirmed : post.tutor_confirmed) ? "accepted" : "waiting"}</p>
            <div className="card-actions"><a className="text-link" href={"/task-details?id=" + post.id}>View task details</a><a className="text-link" href={"/task-details?id=" + post.id + "&edit=1"}>Edit</a><button className="small-button danger-text" type="button" onClick={async () => { if (!window.confirm("Delete this task permanently? This cannot be undone.")) return; try { await api<void>("/api/posts/" + post.id, {method:"DELETE"}); setPosts(current => current.filter(item => item.id !== post.id)); } catch(e) { setError(e instanceof Error ? e.message : "Could not delete task."); } }}>Delete</button><a className="text-link" href="/posts">All posts</a></div>
          </div>
        </article>)}</div>
      </section>}
  </Layout>;
}

function LearningPostsPage() {
  const endpoint = "/api/posts";
  const [posts, setPosts] = useState<LearningPost[]>([]);
  const [form, setForm] = useState<Record<string,string>>(emptyPost);
  const [editId, setEditId] = useState<number | null>(null);
  const [postKind, setPostKind] = useState<"tutor" | "student">("tutor");
  const [filter, setFilter] = useState<"all" | "tutor" | "student">("all");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const pageSize = 20;
  const maxPosts = 200;

  async function load(reset = true) {
    if (reset) setLoading(true);
    setError("");
    try {
      const offset = reset ? 0 : posts.length;
      const query = filter === "all" ? "" : "&post_type=" + filter;
      const result = await api<LearningPost[]>(endpoint + "?offset=" + offset + "&limit=" + pageSize + query);
      setPosts(old => reset ? result.slice(0, maxPosts) : [...old, ...result].slice(0, maxPosts));
      setHasMore(result.length === pageSize && (reset ? result.length : posts.length + result.length) < maxPosts);
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not load posts.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }

  useEffect(() => { setPosts([]); setHasMore(true); void load(true); }, [filter]);

  function resetForm() {
    setForm(emptyPost);
    setEditId(null);
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true); setError(""); setNotice("");
    const payload = { ...form, post_type: postKind, fee: Number(form.fee) };
    try {
      await api(editId === null ? endpoint : endpoint + "/" + editId, {
        method: editId === null ? "POST" : "PUT",
        body: JSON.stringify(payload)
      });
      setNotice(editId === null ? "Listing published." : "Listing updated.");
      resetForm();
      setFilter("all");
      await load(true);
    } catch(err) {
      setError(err instanceof Error ? err.message : "Could not save post.");
    } finally {
      setBusy(false);
    }
  }

  async function action(post: LearningPost, actionName: "confirm" | "withdraw") {
    setError(""); setNotice("");
    try {
      const init: RequestInit = { method: "POST" };
      if (actionName === "confirm") {
        const actor = post.post_type === "tutor" ? "student" : "tutor";
        init.body = JSON.stringify({ actor });
      }
      const updated = await api<LearningPost>(endpoint + "/" + post.id + "/" + actionName, init);
      setPosts(old => old.map(p => p.id === post.id ? updated : p));
      setNotice(actionName === "confirm" ? (post.post_type === "tutor" ? "Tutor offer accepted as a student." : "Student request accepted as a tutor.") : "Task withdrawn.");
    } catch(err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    }
  }

  async function deletePost(id: number) {
    if (!window.confirm("Delete this post permanently?")) return;
    try {
      await api<void>(endpoint + "/" + id, { method: "DELETE" });
      setNotice("Post deleted.");
      await load(true);
    } catch(err) {
      setError(err instanceof Error ? err.message : "Could not delete post.");
    }
  }

  const visiblePosts = posts.filter(post => filter === "all" || post.post_type === filter);

  return <Layout>
    <section className="page-intro compact"><p className="eyebrow">TUTORINN COMMUNITY</p><h1>Tutoring Hub</h1><p>Create a tutor offer or a student request, then browse both types together in one place.</p></section>
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    <section className="panel posts-panel">
      <div className="posts-toolbar">
        <div><h2>Browse tutoring opportunities</h2><p className="muted">Switch the view to see all listings, tutor offers, or student requests.</p></div>
        <div className="post-filters" role="group" aria-label="Filter posts">
          <button type="button" className={filter === "all" ? "button primary" : "button secondary"} onClick={() => setFilter("all")}>All</button>
          <button type="button" className={filter === "tutor" ? "button primary" : "button secondary"} onClick={() => setFilter("tutor")}>Tutor</button>
          <button type="button" className={filter === "student" ? "button primary" : "button secondary"} onClick={() => setFilter("student")}>Student</button>
        </div>
      </div>
      {loading ? <p className="muted">Loading posts…</p> : visiblePosts.length === 0 ? <div className="empty-state"><h3>No posts found</h3><p>Choose another filter or publish the first post using the form below.</p></div> :
        <div className="profile-list">{visiblePosts.map(p => <article className="profile-card" key={p.id}>
          <div className={p.post_type === "student" ? "avatar student-avatar" : "avatar"}>{p.author_name.charAt(0).toUpperCase()}</div>
          <div className="profile-info">
            <p className="eyebrow">{p.post_type === "tutor" ? "TUTOR OFFER" : "STUDENT REQUEST"}</p>
            <h3>{p.subject} · {p.level}</h3><p>Posted by {p.author_name}</p>
            <p className="muted">{p.availability || "Schedule flexible"} · {p.location || "Location not specified"}</p>
            <p>{p.description}</p><p><strong>৳{p.fee}</strong> · <strong className={p.status === "Accepted" || p.status === "Completed" ? "task-status" : ""}>{p.status}</strong></p>
            {p.experience && <p className="muted">Experience / goals: {p.experience}</p>}
            <p className="muted">{p.post_type === "tutor" ? "Student acceptance" : "Tutor acceptance"}: {(p.post_type === "tutor" ? p.student_confirmed : p.tutor_confirmed) ? "accepted" : "waiting"}</p>
            <div className="card-actions">
              <button className="small-button" type="button" onClick={() => { setForm({author_name:p.author_name,subject:p.subject,level:p.level,experience:p.experience,availability:p.availability,location:p.location,fee:String(p.fee),description:p.description}); setPostKind(p.post_type); setEditId(p.id); document.getElementById("post-form")?.scrollIntoView({behavior:"smooth",block:"start"}); }}>Edit</button>
              {p.status === "Pending" && <button className="small-button" type="button" onClick={() => void action(p,"confirm")}>{p.post_type === "tutor" ? "Accept offer as Student" : "Accept request as Tutor"}</button>}
              {p.status === "Pending" && <button className="small-button danger-text" type="button" onClick={() => void action(p,"withdraw")}>Withdraw</button>}
              <button className="small-button danger-text" type="button" onClick={() => void deletePost(p.id)}>Delete</button>
              <a className="text-link" href={"/task-details?id=" + p.id}>Task details</a>
            </div>
          </div>
        </article>)}</div>}
      {!loading && visiblePosts.length > 0 && <div className="card-actions pagination-actions"><p className="muted">Showing {visiblePosts.length} listings (maximum {maxPosts} loaded).</p>{hasMore && posts.length < maxPosts && <button className="button secondary" type="button" disabled={loadingMore} onClick={() => { setLoadingMore(true); void load(false); }}>{loadingMore ? "Loading…" : "Load More"}</button>}</div>}
    </section>
    <section className="panel form-panel posts-form-panel" id="post-form">
      <h2>{editId === null ? "Create a listing" : "Edit listing"}</h2>
      <p className="muted">Choose Tutor to offer teaching, or Student to request tutoring. The selected role determines who can accept the listing.</p>
      <div className="post-kind-switch" role="group" aria-label="Post type">
        <button type="button" className={postKind === "tutor" ? "button primary" : "button secondary"} disabled={editId !== null} onClick={() => setPostKind("tutor")}>Create as Tutor</button>
        <button type="button" className={postKind === "student" ? "button primary" : "button secondary"} disabled={editId !== null} onClick={() => setPostKind("student")}>Create as Student</button>
      </div>
      <form className="profile-form" onSubmit={submit}>
        {([{name:"author_name",label:"Your name"},{name:"subject",label:postKind === "tutor" ? "Subject you teach" : "Subject needed"},{name:"level",label:"Teaching / learning level"},{name:"experience",label:postKind === "tutor" ? "Teaching experience" : "Learning goals / requirements"},{name:"availability",label:"Preferred days and times"},{name:"location",label:"Teaching / learning location"},{name:"fee",label:postKind === "tutor" ? "Expected fee (৳)" : "Budget (৳)",type:"number"},{name:"description",label:"Description",type:"textarea"}] as Field[]).map(f => <label className="field" key={f.name}>{f.label}{f.type === "textarea" ? <textarea value={form[f.name] ?? ""} rows={4} maxLength={4000} onChange={e => setForm({...form,[f.name]:e.target.value})}/> : <input required={["author_name","subject","level","fee"].includes(f.name)} type={f.type ?? "text"} value={form[f.name] ?? ""} min={f.type === "number" ? 0 : undefined} onChange={e => setForm({...form,[f.name]:e.target.value})}/>}</label>)}
        <div className="actions"><button className="button primary" disabled={busy} type="submit">{busy ? "Saving…" : editId === null ? "Publish post" : "Save changes"}</button>{editId !== null && <button className="button secondary" type="button" onClick={resetForm}>Cancel</button>}</div>
      </form>
    </section>
  </Layout>;
}

function RequestDetailsPage() {
  const id = new URLSearchParams(window.location.search).get("id");
  const [post,setPost] = useState<LearningPost|null>(null);
  const [form,setForm] = useState<Record<string,string>>(emptyPost);
  const [editing,setEditing] = useState(new URLSearchParams(window.location.search).get("edit") === "1");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");

  async function loadPost() {
    if (!id) { setError("Choose a task to view its details."); return; }
    try {
      const result = await api<LearningPost>("/api/posts/" + id);
      setPost(result);
      setForm({author_name:result.author_name,subject:result.subject,level:result.level,experience:result.experience,availability:result.availability,location:result.location,fee:String(result.fee),description:result.description});
      setError("");
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not load task details.");
    }
  }

  useEffect(() => { void loadPost(); }, [id]);

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!post) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const updated = await api<LearningPost>("/api/posts/" + post.id, {
        method:"PUT",
        body:JSON.stringify({...form,post_type:post.post_type,fee:Number(form.fee)})
      });
      setPost(updated); setEditing(false); setNotice("Task details updated and saved.");
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not update task.");
    } finally { setBusy(false); }
  }

  async function confirmInterest() {
    if (!post) return;
    setBusy(true); setError(""); setNotice("");
    const actor = post.post_type === "tutor" ? "student" : "tutor";
    try {
      const updated = await api<LearningPost>("/api/posts/" + post.id + "/confirm", {
        method:"POST",body:JSON.stringify({actor})
      });
      setPost(updated);
      setNotice(actor === "student" ? "Tutor offer accepted as a student." : "Student request accepted as a tutor.");
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not accept this task.");
    } finally { setBusy(false); }
  }

  async function deleteTask() {
    if (!post || !window.confirm("Delete this task permanently? This cannot be undone.")) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await api<void>("/api/posts/" + post.id,{method:"DELETE"});
      window.location.href = "/task-details";
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not delete task.");
      setBusy(false);
    }
  }

  return <Layout>
    <a className="text-link back-link" href="/task-details">← Back to Task Details</a>
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    {!post ? !error && <p className="muted">Loading task details…</p> : <section className="detail-card task-detail-card">
      <div className="task-detail-header">
        <div className="task-icon" aria-hidden="true">{post.post_type === "tutor" ? "T" : "S"}</div>
        <div><p className="eyebrow">TASK DETAILS · #{post.id}</p><h2>{post.subject} · {post.level}</h2><p className="muted">{post.post_type === "tutor" ? "Tutor offer" : "Student request"}</p></div>
      </div>
      {!editing ? <>
        <div className="task-meta-grid">
          <div><span>Posted by</span><strong>{post.author_name}</strong></div>
          <div><span>Fee / budget</span><strong>৳{post.fee}</strong></div>
          <div><span>Availability</span><strong>{post.availability || "Flexible"}</strong></div>
          <div><span>Location</span><strong>{post.location || "Not specified"}</strong></div>
        </div>
        <section className="task-description"><h2>Description</h2><p>{post.description || "No additional description provided."}</p></section>
        {post.experience && <section className="task-section"><h2>{post.post_type === "tutor" ? "Teaching experience" : "Learning goals / requirements"}</h2><p>{post.experience}</p></section>}
        <section className="task-section"><h2>Task status</h2><p><strong className={post.status === "Accepted" || post.status === "Completed" ? "task-status" : ""}>{post.status}</strong></p>
          <div className="task-confirmations">
            <p>{post.post_type === "tutor" ? "Student acceptance" : "Tutor acceptance"}: <strong>{(post.post_type === "tutor" ? post.student_confirmed : post.tutor_confirmed) ? "Accepted" : "Pending"}</strong></p>
          </div>
          <p className="muted">{post.post_type === "tutor" ? "A student accepts this tutor offer." : "A tutor accepts this student request."} Once accepted, the status changes from Pending to Accepted.</p>
          {post.status === "Pending" && <div className="task-confirm-controls">
            <button className="button primary" type="button" disabled={busy} onClick={() => void confirmInterest()}>{busy ? "Saving…" : post.post_type === "tutor" ? "Accept offer as Student" : "Accept request as Tutor"}</button>
          </div>}
        </section>
        <div className="actions task-actions">
          <button className="button primary" type="button" disabled={busy || post.status === "Accepted" || post.status === "Completed"} onClick={() => setEditing(true)}>Edit task</button>
          <button className="button secondary" type="button" disabled={busy} onClick={() => void deleteTask()}>Delete task</button>
          <a className="button secondary" href="/posts">Browse Tutoring Hub</a>
        </div>
      </> : <>
        <h2>Edit task</h2>
        <form className="profile-form task-edit-form" onSubmit={save}>
          {([{name:"author_name",label:"Posted by"},{name:"subject",label:"Subject"},{name:"level",label:"Teaching / learning level"},{name:"experience",label:post.post_type === "tutor" ? "Teaching experience" : "Learning goals / requirements"},{name:"availability",label:"Availability"},{name:"location",label:"Location"},{name:"fee",label:post.post_type === "tutor" ? "Fee (৳)" : "Budget (৳)",type:"number"},{name:"description",label:"Description",type:"textarea"}] as Field[]).map(f => <label className="field" key={f.name}>{f.label}{f.type === "textarea" ? <textarea rows={4} maxLength={4000} value={form[f.name] ?? ""} onChange={e => setForm({...form,[f.name]:e.target.value})}/> : <input required={["author_name","subject","level","fee"].includes(f.name)} type={f.type ?? "text"} min={f.type === "number" ? 0 : undefined} value={form[f.name] ?? ""} onChange={e => setForm({...form,[f.name]:e.target.value})}/>}</label>)}
          <div className="actions"><button className="button primary" disabled={busy} type="submit">{busy ? "Saving…" : "Save task"}</button><button className="button secondary" type="button" disabled={busy} onClick={() => { setEditing(false); setError(""); void loadPost(); }}>Cancel</button></div>
        </form>
      </>}
    </section>}
  </Layout>;
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
  if (path === "/posts") return <LearningPostsPage />
  if (path === "/tutors") return <ProfileManager kind="tutor" />
  if (path === "/students") return <ProfileManager kind="student" />
  const tutorMatch = path.match(/^\/tutors\/(\d+)$/)
  if (tutorMatch) return <DetailPage kind="tutor" id={Number(tutorMatch[1])} />
  const studentMatch = path.match(/^\/students\/(\d+)$/)
  if (studentMatch) return <DetailPage kind="student" id={Number(studentMatch[1])} />
  return <Layout><section className="empty-state"><h1>Page not found</h1><p>The page you're looking for doesn't exist.</p><a className="button primary" href="/">Back home</a></section></Layout>
}
