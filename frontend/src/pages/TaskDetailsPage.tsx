import { useEffect, useMemo, useState } from "react"
import type { FormEvent } from "react"
import { api, emptyPost, emptyStudent, emptyTutor, getAdminHeaders, Layout, saveSelectedProfile, selectedProfile, SubjectPicker, useSelectedProfile, type ProfileType, type Student, type Tutor, type Profile, type LearningPost, type InterestResponse, type SelectedProfile } from "../shared"
export default function MyResponsesPage(){
  const [responses,setResponses]=useState<InterestResponse[]>([]),[posts,setPosts]=useState<Record<number,LearningPost>>({})
  const [error,setError]=useState(""),[loading,setLoading]=useState(true)
  const active=useSelectedProfile()
  async function loadHistory(){if(!active){setLoading(false);return}setLoading(true);try{const r=await api<InterestResponse[]>("/api/responses");setResponses(r);const entries=await Promise.all(r.map(async item=>[item.post_id,await api<LearningPost>("/api/posts/"+item.post_id)] as const));setPosts(Object.fromEntries(entries))}catch(e){setError(e instanceof Error?e.message:"Could not load response history.")}finally{setLoading(false)}}
  useEffect(()=>{void loadHistory()},[active?.id,active?.type])
  async function changeResponse(postId:number,response:"Interested"|"Not Interested"){try{await api("/api/posts/"+postId+"/response",{method:"POST",body:JSON.stringify({response})});await loadHistory()}catch(e){setError(e instanceof Error?e.message:"Could not update response.")}}
  return <Layout><section className="page-intro compact"><¶»§q«^