import { useNavigate } from 'react-router'
import NewJobForm from '../NewJobForm.jsx'
import PageHeader from '../PageHeader.jsx'

/** Job Provider: create a job, then go straight to it to add candidates. */
export default function ProviderNewJob() {
  const navigate = useNavigate()
  return (
    <>
      <PageHeader
        title="New job"
        subtitle="Paste the job description or upload it as a .txt file. You add candidates on the next page."
        back={{ to: '/provider', label: 'Your jobs' }}
      />
      <section className="card">
        <NewJobForm
          onCreated={(job) => navigate(`/provider/jobs/${job.id}`, { replace: true })}
          onCancel={() => navigate('/provider')}
        />
      </section>
    </>
  )
}
