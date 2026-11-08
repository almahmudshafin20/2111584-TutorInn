import { useEffect, useState } from "react"
import type { FormEvent } from "react"
import { Layout } from "../components/Layout"
import { CurrentRoleSelector } from "../components/CurrentRoleSelector"
import { api } from "../services/api"
import { isInterested, readCurrentRole } from "../services/session"
import type { Field } from "../types"
import { emptyPost } from "../types/forms"
import type { CurrentRole, LearningPost } from "../types"

export default function LearningPostsPage() {
  const endpoint = "/api/posts";
  const [posts, setPosts] = useState<LearningPost[]>([]);
  const [form, setForm] = useState<Record<string,string>>(emptyPost);
  const [editId, setEditId] = useState<number | null>(null);
  const [postKind, setPostKind] = useState<"tutor" | "student">(() => readCurrentRole() === "student" ? "student" : "tutor");
  const [currentRole, setCurrentRole] = useState<CurrentRole>(readCurrentRole);
  function changeRole(role: CurrentRole) {
    window.localStorage.setItem("tutorinn-role", role);
    setCurrentRole(role);
    setPostKind(role === "student" ? "student" : "tutor");
    resetForm();
  }
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
    if (currentRole === "admin") {
      setError("Admin cannot create Student or Tutor listings.");
      setBusy(false);
      return;
    }
    if (editId !== null && posts.find(post => post.id === editId)?.post_type !== currentRole) {
      setError("You can only edit listings for your current role.");
      setBusy(false);
      return;
    }
    const cleanedForm = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value.trim()]));
    const payload = { ...cleanedForm, post_type: currentRole, fee: Number(form.fee) };
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

  async function action(post: LearningPost, actionName: "confirm" | "not-interested") {
    if (currentRole === "admin" || post.post_type === currentRole) {
      setError("You can express interest only in posts created for the opposite role.");
      return;
    }
    setError(""); setNotice("");
    try {
      const updated = await api<LearningPost>(endpoint + "/" + post.id + "/" + actionName, {
        method: "POST",
        body: JSON.stringify({ actor: currentRole }),
      });
      setPosts(old => old.map(p => p.id === post.id ? updated : p));
      setNotice(actionName === "confirm" ? "Interest saved. Admin approval is still required." : "Marked not interested.");
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
    <section className="page-intro compact"><p className="eyebrow">TUTORINN COMMUNITY</p><h1>Tutoring Hub</h1><p>Create a tutor offer or a student request, then browse both types together in one place.</p><CurrentRoleSelector role={currentRole} onChange={changeRole} /></section>
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
            <p className="muted">{p.post_type === "tutor" ? "Tutor offer" : "Student request"} · {p.status}</p>
            <p className="muted">Fee / budget: ৳{p.fee} · {p.location || "Location not specified"}</p>
            <div className="card-actions">
              <a className="small-button view-details-button" aria-label={"View details for " + p.subject} title="View details" href={"/task-details?id=" + p.id}><span aria-hidden="true">👁</span> View details</a>
              {currentRole !== "admin" && p.post_type === currentRole && <button className="small-button" type="button" onClick={() => { setForm({author_name:p.author_name,subject:p.subject,level:p.level,experience:p.experience,availability:p.availability,location:p.location,fee:String(p.fee),description:p.description}); setPostKind(currentRole); setEditId(p.id); document.getElementById("post-form")?.scrollIntoView({behavior:"smooth",block:"start"}); }}>Edit</button>}
              {currentRole !== "admin" && p.status === "Pending" && p.post_type !== currentRole && <button className="small-button" type="button" onClick={() => void action(p,"confirm")}>Interested</button>}
              {currentRole !== "admin" && p.status === "Pending" && p.post_type !== currentRole && <button className="small-button danger-text" type="button" onClick={() => void action(p,"not-interested")}>Not interested</button>}
              {currentRole === "admin" && p.status === "Pending" && isInterested(p, "admin") && <a className="small-button" href={"/task-details?id=" + p.id}>Review request</a>}
              {currentRole !== "admin" && p.post_type === currentRole && <button className="small-button danger-text" type="button" onClick={() => void deletePost(p.id)}>Delete</button>}
            </div>
          </div>
        </article>)}</div>}
      {!loading && visiblePosts.length > 0 && <div className="card-actions pagination-actions"><p className="muted">Showing {visiblePosts.length} listings (maximum {maxPosts} loaded).</p>{hasMore && posts.length < maxPosts && <button className="button secondary" type="button" disabled={loadingMore} onClick={() => { setLoadingMore(true); void load(false); }}>{loadingMore ? "Loading…" : "Load More"}</button>}</div>}
    </section>
    {currentRole !== "admin" && <section className="panel form-panel posts-form-panel" id="post-form">
      <h2>{editId === null ? "Create a listing" : "Edit listing"}</h2>
      <p className="muted">{currentRole === "student" ? "Create student learning requests. You can browse all listings and express interest in tutor offers." : currentRole === "tutor" ? "Create tutor offers. You can browse all listings and express interest in student requests." : "Admin reviews requests and cannot create Student or Tutor listings."} CRUD remains available for listings belonging to your current role. Interested requests require Admin approval.</p>
      <div className="post-kind-switch" role="group" aria-label="Post type">
        <span className="muted">Creating as {currentRole === "student" ? "Student" : currentRole === "tutor" ? "Tutor" : "Admin"}</span>
      </div>
      <form className="profile-form" onSubmit={submit}>
        {([{name:"author_name",label:"Your name",minLength:2,maxLength:120},{name:"subject",label:postKind === "tutor" ? "Subject you teach" : "Subject needed",minLength:2,maxLength:120},{name:"level",label:"Teaching / learning level",minLength:1,maxLength:80},{name:"experience",label:postKind === "tutor" ? "Teaching experience" : "Learning goals / requirements",maxLength:500},{name:"availability",label:"Preferred days and times",maxLength:255},{name:"location",label:"Teaching / learning location",maxLength:255},{name:"fee",label:postKind === "tutor" ? "Expected fee (৳)" : "Budget (৳)",type:"number",min:0,max:1000000},{name:"description",label:"Description",type:"textarea",maxLength:4000}] as (Field & {minLength?:number;maxLength?:number;min?:number;max?:number})[]).map(f => <label className="field" key={f.name}>{f.label}{f.type === "textarea" ? <textarea value={form[f.name] ?? ""} rows={4} maxLength={f.maxLength} onChange={e => setForm({...form,[f.name]:e.target.value})}/> : <input required={["author_name","subject","level","fee"].includes(f.name)} type={f.type ?? "text"} value={form[f.name] ?? ""} min={f.min} max={f.max} minLength={f.minLength} maxLength={f.maxLength} onChange={e => setForm({...form,[f.name]:e.target.value})}/>}</label>)}
        <div className="actions"><button className="button primary" disabled={busy} type="submit">{busy ? "Saving…" : editId === null ? "Publish post" : "Save changes"}</button>{editId !== null && <button className="button secondary" type="button" onClick={resetForm}>Cancel</button>}</div>
      </form>
    </section>}
  </Layout>;
}
