import { Link } from 'react-router'
import { ArrowRight, Briefcase, User } from 'lucide-react'
import PageHeader from '../PageHeader.jsx'

/** Start page: choose Job Seeker or Job Provider. */
export default function Home() {
  return (
    <>
      <PageHeader
        title="What would you like to do?"
        subtitle="Every score and claim comes from your own documents, with the quotes to prove it."
      />
      <div className="choices">
        <Link to="/seeker" className="card choice">
          <span className="choice__icon" aria-hidden="true"><User size={24} /></span>
          <span className="choice__title">I&apos;m looking for a job</span>
          <span className="choice__text">
            Job Seeker: see how well your resume fits a job, with the evidence behind every skill, a learning
            roadmap, interview practice and resume checks.
          </span>
          <span className="choice__go">Start as a Job Seeker <ArrowRight size={16} aria-hidden="true" /></span>
        </Link>
        <Link to="/provider" className="card choice">
          <span className="choice__icon" aria-hidden="true"><Briefcase size={24} /></span>
          <span className="choice__title">I&apos;m hiring</span>
          <span className="choice__text">
            Job Provider: set a job description once, then upload candidate resumes and compare them side by side
            with the same engine.
          </span>
          <span className="choice__go">Start as a Job Provider <ArrowRight size={16} aria-hidden="true" /></span>
        </Link>
      </div>
    </>
  )
}
