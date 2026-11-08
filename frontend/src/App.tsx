import { useEffect, useMemo, useState } from "react"
import type { FormEvent, ReactNode } from "react"
import { useTheme } from "./context/ThemeContext"

type ProfileType = "student" | "tutor"
type Student = { id:number; full_name:string; email:string; education_level:string; subjects:string[] }
type Tutor = { id:number; full_name:string; email:string; subjects:string[]; teaching_level:string; experience_years:number; hourly_rate:number; bio:string }
type Profile = Student | Tutor
type LearningPost = {
  id:number; post_type:ProfileType; author_name:string; author_profile_id:number|null; author_profile_type:ProfileType|null
  subjects:string[]; subject:string; level:string; experience:string; availability:string; location:string
  fee:number; description:string; status:string
}
type InterestResponse = { id:number; post_id:number; profile_id:number; profile_type:ProfileType; response:"Interested"|"Not Interested"; review_status:string; created_at:string; updated_at:string }
type SelectedProfile = { id:number; type:ProfileType }

const PROFILE_ID_KEY = "tutorinn-profile-id"
const PROFILE_TYPE_KEY = "tutorinn-profile-type"
const emptyStudent = { full_name:"", email:"", education_level:"", subjects:[] as string[] }
const emptyTutor = { full_name:"", email:"", subjects:[] as string[], teaching_level:"", experience_years:"0", hourly_rate:"500", bio:"" }
const emptyPost = { subjects:[] as string[], level:"", experience:"", availability:"", location:"", fee:"500", description:"" }

function selectedProfile(): SelectedProfile | null {
  const id = Number(window.localStorage.getItem(PROFILE_ID_KEY))
  const type = window.localStorage.getItem(PROFILE_TYPE_KEY)
  return Number.isInteger(id) && id > 0 && (type === "student" || type === "tutor") ? { id, type } : null
}
function saveSelectedProfile(profile: SelectedProfile | null) {
  if (profile) {
    window.localStorage.setItem(PROFILE_ID_KEY, String(profile.id))
    window.localStorage.setItem(PROFILE_TYPE_KEY, profile.type)
  } else {
    window.localStorage.removeItem(PROFILE_ID_KEY)
    window.localStorage.removeItem(PROFILE_TYPE_KEY)
  }
  window.dispatchEvent(new Event("tutorinn-profile-change"))
}
function useSelectedProfile(): SelectedProfile | null {
  const [active,setActive] = useState<SelectedProfile|null>(selectedProfile)
  useEffect(() => {
    const sync = () => setActive(selectedProfile())
    window.addEventListener("tutorinn-profile-change",sync)
    return () => window.removeEventListener("tutorinn-profile-change",sync)
  },[])
  return active
}
function getAdminHeaders(): HeadersInit {
  let key = window.sessionStorage.getItem("tutorinn-admin-key")
  if (!key) {
    key = window.prompt("Enter the configured TutorInn Admin API key")
    if (!key) throw new Error("Admin API key is required.")
    window.sessionStorage.setItem("tutorinn-admin-key", key)
  }
  return { "X-Admin-Key": key }
}

