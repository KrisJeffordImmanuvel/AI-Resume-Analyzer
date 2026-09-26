import { useEffect, useState } from 'react'
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router'
import AnalysisResults, { TAB_IDS } from '../AnalysisResults.jsx'
import PageHeader from '../PageHeader.jsx'
import { getJob } from '../api.js'
import { candidateLetters } from '../candidates.js'
import useAnalysis from '../useAnalysis.js'

/** Job Provider, step 3: one candidate's full report (the same seven tabs as Job Seeker). */
export default function ProviderReport() {
  const { jobId, analysisId, tab = 'report' } = useParams()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const blind = params.get('blind') === '1'
  const query = blind ? '?blind=1' : ''
  const { result, error } = useAnalysis(analysisId)
  const [job, setJob] = useState(null)

  useEffect(() => {
    let alive = true
    getJob(jobId).then(
      (j) => alive && setJob(j),
      () => {},
    )
    return () => {
      alive = false
    }
  }, [jobId])

  const base = `/provider/jobs/${jobId}/report/${analysisId}`
  if (!TAB_IDS.includes(tab)) return <Navigate to={base + query} replace />

  const letter = job ? candidateLetters(job)[analysisId] : null
  const name = blind ? (letter ? `Candidate ${letter}` : 'Candidate') : result?.resume_filename
  return (
    <>
      <PageHeader
        title={name ? `Candidate report: ${name}` : 'Candidate report'}
        subtitle={job ? `For the job "${job.title}"` : null}
        back={{ to: `/provider/jobs/${jobId}${query}`, label: 'Back to the ranking' }}
      />
      {error && <p className="form__error" role="alert">{error}</p>}
      {!result && !error && <p className="muted">Loading…</p>}
      {result && (
        <AnalysisResults
          result={result}
          tab={tab}
          onTabChange={(next) => navigate(`${next === 'report' ? base : `${base}/${next}`}${query}`)}
        />
      )}
    </>
  )
}
