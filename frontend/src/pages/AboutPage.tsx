import { AppLayout as Layout } from "../layouts/AppLayout"

const steps = [
  {
    number: "01",
    title: "Set your learning goal",
    description: "Students decide which subject, level and kind of support they need. Tutors prepare a clear profile with the subjects they teach.",
    icon: "⌕",
  },
  {
    number: "02",
    title: "Explore the right details",
    description: "Compare subjects, qualifications, experience and availability to understand whether a tutoring match could work.",
    icon: "▤",
  },
  {
    number: "03",
    title: "Send and manage requests",
    description: "Students send tutoring requests, and Tutors can review them and respond through their own workspace.",
    icon: "↗",
  },
]

const benefits = [
  ["◎", "Multiple subjects", "Tutor profiles can present more than one teaching subject, making expertise easier to discover."],
  ["▤", "Useful profile details", "Qualifications, experience and teaching levels help students make informed choices."],
  ["◷", "Availability at a glance", "Clear availability details help both sides consider practical scheduling."],
  ["↔", "Organized requests", "Tutoring conversations start with structured requests that can be reviewed and managed."],
]

function AboutLearningIllustration() {
  return (
    <div className="about-illustration" aria-label="Illustration of books, a learning dashboard and study materials" role="img">
      <div className="about-orbit about-orbit-one" />
      <div className="about-orbit about-orbit-two" />
      <div className="about-book-stack" aria-hidden="true">
        <span className="about-book about-book-back" />
        <span className="about-book about-book-middle" />
        <span className="about-book about-book-front" />
      </div>
      <div className="about-dashboard" aria-hidden="true">
        <div className="about-dashboard-top"><span /><span /><span /></div>
        <div className="about-dashboard-body">
          <div className="about-dashboard-sidebar"><i /><i /><i /><i /></div>
          <div className="about-dashboard-content">
            <b />
            <div className="about-dashboard-cards"><i /><i /><i /></div>
            <div className="about-dashboard-lines"><i /><i /><i /></div>
          </div>
        </div>
      </div>
      <div className="about-note" aria-hidden="true"><span>✦</span><b>LEARN</b><small>one step at a time</small></div>
      <div className="about-pencil" aria-hidden="true" />
      <div className="about-open-book" aria-hidden="true"><span /><span /></div>
    </div>
  )
}

export default function AboutPage() {
  return (
    <Layout>
      <div className="about-page">
        <section className="about-hero">
          <div className="about-hero-copy">
            <p className="eyebrow">ABOUT TUTORINN</p>
            <h1>Learning grows when the right knowledge <span>connects.</span></h1>
            <p>TutorInn brings Students and Tutors into one organized space—making it easier to discover teaching expertise, share learning goals and manage tutoring requests.</p>
            <a className="button primary" href="/register">Get started</a>
          </div>
          <AboutLearningIllustration />
        </section>

        <section className="about-section about-mission">
          <div className="about-section-heading">
            <p className="eyebrow">OUR MISSION</p>
            <h2>Make finding and offering learning support feel simpler.</h2>
          </div>
          <div className="about-mission-panel">
            <span className="about-mission-mark" aria-hidden="true">✦</span>
            <p>Finding the right learning support should begin with clear information, not confusion. TutorInn is designed to help Students understand their options and help Tutors present what they teach, when they are available and how they can help.</p>
          </div>
        </section>

        <section className="about-section">
          <div className="about-section-heading">
            <p className="eyebrow">HOW TUTORINN WORKS</p>
            <h2>A clear path from learning goal to tutoring request.</h2>
            <p>Each step keeps the important information easy to find.</p>
          </div>
          <div className="about-steps">
            {steps.map((step) => (
              <article className="about-step-card" key={step.number}>
                <div className="about-step-top"><span className="about-step-icon" aria-hidden="true">{step.icon}</span><span className="about-step-number">{step.number}</span></div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="about-section">
          <div className="about-section-heading">
            <p className="eyebrow">WHAT MAKES TUTORINN USEFUL</p>
            <h2>The details that help a good match take shape.</h2>
          </div>
          <div className="about-benefit-grid">
            {benefits.map(([icon, title, description]) => (
              <article className="about-benefit-card" key={title}>
                <span className="about-benefit-icon" aria-hidden="true">{icon}</span>
                <h3>{title}</h3>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="about-section about-roles">
          <div className="about-section-heading">
            <p className="eyebrow">DESIGNED FOR TWO ROLES</p>
            <h2>One platform, with a workspace for each side.</h2>
            <p>Students and Tutors see tools that support the part they play in the learning process.</p>
          </div>
          <div className="about-role-grid">
            <article className="about-role-card">
              <div className="about-role-visual student-workspace" aria-hidden="true"><span className="workspace-window"><i /><i /><i /><b /><b /><b /></span><span className="workspace-tag">LEARNING GOALS</span></div>
              <p className="eyebrow">STUDENT WORKSPACE</p>
              <h3>For Students</h3>
              <p>Explore Tutor profiles, review teaching details, describe learning needs and keep tutoring requests organized.</p>
            </article>
            <article className="about-role-card">
              <div className="about-role-visual tutor-workspace" aria-hidden="true"><span className="workspace-window"><i /><i /><i /><b /><b /><b /></span><span className="workspace-tag">TEACHING PROFILE</span></div>
              <p className="eyebrow">TUTOR WORKSPACE</p>
              <h3>For Tutors</h3>
              <p>Present subjects, qualifications, experience and availability, then review and respond to incoming requests.</p>
            </article>
          </div>
        </section>

        <section className="about-closing">
          <div><p className="eyebrow">YOUR NEXT STEP</p><h2>Bring your learning goals into focus.</h2><p>Join TutorInn to explore a more organized way to connect Students and Tutors.</p></div>
          <a className="button primary" href="/register">Join TutorInn</a>
        </section>
      </div>
    </Layout>
  )
}
