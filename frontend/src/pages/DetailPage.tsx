import { useEffect, useState } from "react"
import { getProfile } from "../services/profiles"
import { AppLayout as Layout } from "../layouts/AppLayout"
import type { ProfileType, Profile } from "../types/domain"

export default function DetailPage({ kind, id }: { kind: ProfileType; id: number }) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [error, setError] = useState("")
  const isTutor = kind === "tutor"

  useEffect(() => {
    let active = true
    setProfile(null)
    setError("")
    getProfile(kind, id)
      .then(result => { if (active) setProfile(result) })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Could not load profile.") })
    return () => { active = false }
  }, [kind, id])

  return (
    <Layout>
      <a className="text-link back-link" href={isTutor ? "/tutors" : "/register?role=student"}>← {isTutor ? "Back to tutors" : "Create a Student account"}</a>
      {error ? <div className="alert error" role="alert">{error}</div> : !profile ? <p className="muted" role="status">Loading profile…</p> : (
        <section className="detail-card">
          <div className="detail-avatar">{profile.full_name.charAt(0).toUpperCase()}</div>
          <p className="eyebrow">{isTutor ? "TUTOR PROFILE" : "STUDENT PROFILE"} · #{profile.id}</p>
          <h1>{profile.full_name}</h1>
          <p className="muted">Public profile · Contact details are kept private. Use TutorInn's authenticated request workflow to connect.</p>
          <h2>{isTutor ? "Subjects taught" : "Preferred subjects"}</h2>
          <div className="tag-list">{profile.subjects.map(subject => <span key={subject}>{subject}</span>)}</div>
          {isTutor && "teaching_level" in profile ? (
            <>
              <h2>Teaching level</h2><p>{profile.teaching_level}</p>
              <div className="detail-stats">
                <div><strong>{profile.experience_years}</strong><span>Years experience</span></div>
                <div><strong>৳{profile.hourly_rate}</strong><span>Hourly rate</span></div>
              </div>
              <h2>About the tutor</h2><p>{profile.bio || "No bio added yet."}</p>
              <p className="muted">{profile.availability || "Availability not listed"}</p>
            </>
          ) : null}
        </section>
      )}
    </Layout>
  )
}
