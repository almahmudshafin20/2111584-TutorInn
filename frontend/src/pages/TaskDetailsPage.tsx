import { useEffect, useState } from "react"
import { api } from "../services/api"
import { AppLayout as Layout } from "../layouts/AppLayout"
import { loadAllPosts, createPostNumberMap } from "../services/posts"
import { useSelectedProfile } from "../hooks/useSelectedProfile"
import type { LearningPost, InterestResponse } from "../types/domain"
export default function MyResponsesPage(){
  const [responses,setResponses]=useState<InterestResponse[]>([]),[posts,setPosts]=useState<Record<number,LearningPost>>({}),[postNumbers,setPostNumbers]=useState<Record<number,number>>({})
  const [error,setError]=useState(""),[loading,setLoading]=useState(true)
  const active=useSelectedProfile()
  async function loadHistory(){if(!active){setLoading(false);return}setLoading(true);try{const [r,all]=await Promise.all([api<InterestResponse[]>("/api/responses"),loadAllPosts()]);setResponses(r);setPosts(Object.fromEntries(all.map(post=>[post.id,post])));setPostNumbers(createPostNumberMap(all))}catch(e){setError(e instanceof Error?e.message:"Could not load response history.")}finally{setLoading(false)}}
  useEffect(()=>{void loadHistory()},[active?.id,active?.type])
  async function changeResponse(postId:number,response:"Interested"|"Not Interested"){try{await api("/api/posts/"+postId+"/response",{method:"POST",body:JSON.stringify({response})});await loadHistory()}catch(e){setError(e instanceof Error?e.message:"Could not update response.")}}
  return <Layout><section className="page-intro compact"><p className="eyebrow">RESPONSE HISTORY</p><h1>My responses</h1><p>Interested and Not Interested responses belong to the selected profile only.</p></section>{error&&<div className="alert error">{error}</div>}{!active?<div className="empty-state"><p>Select a profile in the header to see its responses.</p></div>:loading?<p className="muted">Loading…</p>:responses.length===0?<div className="empty-state"><p>This profile has not responded to any posts yet.</p></div>:<section className="panel"><div className="profile-list">{responses.map(r=><article className="profile-card" key={r.id}><div className="profile-info"><h3>{posts[r.post_id]?.subjects?.join(" · ")||"Tutoring opportunity"}</h3><p>Post #{postNumbers[r.post_id]??"—"} · {r.response}</p><p className="muted">Admin review: {r.review_status}</p><div className="card-actions"><a className="text-link" href={"/task-details?id="+r.post_id}>View post</a><button className="small-button" onClick={()=>void changeResponse(r.post_id,r.response==="Interested"?"Not Interested":"Interested")}>Change to {r.response==="Interested"?"Not Interested":"Interested"}</button></div></div></article>)}</div></section>}</Layout>
}
