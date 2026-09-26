import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { Briefcase, ChevronRight, Plus, Users } from 'lucide-react'
import { errorMessage, listJobs } from '../api.js'
import PageHeader from '../PageHeader.jsx'

const day = (iso) => new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })

/** Job Provider, step 1: your saved jobs. */
export default function ProviderJobs() {
  const [state, setState] = useState({ jobs: null, error: null })

  useEffect(() => {
    let alive = true
    listJobs().then(
      (jobs) => alive && setState({ jobs, error: null }),
      (err) => alive && setState({ jobs: [], error: errorMessage(err) }),
    )
    return () => {
      alive = false
    }
  }, [])

  const { jobs, error } = state
  const newJob = (
    <Link to="/provider/new" className="primary">
      <Plus size={16} aria-hidden="true" /> New job
    </Link>
  )
  return (
    <>
      <PageHeader
        title="Your jobs"
        subtitle="Set a job description once, then compare candidate resumes against it."
        back={{ to: '/', label: 'Home' }}
        actions={jobs?.length ? newJob : null}
      />
      {error && <p className="form__error" role="alert">{error}</p>}
      {!jobs && <p className="muted">Loading…</p>}
      {jobs && jobs.length === 0 && !error && (
        <section className="card empty">
          <Briefcase size={28} aria-hidden="true" className="empty__icon" />
          <h2>No jobs yet</h2>
          <p className="muted">Create a job to start comparing candidates.</p>
          {newJob}
        </section>
      )}
      {jobs && jobs.length > 0 && (
        <ul className="job-list">
          {jobs.map((j) => (
            <li key={j.id}>
              <Link to={`/provider/jobs/${j.id}`} className="card job-link">
                <span className="job-link__main">
                  <strong>{j.title}</strong>
                  <span className="muted">
                    <Users size={14} aria-hidden="true" /> {j.candidate_count} candidate{j.candidate_count === 1 ? '' : 's'} ·
                    created {day(j.created_at)}
                  </span>
                </span>
                <ChevronRight size={20} aria-hidden="true" className="job-link__chevron" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
