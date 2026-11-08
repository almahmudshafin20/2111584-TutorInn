import { Layout } from "../components/Layout"

export default function AboutPage() {
  return <Layout>
    <section className="page-intro"><p className="eyebrow">ABOUT TUTORINN</p><h1>Learning starts with the right connection.</h1><p>TutorInn is a simple tutoring platform concept designed to help students find suitable tutors and help tutors present their teaching experience.</p></section>
    <section className="content-panel"><h2>Our goal</h2><p>Make tutor discovery and profile management clear and accessible. Students can browse tutor information, while both students and tutors have profile management screens for the project MVP.</p><h2>How it is built</h2><p>The frontend uses React and TypeScript. FastAPI provides REST endpoints, and SQLAlchemy connects the API to a persistent database configured through <code>DATABASE_URL</code>.</p><a className="text-link" href="/tutors">Start exploring tutors →</a></section>
  </Layout>
}
