import { useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"
export default function RegisterPage() {
  const { register } = useAuth()
  const [role, setRole] = useState<"student" | "tutor">("student")
  const [form, setForm] = useState({ full_name: "", email: "", password: "", phone_number: "", education_level: "", subjects: "", teaching_level: "", experience_years: "0", hourly_rate: "500", bio: "", availability: "Flexible", claim_token: "" })
  const [error, setError] = useState(""), [busy, setBusy] = useState(false)
  const update = (key: string, value: string) => setForm(previous => ({ ...previous, [key]: value }))
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("")
    const subjects = form.subjects.split(",").map(value => value.trim()).filter(Boolean)
    const payload: Record<string, unknown> = { full_name: form.full_name, email: form.email, password: form.password, phone_number: form.phone_number, subjects }; if (form.claim_token.trim()) payload.claim_token = form.claim_token.trim()
    if (role === "student") payload.education_level = form.education_level
    else Object.assign(payload, { teaching_level: form.teaching_level, experience_years: Number(form.experience_years), hourly_rate: Number(form.hourly_rate), bio: form.bio, availability: form.availability })
    try { await register(role, payload); window.location.assign("/dashboard") } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create account.") } finally { setBusy(false) }
  }
  return <AppLayout><section className="page-intro compact"><p className="eyebrow">JOIN THE COMMUNITY</p><h1>Create your TutorInn account</h1><p>One secure account for your Student or Tutor experience.</p></section><section className="panel auth-panel"><form className="profile-form" onSubmit={submit}>
    <label className="field">I am joining as<select value={role} onChange={event => setRole(event.target.value as "student" | "tutor")}><option value="student">Student</option><option value="tutor">Tutor</option></select></label>
    <label className="field">Full name<input required minLength={2} maxLength={120} value={form.full_name} onChange={event => update("full_name", event.target.value)} /></label>
    <label className="field">Email address<input type="email" required autoComplete="email" value={form.email} onChange={event => update("email", event.target.value)} /></label>
    <label className="field">Admin-issued legacy profile claim code (optional)<input autoComplete="one-time-code" value={form.claim_token} onChange={event => update("claim_token", event.target.value)} /><small className="muted">Only enter this if an Admin has verified your existing MVP profile and issued you a one-time code.</small></label>
    <label className="field">Password (at least 12 characters)<input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={form.password} onChange={event => update("password", event.target.value)} /></label>
    <label className="field">Phone number<input type="tel" value={form.phone_number} onChange={event => update("phone_number", event.target.value)} /></label>
    <label className="field">{role === "student" ? "Subjects you want to learn" : "Subjects you teach"}<input required placeholder="Mathematics, Physics, English" value={form.subjects} onChange={event => update("subjects", event.target.value)} /><small className="muted">Separate subjects with commas.</small></label>
    {role === "student" ? <label className="field">Education level<input required value={form.education_level} onChange={event => update("education_level", event.target.value)} /></label> : <><label className="field">Teaching level / qualification<input required value={form.teaching_level} onChange={event => update("teaching_level", event.target.value)} /></label><label className="field">Years of experience<input type="number" min="0" max="60" required value={form.experience_years} onChange={event => update("experience_years", event.target.value)} /></label><label className="field">Hourly rate (৳)<input type="number" min="1" max="100000" required value={form.hourly_rate} onChange={event => update("hourly_rate", event.target.value)} /></label><label className="field">Availability<input value={form.availability} onChange={event => update("availability", event.target.value)} /></label><label className="field">Short bio<textarea rows={3} value={form.bio} onChange={event => update("bio", event.target.value)} /></label></>}
    {error && <div className="alert error" role="alert">{error}</div>}<button className="button primary" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
  </form><p className="auth-footnote">Already registered? <a className="text-link" href="/login">Sign in</a></p></section></AppLayout>
}
