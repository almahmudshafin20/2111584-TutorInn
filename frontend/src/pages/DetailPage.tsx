import { useEffect, useState } from "react"
import { api, Layout, useSelectedProfile, type ProfileType, type Profile } from "../shared"

type ApprovedMatch = {
  response: { id:number; review_status:string }
  post: { id:number; subjects:string[]; level:string; location:string; availability:string; fee:number; description:string }
  counterpart: { id:number; type:ProfileType; full_name:string; email:string; phone_number:string; subjects:string[]; education_level:string|null; teaching_level:string|null; experience_years:number|null; hourly_rate:number|null; bio:string|null }
}

export default function DetailPage({kind,id}:{kind:ProfileType;id:number}) {
  const [profile,setProfile]=useState<Profile|null>(null)
  const [matches,setMatches]=useState<ApprovedMatch[]>([])
  const [error,setError]=useState("")
  const active=useSelectedProfile()
  const isOwnSelectedProfile=active?.id===id && active.type===kind
  const isTutor=kind==="tutor"
  useEffect(()=>{setProfile(null);api<Profile>(`/api/${kind}s/${id}`).then(setProfile).catch(e=>setError(e instanceof Error?e.message:"Could not load profile."))},[kind,id])
  useEffect(()=>{
    if(!isOwnSelectedProfile){setMatches([]);return}
    api<ApprovedMatch[]>("/api/profiles/approved-matches").then(setMatches).catch(()=>setMatches([]))
  },[isOwnSelectedProfile,active?.id,active?.type])
  return <Layout>
    <a className="text-link back-link" href={isTutor?"/tutors":"/students"}>← Back to {isTutor?"tutors":"students"}</a>
    {error?<div className="alert error">{error}</div>:!profile?<p className="muted">Loading profile…</p>:<section className="detail-card">
      <div className="detail-avatar">{profile.full_name.charAt(0).toUpperCase()}</div>
      <p className="eyebrow">{isTutor?"TUTOR PROFILE":"STUDENT PROFILE"} · #{profile.id}</p>
      <h1>{profile.full_name}</h1>
      <p className="muted">Public profile · Contact details are hidden until an admin approves a match.</p>
      <h2>{isTutor?"Subjects taught":"Preferred subjects"}</h2><div className="tag-list">{profile.subjects.map(s=><span key={s}>{s}</span>)}</div>
      {isTutor&&"teaching_level" in profile?<><h2>Teaching level</h2><p>{profile.teaching_level}</p><div className="detail-stats"><div><strong>{profile.experience_years}</strong><span>Years experience</span></div><div><strong>৳{profile.hourly_rate}</strong><span>Hourly rate</span></div></div><h2>About the tutor</h2><p>{profile.bio||"No bio added yet."}</p></>: "education_level" in profile?<><h2>Education level</h2><p>{profile.education_level}</p></>:null}
      {isOwnSelectedProfile&&<section className="approved-matches"><h2>Approved tutoring matches</h2>{matches.length===0?<p className="muted">No approved matches for this selected profile yet. Pending and rejected requests do not reveal contact details.</p>:matches.map(match=><article className="profile-card" key={match.response.id}><div className="profile-info"><p className="eyebrow">ADMIN APPROVED · POST #{match.post.id}</p><h3>{match.counterpart.full_name}</h3><p>{match.counterpart.type==="tutor"?"Tutor":"Student"} · {match.post.subjects.join(", ")} · {match.post.level}</p><p><strong>Email:</strong> <a href={`mailto:${match.counterpart.email}`}>{match.counterpart.email}</a></p><p><strong>Phone:</strong> <a href={`tel:${match.counterpart.phone_number}`}>{match.counterpart.phone_number||"Not provided"}</a></p></div></article>)}</section>}
      {!isOwnSelectedProfile&&<p className="notice">Select this profile in the Demo profile switcher to see its own approved matches.</p>}
    </section>}
  </Layout>
}
