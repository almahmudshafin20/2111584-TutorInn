import { useEffect, useMemo, useState } from "react"
import type { FormEvent } from "react"
import { api, emptyPost, emptyStudent, emptyTutor, getAdminHeaders, Layout, saveSelectedProfile, selectedProfile, SubjectPicker, useSelectedProfile, type ProfileType, type Student, type Tutor, type Profile, type LearningPost, type InterestResponse, type SelectedProfile } from "../shared"
export default function AdminReviewPage(){
  const [responses,setResponses]=useState<InterestResponse[]>([]),[posts,setPosts]=useState<Record<number,LearningPost>>({})
  const [error,setError]=useState(""),[notice,setNotice]=useState(""),[loading,setLoading]=useState(false)
  async function load(){setLoading(true);setError("");try{const r=await api<InterestResponse[]>("/api/admin/responses?review_status=Pending",{headers:getAdminHeaders()});setResponses(r);const ids=Array.from(new Set(r.map(x=>x.post_id)));const entries=await Promise.all(ids.map(async id=>[id,await api<LearningPost>("/api/posts/"+id)] as const));setPosts(Object.fromEntries(entries))}catch(e){setError(e instanceof Error?e.message:"Could not load admin queue.")}finally{setLoading(false)}}
  async function decide(id:number,decision:"approve"|"reject"){try{await api("/api/responses/"+id+"/"+decision,{method:"POST",headers:getAdminHeaders()});setNotice("Interest response "+(decision==="approve"?"approved.":"rejected."));await load()}catch(e){setError(e instanceof Error?e.message:"Could not update response.")}}
  useEffect(()=>{void load()},¶»§q«^