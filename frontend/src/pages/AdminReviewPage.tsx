import { useEffect, useState } from "react"
import { decideAdminMatch, listPendingAdminMatches } from "../services/admin"
import { AppLayout as Layout } from "../layouts/AppLayout"
import type { AdminCandidate } from "../types/domain"

export default function AdminReviewPage(){
 const [matches,setMatches]=useState<AdminCandidate[]>([]),[error,setError]=useState(""),[notice,setNotice]=useState(""),[loading,setLoading]=useState(false)
 async function load(){setLoading(true);setError("");try{setMatches(await listPendingAdminMatches())}catch(e){setError(e instanceof Error?e.message:"Could not load admin queue.")}finally{setLoading(false)}}
 async function decide(id:number,decision:"approve"|"reject"){try{await decideAdminMatch(id,decision);setNotice("This tutor–student candidate was "+(decision==="approve"?"approved.":"rejected."));await load()}catch(e){setError(e instanceof Error?e.message:"Could not update match.")}}
 useEffect(()=>{void load()},[])
 return <Layout><section className="page-intro compact"><p className="eyebrow">ADMIN</p><h1>Tutor–student match review</h1><p>Review each original post and both complete profiles. Contact either participant directly before approving or rejecting this individual match.</p></section>
 {error&&<div className="alert error">{error}</div>}{notice&&<div className="alert success">{notice}</div>}
 {loading?<p className="muted">Loading review queue…</p>:matches.length===0?<div className="empty-state"><p>No pending Interested matches.</p><button className="button secondary" onClick={()=>void load()}>Refresh</button></div>:<section className="panel"><div className="profile-list">{matches.map(m=><article className="profile-card" key={m.response.id}><div className="profile-info">
 <p className="eyebrow">PENDING MATCH · RESPONSE #{m.response.id} · POST #{m.post.id}</p><h2>{m.post.subjects.join(" · ")||"Tutoring opportunity"}</h2><p>{m.response.profile_type} profile #{m.response.profile_id} expressed interest.</p>
 <h3>Original post</h3><p><strong>{m.post.post_type==="tutor"?"Tutor offer":"Student request"}</strong> · Posted by {m.post.author_name} · {m.post.level}</p><p>{m.post.description||"No description provided."}</p><p>Experience / requirements: {m.post.experience||"Not specified"}</p><p>Availability: {m.post.availability||"Not specified"} · Location: {m.post.location||"Not specified"}</p><p>Fee / budget: ৳{m.post.fee}</p>
 <div className="detail-stats"><div><strong>TUTOR</strong><span>{m.tutor?.full_name||"Tutor profile unavailable"}</span><span>{m.tutor?.email||"No tutor email available"}</span><span>{m.tutor?.phone_number||"No phone number available"}</span><span>{m.tutor?.subjects.join(", ")||"—"}</span><span>{m.tutor?.teaching_level||"—"} · {m.tutor?.experience_years??0} years</span><span>৳{m.tutor?.hourly_rate??"—"}/hour</span><span>{m.tutor?.bio||""}</span>{m.tutor?.email&&<a href={`mailto:${m.tutor.email}`}>Email tutor</a>}{m.tutor?.phone_number&&<a href={`tel:${m.tutor.phone_number}`}>Call tutor</a>}</div><div><strong>STUDENT</strong><span>{m.student?.full_name||"Student profile unavailable"}</span><span>{m.student?.email||"No student email available"}</span><span>{m.student?.phone_number||"No phone number available"}</span><span>{m.student?.subjects.join(", ")||"—"}</span><span>{m.student?.education_level||"—"}</span>{m.student?.email&&<a href={`mailto:${m.student.email}`}>Email student</a>}{m.student?.phone_number&&<a href={`tel:${m.student.phone_number}`}>Call student</a>}</div></div>
 <p className="notice">After approval, the two matched profiles will see each other's contact details in their approved matches section. This demo uses the selected profile switcher, not verified sign-in.</p>
 <div className="card-actions"><button className="button primary" onClick={()=>void decide(m.response.id,"approve")}>Approve this pair</button><button className="button secondary danger-text" onClick={()=>void decide(m.response.id,"reject")}>Reject this pair</button><a className="text-link" href={"/task-details?id="+m.post.id}>Open post</a></div>
 </div></article>)}</div></section>}
 </Layout>
}
