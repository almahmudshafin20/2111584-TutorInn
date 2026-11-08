import { useEffect, useMemo, useState } from "react"
import type { FormEvent } from "react"
import { api, emptyPost, emptyStudent, emptyTutor, getAdminHeaders, Layout, saveSelectedProfile, selectedProfile, SubjectPicker, useSelectedProfile, type ProfileType, type Student, type Tutor, type Profile, type LearningPost, type InterestResponse, type SelectedProfile } from "../shared"
export default function RequestDetailsPage(){
  const id=new URLSearchParams(window.location.search).get("id")
  const [post,setPost]=useState<LearningPost|null>(null),[responses,setResponses]=useState<InterestResponse[]>([])
  const [error,setError]=useState(""),[notice,setNotice]=useState("")
  const active=useSelectedProfile()
  async function load(){if(!id)return;try{const p=await api<LearningPost>("/api/posts/"+id);setPost(p);if(active)setResponses(await api<InterestResponse[]>("/api/responses"))}catch(e){setError(e instanceof Error?e.message:"Could not load post.")}}
  useEffect(()=>{void load()},[id,active?.id,active?.type])
  const own=Boolean(active&&post&&post.author_profile_id===active.id&&post.author_profile_type===active.type)
  const myResponse=responses.find(r=>r.post_id===Number(id))
  const canSeeFullDetails=own||myResponse?.response==="Interested"
  async function respond(response:"Interested"|"Not Interested"){try{await api("/api/posts/"+id+"/response",{method:"POST",body:JSON.stringify({response})});setNotice(response==="Interested"?"Interest submitted for admin review.":"Marked not interested for this profile.");await load()}catch(e){setError(e instanceof Error?e.message:"Could not save response.")}}
  return <Layout><a className="text-link back-link" href="/posts">← Back to Tutoring Hub</a>{error&&<div className="alert error">{error}</div>}{notice&&<div className="alert success">{notice}</div>}{!post?<p className="muted">Loading…</p>:<section className="detail-card"><p className="eyebrow">{post.post_type==="tutor"?"TUTOR OFFER":"STUDENT REQUEST"} · #{post.id}</p><h1>{post.subjects.join(" · ")}</h1><p>Posted by {post.author_name} · {post.level}</p><div className="tag-list">{post.subjects.map(s=><span key={s}>{s}</span>)}</div><h2>Description</h2><p>{canSeeFullDetails?(post.description||"No description provided."):(post.description.slice(0,220)+(post.description.length>220?"…":""))}</p><h2>Details</h2>{canSeeFullDetails?<><p>Experience: {post.experience||"Not specified"}</p><p>Availability: {post.availability||"Flexible"}</p><p>Location: {post.location||"Not specified"}</p><p>Fee / budget: ৳{post.fee}</p></>:<p className="notice">Express interest to reveal the full listing details.</p>}<p>Status: {post.status}</p>{own?<p className="notice">This post belongs to your selected profile.</p>:active&&active.type!==post.post_type&&post.status==="Pending"?<><div className="task-confirm-controls"><button className="button primary" onClick={()=>void respond("Interested")}>Interested</button><button className="button secondary danger-text" onClick={()=>void respond("Not Interested")}>Not interested</button></div>{myResponse&&<p className="muted">Your response: {myResponse.response} · {myResponse.review_status}</p>}</>:!active?<p className="notice">Select a profile to respond to this post.</p>:null}</section>}</Layout>
}

