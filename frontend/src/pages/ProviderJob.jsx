import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router'
import { EyeOff, Trash2, Upload, Users } from 'lucide-react'
import { addCandidates, deleteJob, errorMessage, getJob, isCancelled, removeCandidate } from '../api.js'
import Working from '../Working.jsx'
import FileDrop from '../FileDrop.jsx'
import Comparison from '../Comparison.jsx'
import PageHeader from '../PageHeader.jsx'
import { announce } from '../Announcer.jsx'
import { candidateLetters } from '../candidates.js'

const MAX_FILES = 10
const MAX_MB = 5
const RESUME_TYPES = ['.pdf', '.docx', '.txt']

/** Problems the browser can spot before uploading; the server checks again. */
function fileProblems(files) {
  return files.flatMap((f) => {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase()
    if (!RESUME_TYPES.includes(ext)) return [`"${f.name}" is not a PDF, DOCX or TXT file.`]
    if (f.size > MAX_MB * 1024 * 1024) return [`"${f.name}" is larger than ${MAX_MB} MB.`]
    return []
  })
}

/** Job Provider, step 2: one job. Add candidates, then compare them (ranking and skill matrix). */
export default function ProviderJob() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  // Kept in the address too (?blind=1), so a candidate's report and Back keep blind review on.
  const [blind, setBlindState] = useState(params.get('blind') === '1')
  const [job, setJob] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [error, setError] = useState(null)
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [outcomes, setOutcomes] = useState([])
  const [progress, setProgress] = useState(null) // { index, total, name }
  const fileInput = useRef(null)
  const controller = useRef(null)

  useEffect(() => {
    let alive = true
    getJob(jobId).then(
      (j) => alive && setJob(j),
      (err) => alive && setLoadError(errorMessage(err)),
    )
    return () => {
      alive = false
    }
  }, [jobId])

  const labels = useMemo(() => candidateLetters(job), [job])

  function setBlind(on) {
    setBlindState(on)
    setParams(on ? { blind: '1' } : {}, { replace: true })
  }

  /** One request per resume, so each shows progress, fills the ranking as it finishes and can be cancelled. */
  async function upload() {
    const batch = files
    controller.current = new AbortController()
    setBusy(true)
    setError(null)
    setOutcomes([])
    announce(`Analysing ${batch.length} resume${batch.length === 1 ? '' : 's'}. You can cancel at any time.`)
    const results = []
    let stopped = false
    for (const [index, file] of batch.entries()) {
      if (stopped) {
        results.push({ filename: file.name, status: 'cancelled', message: 'not added (cancelled)' })
        continue
      }
      setProgress({ index, total: batch.length, name: file.name })
      try {
        const res = await addCandidates(job.id, [file], { signal: controller.current.signal })
        results.push(...res.outcomes)
        setJob(res.job)
      } catch (e) {
        if (isCancelled(e)) {
          stopped = true
          results.push({ filename: file.name, status: 'cancelled', message: 'not added (cancelled)' })
        } else {
          results.push({ filename: file.name, status: 'error', message: errorMessage(e) })
        }
      }
      setOutcomes([...results])
    }
    const added = results.filter((o) => o.status === 'added').length
    const other = results.length - added
    announce(
      `${stopped ? 'Stopped. ' : ''}${added} candidate${added === 1 ? '' : 's'} added${other ? `, ${other} not added (see the list)` : ''}.`,
    )
    setProgress(null)
    setBusy(false)
    setFiles([])
    if (fileInput.current) fileInput.current.value = ''
  }

  async function remove(c) {
    const label = blind ? `Candidate ${labels[c.analysis_id]}` : c.filename
    if (!window.confirm(`Remove ${label} from this comparison? The analysis itself is kept.`)) return
    try {
      await removeCandidate(job.id, c.analysis_id)
      setJob(await getJob(job.id))
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  async function removeJob() {
    const n = job.candidates.length
    const also = n ? ` and its ${n} candidate${n === 1 ? '' : 's'} (their resumes and reports)` : ''
    if (!window.confirm(`Delete the job "${job.title}"${also}? This cannot be undone.`)) return
    try {
      await deleteJob(job.id)
      announce(`Job "${job.title}" deleted.`)
      navigate('/provider', { replace: true })
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  function openReport(analysisId) {
    navigate(`/provider/jobs/${job.id}/report/${analysisId}${blind ? '?blind=1' : ''}`)
  }

  const back = { to: '/provider', label: 'Your jobs' }
  if (loadError) {
    return (
      <>
        <PageHeader title="Job not found" back={back} />
        <p className="form__error" role="alert">{loadError}</p>
      </>
    )
  }
  if (!job) {
    return (
      <>
        <PageHeader title="Job" back={back} />
        <p className="muted">Loading…</p>
      </>
    )
  }

  const tooMany = files.length > MAX_FILES
  const problems = fileProblems(files)
  const count = job.candidates.length
  return (
    <>
      <PageHeader
        title={job.title}
        subtitle={`${count} candidate${count === 1 ? '' : 's'} · job description ${job.jd_source === 'upload' ? `from ${job.jd_filename}` : 'pasted'}`}
        back={back}
        actions={
          <button type="button" className="icon-button icon-button--danger" onClick={removeJob}>
            <Trash2 size={15} aria-hidden="true" /> Delete job
          </button>
        }
      />
      <details className="card jd-card">
        <summary>Show the job description</summary>
        <pre className="raw" tabIndex={0} role="region" aria-label="Job description text">{job.jd_text}</pre>
      </details>
      {error && <p className="form__error" role="alert">{error}</p>}

      <section className="card">
        <h2><Users size={18} aria-hidden="true" /> Add candidates</h2>
        <p className="muted">
          Upload up to {MAX_FILES} resumes at a time (PDF, DOCX or TXT). Each one is analysed with exactly the same
          engine as Job Seeker mode.
        </p>
        <FileDrop id="candidate-files" multiple inputRef={fileInput} accept=".pdf,.docx,.txt" files={files}
          label={`Candidate resumes (up to ${MAX_FILES})`} hint={`Up to ${MAX_FILES} resumes: PDF, DOCX or TXT, 5 MB each`}
          onFiles={setFiles} />
        {tooMany && <p className="form__error" role="alert">Choose at most {MAX_FILES} files.</p>}
        {problems.length > 0 && (
          <ul className="outcomes" role="alert">
            {problems.map((p) => (
              <li key={p} className="outcome outcome--error">{p} Remove it from the selection to continue.</li>
            ))}
          </ul>
        )}
        <div className="form__actions">
          <button type="button" className="primary" onClick={upload} disabled={busy || files.length === 0 || tooMany || problems.length > 0}>
            <Upload size={16} aria-hidden="true" />
            {busy ? 'Adding candidates…' : `Add ${files.length || ''} candidate${files.length === 1 ? '' : 's'}`}
          </button>
        </div>
        {progress && (
          <Working
            key={progress.index}
            step={`Analysing resume ${progress.index + 1} of ${progress.total}: ${progress.name}`}
            onCancel={() => controller.current?.abort()}
            cancelLabel={progress.total > 1 ? 'Cancel the rest' : 'Cancel'}
          />
        )}
        {outcomes.length > 0 && (
          <ul className="outcomes">
            {outcomes.map((o, i) => (
              <li key={i} className={`outcome outcome--${o.status}`}>
                <strong>{o.filename}</strong>: {o.status === 'added' ? 'added' : o.message}
              </li>
            ))}
          </ul>
        )}
      </section>

      {count > 0 && (
        <>
          <label className="blind-toggle">
            <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} />
            <EyeOff size={16} aria-hidden="true" /> Blind review: hide file names and show Candidate A, B, C…
          </label>
          <Comparison job={job} blind={blind} labels={labels} onOpen={openReport} onRemove={remove} />
        </>
      )}
      {count === 0 && !busy && <p className="muted">No candidates yet. Add resumes above to compare them.</p>}
    </>
  )
}
