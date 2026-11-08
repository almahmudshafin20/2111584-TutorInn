import { Layout } from "../components/Layout"

export default function HomePage() {
  return (
    <Layout>
      <section className="hero">
        <p className="eyebrow">LEARN WITH CONFIDENCE</p>
        <h1>Find the right tutor.<br /><span>Reach your next goal.</span></h1>
        <p className="hero-copy">TutorInn helps students discover tutors by subject and level, while tutors can manage their teaching profiles in one simple place.</p>
        <div className="actions">
          <a className="button primary" href="/tutors">Explore tutors</a>
          <a className="button secondary" href="/students">Student profiles</a>
        </div>
      </section>
      <section className="section">
        <div className="section-heading"><p className="eyebrow">HOW IT WORKS</p><h2>Everything you need to get started</h2></div>
        <div className="feature-grid">
          <article className="feature-card"><span className="feature-icon">⌕</span><h3>Discover tutors</h3><p>Search by tutor name, subject, or teaching level and open a profile for more details.</p></article>
          <article className="feature-card"><span className="feature-icon">◎</span><h3>Manage profiles</h3><p>Keep student and tutor information organized with simple create, view, edit, and delete actions.</p></article>
          <article className="feature-card"><span className="feature-icon">✓</span><h3>Built for learning</h3><p>A focused student project using React, TypeScript, FastAPI, and a database.</p></article>
        </div>
      </section>
    </Layout>
  )
}
