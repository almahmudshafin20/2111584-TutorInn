import { AppLayout as Layout } from "../layouts/AppLayout"

const features = [
  { icon: "⌕", title: "Find the right tutor", description: "Explore tutor profiles and narrow your search by subject, level and experience." },
  { icon: "◎", title: "Make learning personal", description: "Share your learning goals and find teaching support that fits your needs." },
  { icon: "✓", title: "Keep everything clear", description: "Manage tutoring requests, responses and profile information in one place." },
]

export default function HomePage() {
  return (
    <Layout>
      <section className="hero">
        <div className="hero-content">
          <p className="eyebrow">LEARN WITH CONFIDENCE</p>
          <h1>Find the right tutor.<br /><span>Move forward with confidence.</span></h1>
          <p className="hero-copy">A welcoming place for Students to discover tutors and for Tutors to share their experience, connect and support learning.</p>
          <div className="actions">
            <a className="button primary" href="/tutors">Explore tutors</a>
            <a className="button secondary" href="/register">Join TutorInn</a>
          </div>
          <p className="hero-note">A clearer way to connect around learning.</p>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="hero-visual-card hero-visual-main"><span className="hero-visual-icon">✦</span><strong>Learning, connected.</strong><span>Find support for your next goal.</span></div>
          <div className="hero-visual-card hero-visual-float"><span className="hero-float-dot" /><strong>Good progress starts here</strong><span>Student · Tutor · Together</span></div>
          <div className="hero-visual-orb" />
        </div>
      </section>
      <section className="section">
        <div className="section-heading"><p className="eyebrow">A BETTER WAY TO LEARN</p><h2>Everything you need to make the next connection</h2><p>Simple tools for finding support, sharing experience and keeping tutoring organized.</p></div>
        <div className="feature-grid">
          {features.map(feature => <article className="feature-card" key={feature.title}><span className="feature-icon" aria-hidden="true">{feature.icon}</span><h3>{feature.title}</h3><p>{feature.description}</p></article>)}
        </div>
      </section>
      <section className="home-steps">
        <div><p className="eyebrow">HOW IT WORKS</p><h2>Start with what you need.</h2></div>
        <ol><li><span>01</span><div><strong>Create your account</strong><p>Choose whether you are joining as a Student or Tutor.</p></div></li><li><span>02</span><div><strong>Build your profile</strong><p>Share your subjects, goals, experience and availability.</p></div></li><li><span>03</span><div><strong>Connect and make progress</strong><p>Discover tutors, review requests and manage responses.</p></div></li></ol>
      </section>
    </Layout>
  )
}
