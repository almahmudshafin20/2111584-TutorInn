import { useEffect, useState } from "react"
import { api, getAdminHeaders, Layout } from "../shared"
type Candidate = {
 response:{id:number;post_id:number;profile_id:number;profile_type:"student"|"tutor";response:string;review_status:string;created_at:string;updated_at:string}
 post:{id:number;post_type:string;author_name:string;subjects:string[];level:string;experience:string;availability:string;location:string;fee:number;description:string;status:string}
 tutor:null|{id:number;full_name:string;email:string;subjects:string[];teaching_level:string;experience_years:number;hourly_rate:number;bio:string}
 student:null|{id:number;full_name:string;email:string;education_level:string;subjects:string[]}
}
export default function AdminReviewPage(){
 const [matches,setMatches]=useState<Candidate[]>([]),[error,setError]=useState(""),[notice,setNotice]=useState(""),[loading,setLoading]=useState(false)
 async function load(){setLoading(true);setError("");try{setMatches(await api<Candidate[]>("/api/admin/matches?review_status=Pending",{headers:getAdminHeaders()}))}catch(e){setError(e instanceof Error?e.message:"Could not load admin queue.")}finally{setLoading(false)}}
 async function decide(id:number,decision:"approve"|"reject"){try{await api("/api/responses/"+id+"/"+decision,{method:"POST",headers:getAdminHeaders()});setNotice("This tutor–student candidate was "+(decision==="approve"?"approved.":"rejected."));await load()}catch(e){setError(e instanceof Error?e.message:"Could not update match.")}}
 useEffect(()=>{void load()},[])
 return <Layout><section className="page-intro compact"><p className="eyebrow">ADMIN</p><h1>Tutor–student match review</h1><p>Review the post and both complete profiles before deciding on each individual candidate. Contact emails are visible only in this admin-key-protected view.</p></section>
 {error&&<div className="alert error">{error}</div>}{notice&&<div className="alert success">{notice}</div>}
 {loading?<p className="muted">Loading review queue…</p>:matches.length===0?<div className="empty-state"><p>No pending Interested matches.</p><button className="button secondary" onClick={()=>void load()}>Refresh</button></div>:<section className="panel"><div className="profile-list">{matches.map(m=><article className="profile-card" key={m.response.id}><div className="profile-info">
 <p className="eyebrow">PENDING MATCH · RESPONSE #{m.response.id} · POST #{m.post.id}</p><h2>{m.post.subjects.join(" · ")||"Tutoring opportunity"}</h2><p>{m.response.profile_type} profile #{m.response.profile_id} expressed interest.</p>
 <h3>Original post</h3><p><strong>{m.post.post_type==="tutor"?"Tutor offer":"Student request"}</strong> · Posted by {m.post.author_name} · {m.post.level}</p><p>{m.post.description||"No description provided."}</p><p>Experience / requirements: {m.post.experience||"Not specified"}</p><p>Availability: {m.post.availability||"Not specified"} · Location: {m.post.location||"Not specified"}</p><p>Fee / budget: ৳{m.post.fee}</p>
 <div className="detail-stats"><div><strong>TUTOR</strong><span>{m.tutor?.full_name||"Tutor profile unavailable"}</span><span>{m.tutor?.email||"No tutor email available"}</span><span>{m.tutor?.subjects.join(", ")||"—"}</span><span>{m.tutor?.teaching_level||"—"} · {m.tutor?.experience_years??0} years</span><span>৳{m.tutor?.hourly_rate??"—"}/hour</span><span>{m.tutor?.bio||""}</span></div><div><strong>STUDENT</strong><span>{m.student?.full_name||"Student profile unavailable"}</span><span>{m.student?.email||"No student email available"}</span><span>{m.student?.subjects.join(", ")||"—"}</span><span>{m.student?.education_level||"—"}</span></div></div>
 <p className="notice">Participant contact release is intentionally disabled: the current demo profile selector is not verified authentication. Approval here does not expose private details to participants.</p>
 <div className="card-actions"><button className="button primary" onClick={()=>void decide(m.response.id,"approve")}>Approve this pair</button><button className="button secondary danger-text" onClick={()=>void decide(m.response.id,"reject")}>Reject this pair</button><a className="text-link" href={"/task-details?id="+m.post.id}>Open post</a></div>
 </div></article>)}</div></section>}
 </Layout>
}
