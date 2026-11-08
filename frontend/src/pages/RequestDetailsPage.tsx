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
  async function respond(response:"Interested"|"Not Interested"){try{await api("/api/posts/"+id+"/response",{method:"POST",body:JSON.stringify({response})});setNotice(response==="Interested"?"Interest submitted for admin review.":"Marked not¶»§q«^