async function api<T>(url:string, init?:RequestInit):Promise<T> {
  const profile = selectedProfile()
  const headers:Record<string,string> = {
    ...(init?.body ? {"Content-Type":"application/json"} : {}),
    ...(profile ? {"X-TutorInn-Profile-ID":String(profile.id),"X-TutorInn-Profile-Type":profile.type} : {}),
    ...(init?.headers as Record<string,string> || {}),
  }
  const response = await fetch(url,{...init,headers})
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === "string") message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((item:{loc?:unknown[];msg?:string}) => `${Array.isArray(item.loc) ? item.loc.filter(x=>x!=="body").join(".")+": " : ""}${item.msg ?? "Invalid value"}`).join("; ")
    } catch { /* retain HTTP status */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function SubjectPicker({value,onChange,label="Subjects"}:{value:string[];onChange:(next:string[])=>void;label?:string}) {
  const [draft,setDraft] = useState("")
  function add(raw:string) {
    const next = raw.split(/[,;\n]/).map(x=>x.trim()).filter(Boolean)
    if (next.length) {
      const unique = new Map<string,string>()
      for (const item of [...value,...next]) if (!unique.has(item.toLocaleLowerCase())) unique.set(item.toLocaleLowerCase(),item)
      onChange(Array.from(unique.values()).slice(0,20))
    }
    setDraft("")
  }
  return <div className="field">
    <span>{label}</span>
    <div className="tag-list">{value.map(subject=><button type="button" key={subject} className="subject-chip" onClick={()=>onChange(value.filter(x=>x!==subject))} aria-label={`Remove ${subject}`}>{subject} ×</button>)}</div>
    <div className="search-form">
      <input value={draft} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"||e.key===","){e.preventDefault();add(draft)}}} placeholder="Type a subject and press Enter"/>
      <button type="button" className="button secondary" onClick={()=>add(draft)} disabled={!draft.trim()}>Add</button>
    </div>
    <small className="muted">Add each subject separately. Duplicate subjects are ignored.</small>
  </div>
}

function Header() {
  const {theme,toggleTheme}=useTheme()
  const [profiles,setProfiles]=useState<Profile[]>([])
  const active=useSelectedProfile()
  async function load() {
    try {
      const [students,tutors]=await Promise.all([api<Student[]>("/api/students"),api<Tutor[]>("/api/tutors")])
      const all:Profile[]=[...students,...tutors]
      setProfiles(all)
      const current=selectedProfile()
      if (current && !all.some(p=>p.id===current.id && (current.type==="student" ? "education_level" in p : "teaching_level" in p))) {
        saveSelectedProfile(null)
      }
    } catch { /* profile directories show their own load errors */ }
  }
  useEffect(()=>{void load();const refresh=()=>void load();window.addEventListener("tutorinn-profile-change",refresh);return()=>window.removeEventListener("tutorinn-profile-change",refresh)},[])
  return <header className="site-header">
    <a className="brand" href="/">TutorInn<span>.</span></a>
    <nav aria-label="Main navigation"><a href="/">Home</a><a href="/about">About</a><a href="/posts">Tutoring Hub</a><a href="/task-details">My responses</a><a href="/admin">Admin review</a></nav>
    <div className="header-tools">
      <label className="profile-switcher"><span>Demo profile</span><select aria-label="Selected demo profile" value={active ? `${active.type}:${active.id}` : ""} onChange={e=>{const [type,id]=e.target.value.split(":");saveSelectedProfile(type==="student"||type==="tutor"?{type,id:Number(id)}:null)}}>
        <option value="">Select profile</option>
        {profiles.map(p=><option key={("education_level" in p?"student":"tutor")+":"+p.id} value={`${"education_level" in p?"student":"tutor"}:${p.id}`}>{p.full_name} · {"education_level" in p?"Student":"Tutor"} #{p.id}</option>)}
      </select></label>
      <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={`Switch to ${theme==="dark"?"light":"dark"} theme`}><span aria-hidden="true">{theme==="dark"?"☀":"☾"}</span><span>{theme==="dark"?"Light mode":"Dark mode"}</span></button>
    </div>
  </header>
}
function Footer(){return <footer className="site-footer">TutorInn · A simple place to connect learners and tutors.</footer>}
function Layout({children}:{children:ReactNode}){return <><Header/><main className="page">{children}</main><Footer/></>}
function HomePage(){return <Layout><section className="hero"><p className="eyebrow">LEARN WITH CONFIDENCE</p><h1>Find the right tutor.<br/><span>Reach your next goal.</span></h1><p className="hero-copy">Find tutors by subject and level, manage student and tutor profiles, and connect around learning opportunities.</p><div className="actions"><a className="button primary" href="/tutors">Explore tutors</a><a className="button secondary" href="/students">Student profiles</a><a className="button secondary" href="/posts">Tutoring Hub</a></div></section><section className="section"><div className="section-heading"><p className="eyebrow">HOW IT WORKS</p><h2>Everything you need to get started</h2></div><div className="feature-grid"><article className="feature-card"><span className="feature-icon">⌕</span><h3>Discover tutors</h3><p>Search tutors by name, subject, and teaching level.</p></article><article className="feature-card"><span className="feature-icon">◎</span><h3>Manage profiles</h3><p>Create, edit, delete, and select profiles directly from each directory.</p></article><article className="feature-card"><span className="feature-icon">✓</span><h3>Independent responses</h3><p>Each student or tutor can respond independently to each opportunity.</p></article></div></section></Layout>}
function AboutPage(){return <Layout><section className="page-intro"><p className="eyebrow">ABOUT TUTORINN</p><h1>Learning starts with the right connection.</h1><p>TutorInn helps students discover suitable tutors and helps tutors present their teaching experience.</p></section><section className="content-panel"><h2>Demo identity</h2><p>TutorInn currently uses a selected profile in this browser instead of user login. This is a demo workflow, not secure authentication.</p><h2>Technology</h2><p>React, TypeScript, FastAPI, and SQLAlchemy.</p></section></Layout>}

function ProfileManager({kind}:{kind:ProfileType}) {
  const isTutor=kind==="tutor", endpoint=`/api/${kind}s`
  const [profiles,setProfiles]=useState<Profile[]>([])
  const [form,setForm]=useState<Record<string,any>>(isTutor?{...emptyTutor}:{...emptyStudent})
  const [editId,setEditId]=useState<number|null>(null),[search,setSearch]=useState("")
  const [loading,setLoading]=useState(true),[saving,setSaving]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("")
  const active=useSelectedProfile()
  async function load(term=search){setLoading(true);setError("");try{setProfiles(await api<Profile[]>(endpoint+(term.trim()?"?q="+encodeURIComponent(term.trim()):"")))}catch(e){setError(e instanceof Error?e.message:"Could not load profiles.")}finally{setLoading(false)}}
  useEffect(()=>{void load("")},[endpoint])
  function reset(){setForm(isTutor?{...emptyTutor}:{...emptyStudent});setEditId(null)}
  function edit(profile:Profile){setEditId(profile.id);setForm("teaching_level" in profile?{...profile,experience_years:String(profile.experience_years),hourly_rate:String(profile.hourly_rate)}:{...profile});setNotice("");document.getElementById("profile-form")?.scrollIntoView({behavior:"smooth"})}
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
        <label className="field">Email<input type="email" required value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label>
        {!isTutor&&<label className="field">Education level<input required value={form.education_level} onChange={e=>setForm({...form,education_level:e.target.value})}/></label>}
        <SubjectPicker value={form.subjects||[]} onChange={subjects=>setForm({...form,subjects})} label={isTutor?"Subjects I teach":"Subjects I want to learn"}/>
        {isTutor&&<><label className="field">Teaching level<input required value={form.teaching_level} onChange={e=>setForm({...form,teaching_level:e.target.value})}/></label><label className="field">Experience (years)<input required type="number" min="0" max="60" value={form.experience_years} onChange={e=>setForm({...form,experience_years:e.target.value})}/></label><label className="field">Hourly rate (৳)<input required type="number" min="1" value={form.hourly_rate} onChange={e=>setForm({...form,hourly_rate:e.target.value})}/></label><label className="field">Short bio<textarea rows={4} value={form.bio} onChange={e=>setForm({...form,bio:e.target.value})}/></label></>}
        <div className="actions"><button className="button primary" disabled={saving||!form.subjects?.length}>{saving?"Saving…":editId===null?"Create profile":"Save changes"}</button>{editId!==null&&<button type="button" className="button secondary" onClick={reset}>Cancel</button>}</div>
      </form></aside>
    </section></Layout>
}

function DetailPage({kind,id}:{kind:ProfileType;id:number}){
  const [profile,setProfile]=useState<Profile|null>(null),[error,setError]=useState("")
  const isTutor=kind==="tutor"
  useEffect(()=>{api<Profile>(`/api/${kind}s/${id}`).then(setProfile).catch(e=>setError(e instanceof Error?e.message:"Could not load profile."))},[kind,id])
  return <Layout><a className="text-link back-link" href={isTutor?"/tutors":"/students"}>← Back to {isTutor?"tutors":"students"}</a>{error?<div className="alert error">{error}</div>:!profile?<p className="muted">Loading profile…</p>:<section className="detail-card"><div className="detail-avatar">{profile.full_name.charAt(0).toUpperCase()}</div><p className="eyebrow">{isTutor?"TUTOR PROFILE":"STUDENT PROFILE"} · #{profile.id}</p><h1>{profile.full_name}</h1><p className="muted">Contact details are private in this public profile view.</p><h2>{isTutor?"Subjects taught":"Preferred subjects"}</h2><div className="tag-list">{profile.subjects.map(s=><span key={s}>{s}</span>)}</div>{isTutor&&"teaching_level" in profile?<><h2>Teaching level</h2><p>{profile.teaching_level}</p><div className="detail-stats"><div><strong>{profile.experience_years}</strong><span>Years experience</span></div><div><strong>৳{profile.hourly_rate}</strong><span>Hourly rate</span></div></div><h2>About the tutor</h2><p>{profile.bio||"No bio added yet."}</p></>: "education_level" in profile?<><h2>Education level</h2><p>{profile.education_level}</p></>:null}</section>}</Layout>
}

function LearningPostsPage(){
  const [posts,setPosts]=useState<LearningPost[]>([]),[responses,setResponses]=useState<InterestResponse[]>([])
  const [form,setForm]=useState({...emptyPost}),[editId,setEditId]=useState<number|null>(null)
  const [filter,setFilter]=useState<"all"|"tutor"|"student">("all"),[subjectFilter,setSubjectFilter]=useState("")
  const [loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("")
  const active=useSelectedProfile()
  async function load(){setLoading(true);setError("");try{const [p,r]=await Promise.all([api<LearningPost[]>("/api/posts?offset=0&limit=20"+(filter==="all"?"":"&post_type="+filter)),active?api<InterestResponse[]>("/api/responses"):Promise.resolve([])]);setPosts(p);setResponses(r)}catch(e){setError(e instanceof Error?e.message:"Could not load posts.")}finally{setLoading(false)}}
  useEffect(()=>{void load()},[filter,active?.id,active?.type])
  function reset(){setForm({...emptyPost});setEditId(null)}
  async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();if(!active){setError("Select a Student or Tutor profile in the header before creating a listing.");return}if(editId!==null&&!posts.some(p=>p.id===editId&&p.author_profile_id===active.id&&p.author_profile_type===active.type)){setError("Only the selected author profile can edit this post.");return}
    setBusy(true);setError("");setNotice("");try{await api(editId===null?"/api/posts":"/api/posts/"+editId,{method:editId===null?"POST":"PUT",body:JSON.stringify({...form,post_type:active.type,author_name:"",subject:form.subjects[0]||""})});setNotice(editId===null?"Listing published.":"Listing updated.");reset();await load()}catch(e){setError(e instanceof Error?e.message:"Could not save listing.")}finally{setBusy(false)}}
  async function respond(post:LearningPost,response:"Interested"|"Not Interested"){setBusy(true);setError("");setNotice("");try{await api<InterestResponse>(`/api/posts/${post.id}/response`,{method:"POST",body:JSON.stringify({response})});setNotice(response==="Interested"?"Interest saved. It is now waiting for individual admin review.":"Marked not interested for this profile only.");await load()}catch(e){setError(e instanceof Error?e.message:"Could not save response.")}finally{setBusy(false)}}
  async function remove(post:LearningPost){if(!window.confirm("Delete this post permanently?"))return;try{await api<void>("/api/posts/"+post.id,{method:"DELETE"});setNotice("Post deleted.");await load()}catch(e){setError(e instanceof Error?e.message:"Could not delete post.")}}
  const filtered=posts.filter(p=>(!subjectFilter||p.subjects.some(s=>s.toLocaleLowerCase()===subjectFilter.toLocaleLowerCase()))&&myResponse(p.id)?.response!=="Not Interested")
  const myResponse=(postId:number)=>responses.find(r=>r.post_id===postId)
  return <Layout><section className="page-intro compact"><p className="eyebrow">TUTORINN COMMUNITY</p><h1>Tutoring Hub</h1><p>Browse tutor offers and student requests. Select a profile in the header to publish, manage posts, and respond independently.</p>{active&&<p className="notice">Using {active.type} profile #{active.id}. Demo identity only — not authentication.</p>}</section>
    {error&&<div className="alert error">{error}</div>}{notice&&<div className="alert success">{notice}</div>}
    <section className="panel posts-panel"><div className="posts-toolbar"><div><h2>Browse opportunities</h2><p className="muted">Filter by post type or subject.</p></div><div className="post-filters"><button className={filter==="all"?"button primary":"button secondary"} onClick={()=>setFilter("all")}>All</button><button className={filter==="tutor"?"button primary":"button secondary"} onClick={()=>setFilter("tutor")}>Tutor</button><button className={filter==="student"?"button primary":"button secondary"} onClick={()=>setFilter("student")}>Student</button></div></div>
      <label className="field">Filter by subject<input value={subjectFilter} onChange={e=>setSubjectFilter(e.target.value)} placeholder="Enter English, Bangla, Mathematics…"/></label>
      {loading?<p className="muted">Loading posts…</p>:filtered.length===0?<div className="empty-state"><h3>No posts found</h3></div>:<div className="profile-list">{filtered.map(p=>{const own=active&&p.author_profile_id===active.id&&p.author_profile_type===active.type;const response=myResponse(p.id);const canRespond=active&&active.type!==p.post_type&&p.status==="Pending";return <article className="profile-card" key={p.id}><div className={p.post_type==="student"?"avatar student-avatar":"avatar"}>{p.author_name.charAt(0).toUpperCase()}</div><div className="profile-info"><p className="eyebrow">{p.post_type==="tutor"?"TUTOR OFFER":"STUDENT REQUEST"}</p><h3>{p.level}</h3><p>Posted by {p.author_name} · {p.status}</p><div className="tag-list">{p.subjects.map(s=><span key={s}>{s}</span>)}</div><p className="muted">৳{p.fee} · {p.location||"Location not specified"}</p><div className="card-actions"><a className="text-link" href={"/task-details?id="+p.id}>View details</a>{own&&<><button className="small-button" onClick={()=>{setForm({subjects:p.subjects,level:p.level,experience:p.experience,availability:p.availability,location:p.location,fee:String(p.fee),description:p.description});setEditId(p.id);document.getElementById("post-form")?.scrollIntoView({behavior:"smooth"})}}>Edit</button><button className="small-button danger-text" onClick={()=>void remove(p)}>Delete</button></>}</div>{canRespond&&<div className="card-actions"><button className="small-button" disabled={busy} onClick={()=>void respond(p,"Interested")}>Interested</button><button className="small-button danger-text" disabled={busy} onClick={()=>void respond(p,"Not Interested")}>Not interested</button>{response&&<span className="muted">Your response: {response.response}{response.review_status!=="Not required"?" · "+response.review_status:""}</span>}</div>}{response&&!canRespond&&<p className="muted">Your response: {response.response}{response.review_status!=="Not required"?" · "+response.review_status:""}</p>}</div></article>})}</div>}
    </section>
    <section className="panel form-panel posts-form-panel" id="post-form"><h2>{editId===null?"Create a listing":"Edit listing"}</h2>{!active?<p className="notice">Select a profile in the navigation bar first. You can create a profile from <a className="text-link" href="/students">Student Profiles</a> or <a className="text-link" href="/tutors">Tutor Profiles</a>.</p>:<><p className="muted">Posting as {active.type} profile #{active.id}.</p><form className="profile-form" onSubmit={submit}><SubjectPicker value={form.subjects} onChange={subjects=>setForm({...form,subjects})} label={active.type==="tutor"?"Subjects you teach":"Subjects you need"}/><label className="field">Teaching / learning level<input required value={form.level} onChange={e=>setForm({...form,level:e.target.value})}/></label><label className="field">{active.type==="tutor"?"Teaching experience":"Learning goals / requirements"}<textarea rows={3} value={form.experience} onChange={e=>setForm({...form,experience:e.target.value})}/></label><label className="field">Availability<input value={form.availability} onChange={e=>setForm({...form,availability:e.target.value})}/></label><label className="field">Location<input value={form.location} onChange={e=>setForm({...form,location:e.target.value})}/></label><label className="field">{active.type==="tutor"?"Expected fee (৳)":"Budget (৳)"}<input required type="number" min="0" value={form.fee} onChange={e=>setForm({...form,fee:e.target.value})}/></label><label className="field">Description<textarea rows={4} value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label><div className="actions"><button className="button primary" disabled={busy||!form.subjects.length}>{busy?"Saving…":editId===null?"Publish post":"Save changes"}</button>{editId!==null&&<button type="button" className="button secondary" onClick={reset}>Cancel</button>}</div></form></>}</section>
  </Layout>
}

function MyResponsesPage(){
  const [responses,setResponses]=useState<InterestResponse[]>([]),[posts,setPosts]=useState<Record<number,LearningPost>>({})
  const [error,setError]=useState(""),[loading,setLoading]=useState(true)
  const active=useSelectedProfile()
  async function loadHistory(){if(!active){setLoading(false);return}setLoading(true);try{const r=await api<InterestResponse[]>("/api/responses");setResponses(r);const entries=await Promise.all(r.map(async item=>[item.post_id,await api<LearningPost>("/api/posts/"+item.post_id)] as const));setPosts(Object.fromEntries(entries))}catch(e){setError(e instanceof Error?e.message:"Could not load response history.")}finally{setLoading(false)}}
  useEffect(()=>{void loadHistory()},[active?.id,active?.type])
  async function changeResponse(postId:number,response:"Interested"|"Not Interested"){try{await api("/api/posts/"+postId+"/response",{method:"POST",body:JSON.stringify({response})});await loadHistory()}catch(e){setError(e instanceof Error?e.message:"Could not update response.")}}
  return <Layout><section className="page-intro compact"><p className="eyebrow">RESPONSE HISTORY</p><h1>My responses</h1><p>Interested and Not Interested responses belong to the selected profile only.</p></section>{error&&<div className="alert error">{error}</div>}{!active?<div className="empty-state"><p>Select a profile in the header to see its responses.</p></div>:loading?<p className="muted">Loading…</p>:responses.length===0?<div className="empty-state"><p>This profile has not responded to any posts yet.</p></div>:<section className="panel"><div className="profile-list">{responses.map(r=><article className="profile-card" key={r.id}><div className="profile-info"><h3>{posts[r.post_id]?.subjects?.join(" · ")||"Tutoring opportunity"}</h3><p>Post #{r.post_id} · {r.response}</p><p className="muted">Admin review: {r.review_status}</p><div className="card-actions"><a className="text-link" href={"/task-details?id="+r.post_id}>View post</a><button className="small-button" onClick={()=>void changeResponse(r.post_id,r.response==="Interested"?"Not Interested":"Interested")}>Change to {r.response==="Interested"?"Not Interested":"Interested"}</button></div></div></article>)}</div></section>}</Layout>
}

function AdminReviewPage(){
  const [responses,setResponses]=useState<InterestResponse[]>([]),[posts,setPosts]=useState<Record<number,LearningPost>>({})
  const [error,setError]=useState(""),[notice,setNotice]=useState(""),[loading,setLoading]=useState(false)
  async function load(){setLoading(true);setError("");try{const r=await api<InterestResponse[]>("/api/admin/responses?review_status=Pending",{headers:getAdminHeaders()});setResponses(r);const ids=Array.from(new Set(r.map(x=>x.post_id)));const entries=await Promise.all(ids.map(async id=>[id,await api<LearningPost>("/api/posts/"+id)] as const));setPosts(Object.fromEntries(entries))}catch(e){setError(e instanceof Error?e.message:"Could not load admin queue.")}finally{setLoading(false)}}
  async function decide(id:number,decision:"approve"|"reject"){try{await api("/api/responses/"+id+"/"+decision,{method:"POST",headers:getAdminHeaders()});setNotice("Interest response "+(decision==="approve"?"approved.":"rejected."));await load()}catch(e){setError(e instanceof Error?e.message:"Could not update response.")}}
  useEffect(()=>{void load()},[])
  return <Layout><section className="page-intro compact"><p className="eyebrow">ADMIN</p><h1>Interested response review</h1><p>Each Interested response is reviewed separately. Not Interested responses do not enter this queue.</p></section>{error&&<div className="alert error">{error}</div>}{notice&&<div className="alert success">{notice}</div>}{loading?<p className="muted">Loading review queue…</p>:responses.length===0?<div className="empty-state"><p>No pending Interested responses.</p><button className="button secondary" onClick={()=>void load()}>Refresh</button></div>:<section className="panel"><div className="profile-list">{responses.map(r=><article className="profile-card" key={r.id}><div className="profile-info"><h3>{posts[r.post_id]?.subjects?.join(" · ")||"Tutoring post"} · #{r.post_id}</h3><p>{r.profile_type} profile #{r.profile_id} expressed interest</p><div className="card-actions"><button className="button primary" onClick={()=>void decide(r.id,"approve")}>Approve this response</button><button className="button secondary danger-text" onClick={()=>void decide(r.id,"reject")}>Reject this response</button><a className="text-link" href={"/task-details?id="+r.post_id}>View post</a></div></div></article>)}</div></section>}</Layout>
}

function RequestDetailsPage(){
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

export default function App(){
  const path=window.location.pathname.replace(/\/$/,"")||"/"
  if(path==="/")return <HomePage/>
  if(path==="/about")return <AboutPage/>
  if(path==="/posts")return <LearningPostsPage/>
  if(path==="/task-details")return window.location.search?<RequestDetailsPage/>:<MyResponsesPage/>
  if(path==="/admin")return <AdminReviewPage/>
  if(path==="/tutors")return <ProfileManager kind="tutor"/>
  if(path==="/students")return <ProfileManager kind="student"/>
  const tutor=path.match(/^\/tutors\/(\d+)$/);if(tutor)return <DetailPage kind="tutor" id={Number(tutor[1])}/>
  const student=path.match(/^\/students\/(\d+)$/);if(student)return <DetailPage kind="student" id={Number(student[1])}/>
  return <Layout><section className="empty-state"><h1>Page not found</h1><a className="button primary" href="/">Back home</a></section></Layout>
}
