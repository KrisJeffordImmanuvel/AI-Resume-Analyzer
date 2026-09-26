import { Link, Navigate, useNavigate, useParams } from 'react-router'
import { Plus } from 'lucide-react'
import AnalysisResults, { TAB_IDS } from '../AnalysisResults.jsx'
import PageHeader from '../PageHeader.jsx'
import useAnalysis from '../useAnalysis.js'

const when = (iso) => new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })

/** Job Seeker, step 2: the analysis. Each report tab has its own address (…/analysis/12/roadmap). */
export default function AnalysisPage() {
  const { id, tab = 'report' } = useParams()
  const navigate = useNavigate()
  const { result, error } = useAnalysis(id)
  const base = `/seeker/analysis/${id}`

  if (!TAB_IDS.includes(tab)) return <Navigate to={base} replace />

  const newAnalysis = (
    <Link to="/seeker" className="secondary">
      <Plus size={16} aria-hidden="true" /> New analysis
    </Link>
  )
  return (
    <>
      <PageHeader
        title={result ? `Analysis: ${result.resume_filename}` : 'Analysis'}
        subtitle={
          result &&
          `Against the job description ${result.jd_filename ? `"${result.jd_filename}"` : 'you pasted'} · ${when(result.created_at)}`
        }
        back={{ to: '/seeker', label: 'Upload page' }}
        actions={newAnalysis}
      />
      {error && <p className="form__error" role="alert">{error}</p>}
      {!result && !error && <p className="muted">Loading…</p>}
      {result && (
        <AnalysisResults
          result={result}
          tab={tab}
          onTabChange={(next) => navigate(next === 'report' ? base : `${base}/${next}`)}
        />
      )}
    </>
  )
}
