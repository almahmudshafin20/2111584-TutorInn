import { useEffect, useMemo, useState } from "react"
import type { FormEvent } from "react"
import { api, emptyPost, emptyStudent, emptyTutor, getAdminHeaders, Layout, saveSelectedProfile, selectedProfile, SubjectPicker, useSelectedProfile, type ProfileType, type Student, type Tutor, type Profile, type LearningPost, type InterestResponse, type SelectedProfile } from "../shared"
export default function ProfileManager({kind}:{kind:ProfileType}) {
  const isTutor=kind==="tutor", endpoint=`/api/${kind}s`
  const [profiles,setProfiles]=useState<Profile[]>([])
  const [form,setForm]=useState<Record<string,any>>(isTutor?{...emptyTutor}:{...emptyStudent})
  const [editId,setEditId]=useState<number|null>(null),[search,setSearch]=useState("")
  const [loading,setLoading]=useState(true),[saving,setSaving]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("")
  const active=useSelectedProfile()
  async function load(term=search){setLoading(true);setError("");try{setProfiles(await api<Profile[]>(endpoint+(term.trim()?"?q="+encodeURIComponent(term.trim()):"")))}catch(e){setError(e instanceof Error?e.message:"Could not load profiles.")}finally{setLoading(false)}}
  useEffect(()=>{void load("")},[endpoint])
  function reset(){setForm(isTutor?{...emptyTutor}:{...emptyStudent});setEditId(null)}
  function edit(profile:Profile){setEditId(profile.id);setForm("teaching_level" in profile?{...profile,email:"",experience_years:String(profile.experience_years),hourly_rate:String(profile.hourly_rate)}:{...profile,email:""});setNotice("");document.getElementById("profile-form")?.scrollIntoView({behavior:"smooth"})}
  async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setSaving(true);setError("");setNotice("")
    const payload={...form}
    if(isTutor){payload.experience_years=Number(form.experience_years);payload.hourly_rate=Number(form.hourly_rate)}
    delete payload.id;delete payload.preferred_subjects;delete payload.subject
    try{
      const saved=await api<Profile>(endpoint+(editId===null?"":"/"+editId),{method:editId===null?"POST":"PUT",body:JSON.stringify(payload)})
      if(editId===null){saveSelectedProfile({id:saved.id,type:kind});setNotice("Profile created and selected successfully.")}
      else setNotice("Profile updated successfully.")
      reset();await load()
    }catch(e){setError(e instanceof Error?e.message:"Could not save profile.")}finally{setSaving(false)}
  }
  async function remove(profile:Profile){if(!window.confirm(`Delete ${profile.full_name}? This also permanently deletes tutoring posts created by this profile and all related responses.`))return;setError("");setNotice("")
    try{await api<void>(endpoint+"/"+profile.id,{method:"DELETE"});if(active?.id===profile.id&&active.type===kind)saveSelectedProfile(null);if(editId===profile.id)reset();setNotice("Profile deleted.");await load()}
    catch(e){setError(e instanceof Error?e.message:"Could not delete profile.")}
  }
  function useProfile(profile:Profile){saveSelectedProfile({id:profile.id,type:kind});setNotice(`${profile.full_name} is now the selected demo profile.`)}
  const title=isTutor?"Tutor profiles":"Student profiles"
  return <Layout><section className="page-intro compact"><p className="eyebrow">{isTutor?"TUTOR DIRECTORY":"STUDENT DIRECTORY"}</p><h1>{title}</h1><p>Manage profiles directly here. You do not need to visit the Tutoring Hub to edit or delete a profile.</p></section>
    {error&&<div className="alert error" role="alert">{error}</div>}{notice&&<div className="alert success" role="status">{notice}</div>}
    <section className="manager-grid"><div className="panel list-panel"><div className="panel-heading"><div><h2>{isTutor?"Browse tutors":"Browse students"}</h2><p>{profiles.length} profile(s)</p></div></div>
      <form className="search-form" onSubmit={e=>{e.preventDefault();void load(search)}}><input value={search} onChange={e=>setSearch(e.target.value)} placeholder={isTutor?"Search name, subject or bio":"Search name or subject"}/><button className="button primary">Search</button>{search&&<button type="button" className="button secondary" onClick={()=>{setSearch("");void load("")}}>Clear</button>}</form>
      {loading?<p className="muted">Loading profiles…</p>:profiles.length===0?<div className="empty-state"><h3>No profiles yet</h3><p>Create the first profile using the form.</p></div>:<div className="profile-list">{profiles.map(p=>{
        const pType="teaching_level" in p?"tutor":"student", subjects=p.subjects||[]
        return <article className="profile-card" key={p.id}><div className={pType==="student"?"avatar student-avatar":"avatar"}>{p.full_name.charAt(0).toUpperCase()}</div><div className="profile-info"><h3><a href={`/${kind}s/${p.id}`}>{p.full_name}</a></h3><p>{pType==="tutor"?(p as Tutor).teaching_level:(p as Student).education_level}</p><div className="tag-list">{subjects.map(s=><span key={s}>{s}</span>)}</div>{pType==="tutor"&&<p className="muted">{(p as Tutor).experience_years} years experience · ৳{(p as Tutor).hourly_rate}/hour</p>}<div className="card-actions"><a className="text-link" href={`/${kind}s/${p.id}`}>View details</a><button type="button" className="small-button" onClick={()=>useProfile(p)}>{active?.id===p.id&&active.type===kind?"Selected":"Use profile"}</button><button type="button" className="small-button" onClick={()=>edit(p)}>Edit</button><button type="button" className="small-button danger-text" onClick={()=>void remove(p)}>Delete</button></div></div></article>
      })}</div>}</div>
      <aside className="panel form-panel" id="profile-form"><h2>{editId===null?`Create ${isTutor?"tutor":"student"} profile`:"Edit profile"}</h2><form className="profile-form" onSubmit={submit}>
        <label className="field">Full name<input required minLength={2} value={form.full_name} onChange={e=>setForm({...form,full_name:e.target.value})}/></label>
        <label className="field">Email<input type="email" required value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/>{editId!==null&&<small className="muted">For privacy, public profile APIs do not return the saved email. Re-enter it only if you want to update it.</small>}</label>
        {!isTutor&&<label className="field">Education level<input required value={form.education_level} onChange={e=>setForm({...form,education_level:e.target.value})}/></label>}
        <SubjectPicker value={form.subjects||[]} onChange={subjects=>setForm({...form,subjects})} label={isTutor?"Subjects I teach":"Subjects I want to learn"}/>
        {isTutor&&<><label className="field">Teaching level<input required value={form.teaching_level} onChange={e=>setForm({...form,teaching_level:e.target.value})}/></label><label className="field">Experience (years)<input required type="number" min="0" max="60" value={form.experience_years} onChange={e=>setForm({...form,experience_years:e.target.value})}/></label><label className="field">Hourly rate (৳)<input required type="number" min="1" value={form.hourly_rate} onChange={e=>setForm({...form,hourly_rate:e.target.value})}/></label><label className="field">Short bio<textarea rows={4} value={form.bio} onChange={e=>setForm({...form,bio:e.target.value})}/></label></>}
        <div className="actions"><button className="button primary" disabled={saving||!form.subjects?.length}>{saving?"Saving…":editId===null?"Create profile":"Save changes"}</button>{editId!==null&&<button type="button" className="button secondary" onClick={reset}>Cancel</button>}</div>
      </form></aside>
    </section></Layout>
}
