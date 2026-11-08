import { useEffect, useState } from "react"
import { Layout } from "../components/Layout"
import { CurrentRoleSelector } from "../components/CurrentRoleSelector"
import { approvePost, listPosts, rejectPost } from "../services/api"
import { isInterested, readCurrentRole } from "../services/session"
import type { CurrentRole, LearningPost } from "../types"

export default function TaskDetailsPage() {
  const [posts, setPosts] = useState<LearningPost[]>([]);
  const [currentRole, setCurrentRole] = useState<CurrentRole>(readCurrentRole);
  function changeRole(role: CurrentRole) { window.localStorage.setItem("tutorinn-role", role); setCurrentRole(role); }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    listPosts(0, 20)
      .then(setPosts)
      .catch(e => setError(e instanceof Error ? e.message : "Could not load tasks."))
      .finally(() => setLoading(false));
  }, []);
  const taskPosts = posts.filter(post => currentRole === "admin"
    ? post.status === "Pending" && isInterested(post, "admin")
    : post.post_type !== currentRole && isInterested(post, currentRole));
  return <Layout>
    <section className="page-intro compact"><p className="eyebrow">TASK DETAILS</p><h1>{currentRole === "admin" ? "Admin review queue" : "Your interest requests"}</h1><p>{currentRole === "admin" ? "Review interested listings. Only an Admin API key configured on the backend can approve or reject a request." : "Track listings you marked Interested. Accepting or rejecting is reserved for Admin; you can mark an opposite-role listing Interested or Not interested here."}</p><CurrentRoleSelector role={currentRole} onChange={changeRole} /></section>
    {error && <div className="alert error" role="alert">{error}</div>}
    {loading ? <p className="muted">Loading tasks…</p> : taskPosts.length === 0 ? <div className="empty-state"><h2>{currentRole === "admin" ? "No interested requests to review" : "No interest requests yet"}</h2><p>{currentRole === "admin" ? "When a Student or Tutor marks a listing Interested, it will appear here." : "Open a listing in Tutoring Hub and choose Interested to track it here."}</p><a className="button primary" href="/posts">Browse Tutoring Hub</a></div> :
      <section className="panel list-panel">
        <div className="panel-heading"><div><h2>{currentRole === "admin" ? "Pending Admin decisions" : "Interest status"}</h2><p>CRUD remains available from Tutoring Hub and the details view.</p></div></div>
        <div className="profile-list">{taskPosts.map(post => <article className="profile-card" key={post.id}>
          <div className={post.post_type === "student" ? "avatar student-avatar" : "avatar"}>{post.post_type === "tutor" ? "T" : "S"}</div>
          <div className="profile-info"><h3>{post.subject} · {post.level}</h3><p>{post.post_type === "tutor" ? "Tutor offer" : "Student request"} · {post.status}</p>
            <p><strong>Student response:</strong> {post.student_response} · <strong>Tutor response:</strong> {post.tutor_response}</p>
            <div className="card-actions"><a className="text-link" href={"/task-details?id=" + post.id}> <span aria-hidden="true">👁</span> View details</a>{currentRole === "admin" && post.status === "Pending" && <><button className="small-button" type="button" onClick={async () => { try { const updated = await approvePost(post.id); setPosts(old => old.map(p => p.id === updated.id ? updated : p)); setError(""); } catch(e) { setError(e instanceof Error ? e.message : "Could not approve request."); } }}>Approve</button><button className="small-button danger-text" type="button" onClick={async () => { try { const updated = await rejectPost(post.id); setPosts(old => old.map(p => p.id === updated.id ? updated : p)); setError(""); } catch(e) { setError(e instanceof Error ? e.message : "Could not reject request."); } }}>Reject</button></>}</div>
          </div>
        </article>)}</div>
      </section>}
  </Layout>;
}
