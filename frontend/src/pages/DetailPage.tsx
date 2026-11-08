import { useEffect, useState } from "react"
import { Layout } from "../components/Layout"
import { api } from "../services/api"
import type { Profile } from "../types"

export default function DetailPage({ kind, id }: { kind: "student" | "tutor"; id: number }) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [error, setError] = useState("")
  const isTutor = kind === "tutor"
  useEffect(() => {
    api<Profile>(`/api/${kind}s/${id}`).then(setProfile).catch(err => setError(err instanceof Error ? err.message : "Could not load profile."))
  }, [kind, id])
  return <Layout>
    <a className="text-link back-link" href={isTutor ? "/tutors" : "/students"}>← Back to {isTutor ? "tutors" : "students"}</a>
    {error ? <div className="alert error">{error}</div> : !profile ? <p className="muted">Loading profile…</p> : <section className="detail-card">
      <div className="detail-avatar">{profile.full_name.charAt(0).toUpperCase()}</div>
      <p className="eyebrow">{isTutor ? "TUTOR PROFILE" : "STUDENT PROFILE"} · #{profile.id}</p>
      <h1>{profile.full_name}</h1>
      <p className="muted">Contact details are private in this public profile view.</p>
      {isTutor && "subject" in profile ? <><div className="tag-list"><span>{profile.subject}</span><span>{profile.teaching_level}</span></div><div className="detail-stats"><div><strong>{profile.experience_years}</strong><span>Years experience</span></div><div><strong>৳{profile.hourly_rate}</strong><span>Hourly rate</span></div></div><h2>About the tutor</h2><p>{profile.bio || "This tutor has not added a bio yet."}</p></> : "education_level" in profile ? <><h2>Education level</h2><p>{profile.education_level}</p><h2>Preferred subjects</h2><p>{profile.preferred_subjects || "No preferred subjects listed."}</p></> : null}
    </section>}
  </Layout>
}
