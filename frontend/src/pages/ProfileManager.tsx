import { useEffect, useMemo, useState } from "react"
import type { FormEvent } from "react"
import { Layout } from "../components/Layout"
import { createProfile, deleteProfile as deleteProfileRequest, listProfiles, updateProfile } from "../services/api"
import { readCurrentRole } from "../services/session"
import { emptyStudent, emptyTutor, studentFields, tutorFields } from "../types/forms"
import type { Field, Profile, Student, Tutor } from "../types"

export default function ProfileManager({ kind }: { kind: "student" | "tutor" }) {
  const isTutor = kind === "tutor"
  const currentRole = readCurrentRole()
  const canManageThisKind = currentRole === kind
  const fields = isTutor ? tutorFields : studentFields
  const blank = isTutor ? emptyTutor : emptyStudent
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [form, setForm] = useState<Record<string, string>>(blank)
  const [editId, setEditId] = useState<number | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  async function loadProfiles(term = search) {
    setLoading(true)
    setError("")
    try {
      setProfiles(await listProfiles(kind, term))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load profiles.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadProfiles("") }, [kind])

  const visibleFields = fields
  const heading = isTutor ? "Tutor profiles" : "Student profiles"
  const subtitle = isTutor
    ? "Find tutors by name or subject, view details, and manage tutor profiles."
    : "Create and manage student records for the TutorInn MVP."

  function resetForm() {
    setForm(blank)
    setEditId(null)
  }

  function startEdit(profile: Profile) {
    const values: Record<string, string> = {}
    for (const field of visibleFields) values[field.name] = String((profile as unknown as Record<string, unknown>)[field.name] ?? "")
    setForm(values)
    setEditId(profile.id)
    setNotice("")
    setError("")
    document.getElementById("profile-form")?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canManageThisKind) {
      setError(`Continue as ${currentRole} to manage ${kind} profiles.`)
      return
    }
    setSaving(true)
    setError("")
    setNotice("")
    const payload: Record<string, string | number> = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value.trim()]))
    if (isTutor) {
      payload.experience_years = Number(form.experience_years)
      payload.hourly_rate = Number(form.hourly_rate)
    }
    try {
      if (editId === null) {
        await createProfile(kind, payload)
        setNotice(`${isTutor ? "Tutor" : "Student"} profile created successfully.`)
      } else {
        await updateProfile(kind, editId, payload)
        setNotice(`${isTutor ? "Tutor" : "Student"} profile updated successfully.`)
      }
      resetForm()
      await loadProfiles()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile.")
    } finally {
      setSaving(false)
    }
  }

  async function deleteProfile(profile: Profile) {
    if (!canManageThisKind) {
      setError(`Continue as ${currentRole} to manage ${kind} profiles.`)
      return
    }
    if (!window.confirm(`Delete the profile for ${profile.full_name}? This cannot be undone.`)) return
    setError("")
    setNotice("")
    try {
      await deleteProfileRequest(kind, profile.id)
      setNotice("Profile deleted.")
      if (editId === profile.id) resetForm()
      await loadProfiles()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete profile.")
    }
  }

  const tutorProfiles = useMemo(() => profiles as Tutor[], [profiles])
  const studentProfiles = useMemo(() => profiles as Student[], [profiles])

  return <Layout>
    <section className="page-intro compact"><p className="eyebrow">{isTutor ? "TUTOR DIRECTORY" : "STUDENT MANAGEMENT"}</p><h1>{heading}</h1><p>{subtitle}</p></section>
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    <section className="manager-grid">
      <div className="panel list-panel">
        <div className="panel-heading"><div><h2>{isTutor ? "Browse tutors" : "All students"}</h2><p>{profiles.length} profile{profiles.length === 1 ? "" : "s"}</p></div></div>
        <form className="search-form" onSubmit={e => { e.preventDefault(); void loadProfiles(search) }}>
          <input aria-label={isTutor ? "Search tutors" : "Search students"} value={search} onChange={e => setSearch(e.target.value)} placeholder={isTutor ? "Search name, subject or bio" : "Search name or subject"} />
          <button className="button primary" type="submit">Search</button>
          {search && <button className="button secondary" type="button" onClick={() => { setSearch(""); void loadProfiles("") }}>Clear</button>}
        </form>
        {loading ? <p className="muted">Loading profiles…</p> : profiles.length === 0 ? <div className="empty-state"><h3>No profiles yet</h3><p>Create the first profile using the form.</p></div> : <div className="profile-list">
          {isTutor ? tutorProfiles.map(profile => <article className="profile-card" key={profile.id}>
            <div className="avatar">{profile.full_name.trim().charAt(0).toUpperCase()}</div>
            <div className="profile-info"><h3><a href={`/tutors/${profile.id}`}>{profile.full_name}</a></h3><p>{profile.subject} · {profile.teaching_level}</p><p className="muted">{profile.experience_years} year{profile.experience_years === 1 ? "" : "s"} experience · ৳{profile.hourly_rate}/hour</p><div className="card-actions"><a className="text-link" href={`/tutors/${profile.id}`}>View details</a>{canManageThisKind && <><button type="button" className="small-button" onClick={() => startEdit(profile)}>Edit</button><button type="button" className="small-button danger-text" onClick={() => void deleteProfile(profile)}>Delete</button></>}</div></div>
          </article>) : studentProfiles.map(profile => <article className="profile-card" key={profile.id}>
            <div className="avatar student-avatar">{profile.full_name.trim().charAt(0).toUpperCase()}</div>
            <div className="profile-info"><h3><a href={`/students/${profile.id}`}>{profile.full_name}</a></h3><p>{profile.education_level}</p><p className="muted">{profile.preferred_subjects || "No preferred subjects listed"}</p><div className="card-actions"><a className="text-link" href={`/students/${profile.id}`}>View details</a>{canManageThisKind && <><button type="button" className="small-button" onClick={() => startEdit(profile)}>Edit</button><button type="button" className="small-button danger-text" onClick={() => void deleteProfile(profile)}>Delete</button></>}</div></div>
          </article>)}
        </div>}
      </div>
      {canManageThisKind && <aside className="panel form-panel" id="profile-form">
        <h2>{editId === null ? `Create ${isTutor ? "tutor" : "student"} profile` : "Edit profile"}</h2>
        <p className="muted">{editId === null ? "Fill in the details below to add a profile." : `Editing profile #${editId}.`}</p>
        <form className="profile-form" onSubmit={submitForm}>
          {visibleFields.map(field => <label className="field" key={field.name}>{field.label}{field.type === "textarea" ? <textarea value={form[field.name] ?? ""} onChange={e => setForm({ ...form, [field.name]: e.target.value })} placeholder={field.placeholder} rows={4} maxLength={2000} /> : <input type={field.type ?? "text"} value={form[field.name] ?? ""} onChange={e => setForm({ ...form, [field.name]: e.target.value })} placeholder={field.placeholder} required={field.required} min={field.name === "experience_years" ? 0 : field.name === "hourly_rate" ? 1 : undefined} max={field.name === "experience_years" ? 60 : undefined} step={field.name === "hourly_rate" ? "0.01" : "1"} />}</label>)}
          <div className="actions"><button className="button primary" type="submit" disabled={saving}>{saving ? "Saving…" : editId === null ? "Create profile" : "Save changes"}</button>{editId !== null && <button className="button secondary" type="button" onClick={resetForm}>Cancel</button>}</div>
        </form>
      </aside>}
    </section>
  </Layout>
}
