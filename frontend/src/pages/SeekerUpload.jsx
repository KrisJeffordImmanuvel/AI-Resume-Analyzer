import { useNavigate } from 'react-router'
import AnalyzeForm from '../AnalyzeForm.jsx'
import RecentAnalyses from '../RecentAnalyses.jsx'
import PageHeader from '../PageHeader.jsx'
import { announce } from '../Announcer.jsx'

/** Job Seeker, step 1: upload a resume and a job description (or open a saved analysis). */
export default function SeekerUpload() {
  const navigate = useNavigate()

  function openResult(result, isNew) {
    if (isNew) {
      announce(
        result.score.value === null
          ? 'Analysis ready. No score: the job description has no recognisable skills.'
          : `Analysis ready. Job-fit score ${result.score.value} out of 100.`,
      )
    }
    // Pass the result along so the analysis page shows it at once.
    navigate(`/seeker/analysis/${result.id}`, { state: { result } })
  }

  return (
    <>
      <PageHeader
        title="Analyze a resume"
        subtitle="Upload a resume and a job description. The next page shows how well they fit."
        back={{ to: '/', label: 'Home' }}
      />
      <AnalyzeForm onResult={(r) => openResult(r, true)} />
      <RecentAnalyses refreshKey={0} onOpen={(r) => openResult(r, false)} onDeleted={() => {}} />
    </>
  )
}
