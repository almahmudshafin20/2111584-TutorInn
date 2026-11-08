import { useEffect, useMemo, useState } from "react"
import type { FormEvent, ReactNode } from "react"
import { useTheme } from "./context/ThemeContext"

export type ProfileType = "student" | "tutor"
export type Student = { id:number; full_name:string; email?:string; phone_number?:string; education_level:string; subjects:string[] }
export type Tutor = { id:number; full_name:string; email?:string; phone_number?:string; subjects:string[]; teaching_level:string; experience_years:number; hourly_rate:number; bio:string }
export type Profile = Student | Tutor
export type LearningPost = {
  id:number; post_type:ProfileType; author_name:string; author_profile_id:number|null; author_profile_type:ProfileType|null
  subjects:string[]; subject:string; level:string; experience:string; availability:string; location:string
  fee:number; description:string; status:string
}
export type InterestResponse = { id:number; post_id:number; profile_id:number; profile_type:ProfileType; response:"Interested"|"Not Interested"; review_status:string; created_at:string; updated_at:string }
export type SelectedProfile = { id:number; type:ProfileType }

export const emptyStudent = { full_name:"", email:"", phone_number:"", education_level:"", subjects:[] as string[] }
export const emptyTutor = { full_name:"", email:"", phone_number:"", subjects:[] as string[], teaching_level:"", experience_years:"0", hourly_rate:"500", bio:"" }
export const emptyPost = { subjects:[] as string[], level:"", experience:"", availability:"", location:"", fee:"500", description:"" }

// Display numbers are derived from the current newest-first post list. Database IDs
// remain stable and continue to be used for API requests and relationships.
export async function loadAllPosts(): Promise<LearningPost[]> {
  const pageSize = 20
  const all: LearningPost[] = []
  for (let offset = 0; offset <= 180; offset += pageSize) {
    const page = await api<LearningPost[]>(`/api/posts?offset=${offset}&limit=${pageSize}`)
    all.push(...page)
    if (page.length < pageSize) break
  }
  return all
}

export function createPostNumberMap(posts: LearningPost[]): Record<number, number> {
  return Object.fromEntries(posts.map((post, index) => [post.id, index + 1]))
}

import { selectedProfile, saveSelectedProfile } from "./services/session"
import { api, getAdminHeaders } from "./services/api"
export { selectedProfile, saveSelectedProfile } from "./services/session"
export { api, getAdminHeaders } from "./services/api"

export function useSelectedProfile(): SelectedProfile | null {
  const [active,setActive] = useState<SelectedProfile|null>(selectedProfile)
  useEffect(() => {
    const sync = () => setActive(selectedProfile())
    window.addEventListener("tutorinn-profile-change",sync)
    return () => window.removeEventListener("tutorinn-profile-change",sync)
  },[])
  return active
}

export function SubjectPicker({value,onChange,label="Subjects"}:{value:string[];onChange:(next:string[])=>void;label?:string}) {
  const [draft,setDraft] = useState("")
  const [catalog,setCatalog] = useState<string[]>([])
  useEffect(()=>{api<string[]>("/api/subjects").then(setCatalog).catch(()=>setCatalog([]))},[])
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
      <input list="tutorinn-subject-catalog" value={draft} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"||e.key===","){e.preventDefault();add(draft)}}} placeholder="Type or choose a subject and press Enter"/><datalist id="tutorinn-subject-catalog">{catalog.map(item=><option key={item} value={item}/>)}</datalist>
      <button type="button" className="button secondary" onClick={()=>add(draft)} disabled={!draft.trim()}>Add</button>
    </div>
    <small className="muted">Add each subject separately. Duplicate subjects are ignored.</small>
  </div>
}

export function Header() {
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

export function Footer(){return <footer className="site-footer">TutorInn · A simple place to connect learners and tutors.</footer>}

export function Layout({children}:{children:ReactNode}){return <><Header/><main className="page">{children}</main><Footer/></>}
