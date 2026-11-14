import { AppLayout as Layout } from "../layouts/AppLayout"

export default function AboutPage() {
  return (
    <Layout>
      <section className="page-intro about-intro">
        <p className="eyebrow">ABOUT TUTORINN</p>
        <h1>Learning starts with the right connection.</h1>
        <p>TutorInn brings Students and Tutors together through clear profiles, useful discovery tools and straightforward tutoring workflows.</p>
      </section>
      <section className="about-grid">
        <article className="about-card"><span className="feature-icon" aria-hidden="true">◎</span><h2>For Students</h2><p>Describe what you want to learn, explore tutor profiles and manage your tutoring requests in one workspace.</p></article>
        <article className="about-card"><span className="feature-icon" aria-hidden="true">✦</span><h2>For Tutors</h2><p>Present your subjects, qualifications, experience and availability, then review requests from Students.</p></article>
        <article className="about-card"><span className="feature-icon" aria-hidden="true">◇</span><h2>Built around clarity</h2><p>Role-specific workspaces keep the right tools and information easy to find while protecting account access.</p></article>
      </section>
      <section className="content-panel about-technology"><p className="eyebrow">OUR PLATFORM</p><h2>Designed to keep learning organized.</h2><p>TutorInn is built with React and TypeScript, FastAPI and PostgreSQL. The platform keeps its public experience, account workflows and tutoring tools connected through a consistent application architecture.</p></section>
    </Layout>
  )
}
