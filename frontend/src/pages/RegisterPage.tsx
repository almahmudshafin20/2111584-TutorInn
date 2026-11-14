import { useState } from "react"
import type { FormEvent } from "react"
import { AppLayout } from "../layouts/AppLayout"
import { useAuth } from "../context/AuthContext"

export default function RegisterPage() {
  const { register } = useAuth()
  const [role, setRole] = useState<"student" | "tutor">(() => new URLSearchParams(window.location.search).get("role") === "tutor" ? "tutor" : "student")
  const [form, setForm] = useState({ full_name: "", email: "", password: "", password_confirm: "", phone_number: "", education_level: "", subjects: "", teaching_level: "", experience_years: "0", hourly_rate: "500", bio: "", availability: "Flexible", claim_token: "" })
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const update = (key: string, value: string) => setForm(previous => ({ ...previous, [key]: value }))

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (form.password !== form.password_confirm) { setError("Passwords do not match."); return }
    setBusy(true)
    setError("")
    const subjects = form.subjects.split(",").map(value => value.trim()).filter(Boolean)
    const payload: Record<string, unknown> = { full_name: form.full_name, email: form.email, password: form.password, phone_number: form.phone_number, subjects }
    if (form.claim_token.trim()) payload.claim_token = form.claim_token.trim()
    if (role === "student") payload.education_level = form.education_level
    else Object.assign(payload, { teaching_level: form.teaching_level, experience_years: Number(form.experience_years), hourly_rate: Number(form.hourly_rate), bio: form.bio, availability: form.availability })
    try {
      await register(role, payload)
      window.location.assign("/dashboard")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create account.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppLayout>
      <section className="auth-shell auth-shell-register" aria-labelledby="register-title">
        <aside className="auth-aside">
          <span className="auth-mark" aria-hidden="true">T.</span>
          <p className="eyebrow">JOIN THE COMMUNITY</p>
          <h2>Start with the right connection.</h2>
          <p>Create your account and build a learning experience around your goals.</p>
          <ul className="auth-benefits">
            <li><span aria-hidden="true">✓</span> A dedicated workspace for your role</li>
            <li><span aria-hidden="true">✓</span> Profiles that highlight learning needs or teaching experience</li>
            <li><span aria-hidden="true">✓</span> A clear place to manage requests and responses</li>
          </ul>
          <div className="auth-orbit auth-orbit-one" aria-hidden="true" />
          <div className="auth-orbit auth-orbit-two" aria-hidden="true" />
        </aside>
        <div className="auth-content">
          <div className="auth-form-heading">
            <p className="eyebrow">CREATE YOUR ACCOUNT</p>
            <h1 id="register-title">Join TutorInn</h1>
            <p>Tell us a little about yourself to set up your workspace.</p>
          </div>
          <form className="profile-form auth-form" onSubmit={submit}>
            <fieldset className="role-choice-field">
              <legend>I am joining as</legend>
              <div className="role-choice-grid">
                <label className={`role-choice-card ${role === "student" ? "is-selected" : ""}`}>
                  <input className="role-choice-radio" type="radio" name="account-role" value="student" checked={role === "student"} onChange={() => setRole("student")} />
                  <span className="role-choice-symbol" aria-hidden="true">◎</span>
                  <span className="role-choice-copy"><strong>Student</strong><small>Find tutors and manage learning requests</small></span>
                  <span className="role-choice-indicator" aria-hidden="true" />
                </label>
                <label className={`role-choice-card ${role === "tutor" ? "is-selected" : ""}`}>
                  <input className="role-choice-radio" type="radio" name="account-role" value="tutor" checked={role === "tutor"} onChange={() => setRole("tutor")} />
                  <span className="role-choice-symbol" aria-hidden="true">✦</span>
                  <span className="role-choice-copy"><strong>Tutor</strong><small>Share your expertise and teach learners</small></span>
                  <span className="role-choice-indicator" aria-hidden="true" />
                </label>
              </div>
            </fieldset>
            <label className="field">Full name
              <input required minLength={2} maxLength={120} autoComplete="name" value={form.full_name} onChange={event => update("full_name", event.target.value)} placeholder="Your full name" />
            </label>
            <label className="field">Email address
              <input type="email" required autoComplete="email" value={form.email} onChange={event => update("email", event.target.value)} placeholder="you@example.com" />
            </label>
            <label className="field">Password <span className="field-hint">At least 12 characters</span>
              <input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={form.password} onChange={event => update("password", event.target.value)} placeholder="Create a strong password" />
            </label>
            <label className="field">Confirm password
              <input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={form.password_confirm} onChange={event => update("password_confirm", event.target.value)} placeholder="Re-enter your password" />
            </label>
            <label className="field">Phone number <span className="field-hint">Optional</span>
              <input type="tel" autoComplete="tel" value={form.phone_number} onChange={event => update("phone_number", event.target.value)} placeholder="+880 1XXXXXXXXX" />
            </label>
            <label className="field">{role === "student" ? "Subjects you want to learn" : "Subjects you teach"}
              <input required placeholder="Mathematics, Physics, English" value={form.subjects} onChange={event => update("subjects", event.target.value)} />
              <small className="muted">Separate subjects with commas.</small>
            </label>
            {role === "student" ? (
              <label className="field">Education level
                <input required value={form.education_level} onChange={event => update("education_level", event.target.value)} placeholder="e.g. HSC, University" />
              </label>
            ) : (
              <>
                <label className="field">Teaching level / qualification
                  <input required value={form.teaching_level} onChange={event => update("teaching_level", event.target.value)} placeholder="e.g. University, A-Level" />
                </label>
                <div className="auth-field-grid">
                  <label className="field">Years of experience
                    <input type="number" min="0" max="60" required value={form.experience_years} onChange={event => update("experience_years", event.target.value)} />
                  </label>
                  <label className="field">Hourly rate (৳)
                    <input type="number" min="1" max="100000" required value={form.hourly_rate} onChange={event => update("hourly_rate", event.target.value)} />
                  </label>
                </div>
                <label className="field">Availability
                  <input value={form.availability} onChange={event => update("availability", event.target.value)} placeholder="e.g. Weekends, evenings" />
                </label>
                <label className="field">Short bio
                  <textarea rows={3} value={form.bio} onChange={event => update("bio", event.target.value)} placeholder="Share a little about your teaching experience." />
                </label>
              </>
            )}
            <details className="claim-details">
              <summary>Have an existing TutorInn profile?</summary>
              <label className="field">Admin-issued profile claim code (optional)
                <input autoComplete="one-time-code" value={form.claim_token} onChange={event => update("claim_token", event.target.value)} />
                <small className="muted">Only enter this if an Admin has verified your existing MVP profile and issued you a one-time code.</small>
              </label>
            </details>
            {error && <div className="alert error" role="alert">{error}</div>}
            <button className="button primary auth-submit" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
          </form>
          <p className="auth-footnote">Already have an account? <a className="text-link" href="/login">Log in</a></p>
        </div>
      </section>
    </AppLayout>
  )
}
