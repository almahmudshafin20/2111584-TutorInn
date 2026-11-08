import { useEffect, useState } from "react"
import { Layout } from "../components/Layout"
import { CurrentRoleSelector } from "../components/CurrentRoleSelector"
import { api } from "../services/api"
import { readCurrentRole } from "../services/session"
import { emptyPost } from "../types/forms"
import type { CurrentRole, LearningPost } from "../types"

export default function RequestDetailsPage() {
  const id = new URLSearchParams(window.location.search).get("id");
  const [post,setPost] = useState<LearningPost|null>(null);
  const [currentRole, setCurrentRole] = useState<CurrentRole>(readCurrentRole);
  function changeRole(role: CurrentRole) { window.localStorage.setItem("tutorinn-role", role); setCurrentRole(role); }
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

  const canSeeFullDetails = Boolean(post) && (
    currentRole === "admin" ||
    post!.post_type === currentRole ||
    (currentRole === "student" && post!.post_type === "tutor" && post!.student_confirmed) ||
    (currentRole === "tutor" && post!.post_type === "student" && post!.tutor_confirmed)
  );

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!post) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const updated = await api<LearningPost>("/api/posts/" + post.id, {
        method:"PUT",
        body:JSON.stringify({...Object.fromEntries(Object.entries(form).map(([key,value]) => [key,value.trim()])),post_type:post.post_type,fee:Number(form.fee)})
      });
      setPost(updated); setEditing(false); setNotice("Task details updated and saved.");
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not update task.");
    } finally { setBusy(false); }
  }

  async function confirmInterest(actor: "student" | "tutor") {
    if (!post) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const updated = await api<LearningPost>("/api/posts/" + post.id + "/confirm", {
        method:"POST",body:JSON.stringify({actor})
      });
      setPost(updated);
      setNotice("Interest saved. The listing remains pending until Admin approval.");
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not confirm interest.");
    } finally { setBusy(false); }
  }

  async function rejectInterest() {
    if (!post || !window.confirm("Mark this opportunity as not interested?")) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const updated = await api<LearningPost>("/api/posts/" + post.id + "/not-interested", { method:"POST", body:JSON.stringify({actor:currentRole}) });
      setPost(updated);
      setNotice("Marked not interested. The listing remains available to others.");
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not reject this task.");
    } finally { setBusy(false); }
  }

  async function approveTask() {
    if (!post) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const updated = await api<LearningPost>("/api/posts/" + post.id + "/approve", {method:"POST",headers:getAdminHeaders()});
      setPost(updated); setNotice("Request approved by Admin.");
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not approve this task.");
    } finally { setBusy(false); }
  }

  async function rejectTaskAsAdmin() {
    if (!post || !window.confirm("Reject this request as Admin?")) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const updated = await api<LearningPost>("/api/posts/" + post.id + "/reject", {method:"POST",headers:getAdminHeaders()});
      setPost(updated); setNotice("Request rejected by Admin.");
    } catch(e) {
      setError(e instanceof Error ? e.message : "Could not reject this task.");
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
          {canSeeFullDetails && <>
            <div><span>Fee / budget</span><strong>৳{post.fee}</strong></div>
            <div><span>Availability</span><strong>{post.availability || "Flexible"}</strong></div>
            <div><span>Location</span><strong>{post.location || "Not specified"}</strong></div>
          </>}
        </div>
        <section className="task-description"><h2>Description</h2><p>{canSeeFullDetails ? (post.description || "No additional description provided.") : (post.description ? post.description.slice(0, 220) + (post.description.length > 220 ? "…" : "") : "No additional description provided.")}</p></section>
        {!canSeeFullDetails && currentRole !== "admin" && post.post_type !== currentRole && post.status === "Pending" && <p className="notice">Mark this listing Interested to reveal the remaining listing details. Contact information stays private.</p>}
        {canSeeFullDetails && post.experience && <section className="task-section"><h2>{post.post_type === "tutor" ? "Teaching experience" : "Learning goals / requirements"}</h2><p>{post.experience}</p></section>}
        <section className="task-section"><h2>Task status</h2><p><strong className={post.status === "Accepted" || post.status === "Completed" ? "task-status" : ""}>{post.status}</strong></p>
          <div className="task-confirmations">
            <p>Interest response from {post.post_type === "tutor" ? "Student" : "Tutor"}: <strong>{post.post_type === "tutor" ? post.student_response : post.tutor_response}</strong></p>
            <p>{post.post_type === "tutor" ? "Tutor offer" : "Student request"} status: <strong>{post.status}</strong></p>
          </div>
          <p className="muted">{post.post_type === "tutor" ? "Students may express interest in this tutor offer." : "Tutors may express interest in this student request."} Only Admin can approve or reject. Contact information is not shown in public listing details.</p>
          <CurrentRoleSelector role={currentRole} onChange={changeRole} />
          {currentRole !== "admin" && post.status === "Pending" && post.post_type !== currentRole && <div className="task-confirm-controls">
            <button className="button primary" type="button" disabled={busy} onClick={() => void confirmInterest(currentRole)}>Interested</button>
            <button className="button secondary danger-text" type="button" disabled={busy} onClick={() => void rejectInterest()}>Not interested</button>
          </div>}
          {currentRole === "admin" && post.status === "Pending" && <div className="task-confirm-controls">
            <button className="button primary" type="button" disabled={busy} onClick={() => void approveTask()}>Approve request</button>
            <button className="button secondary danger-text" type="button" disabled={busy} onClick={() => void rejectTaskAsAdmin()}>Reject request</button>
          </div>}
          {currentRole !== "admin" && post.post_type === currentRole && <p className="muted">You can review your own listing and manage it with Edit or Delete. Only the opposite role can express interest.</p>}
        </section>
        <div className="actions task-actions">
          {currentRole !== "admin" && post.post_type === currentRole && <><button className="button primary" type="button" disabled={busy || post.status === "Accepted" || post.status === "Completed"} onClick={() => setEditing(true)}>Edit task</button>
          <button className="button secondary" type="button" disabled={busy} onClick={() => void deleteTask()}>Delete task</button></>}
          <a className="button secondary" href="/posts">Browse Tutoring Hub</a>
        </div>
      </> : <>
        <h2>Edit task</h2>
        <form className="profile-form task-edit-form" onSubmit={save}>
          {([{name:"author_name",label:"Posted by",minLength:2,maxLength:120},{name:"subject",label:"Subject",minLength:2,maxLength:120},{name:"level",label:"Teaching / learning level",minLength:1,maxLength:80},{name:"experience",label:post.post_type === "tutor" ? "Teaching experience" : "Learning goals / requirements",maxLength:500},{name:"availability",label:"Availability",maxLength:255},{name:"location",label:"Location",maxLength:255},{name:"fee",label:post.post_type === "tutor" ? "Fee (৳)" : "Budget (৳)",type:"number",min:0,max:1000000},{name:"description",label:"Description",type:"textarea",maxLength:4000}] as (Field & {minLength?:number;maxLength?:number;min?:number;max?:number})[]).map(f => <label className="field" key={f.name}>{f.label}{f.type === "textarea" ? <textarea rows={4} maxLength={f.maxLength} value={form[f.name] ?? ""} onChange={e => setForm({...form,[f.name]:e.target.value})}/> : <input required={["author_name","subject","level","fee"].includes(f.name)} type={f.type ?? "text"} min={f.min} max={f.max} minLength={f.minLength} maxLength={f.maxLength} value={form[f.name] ?? ""} onChange={e => setForm({...form,[f.name]:e.target.value})}/>}</label>)}
          <div className="actions"><button className="button primary" disabled={busy} type="submit">{busy ? "Saving…" : "Save task"}</button><button className="button secondary" type="button" disabled={busy} onClick={() => { setEditing(false); setError(""); void loadPost(); }}>Cancel</button></div>
        </form>
      </>}
    </section>}
  </Layout>;
}
