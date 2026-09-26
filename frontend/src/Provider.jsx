import { useEffect, useMemo, useRef, useState } from 'react'
import { Briefcase, EyeOff, Plus, Trash2, Upload, Users } from 'lucide-react'
import { addCandidates, deleteJob, errorMessage, getAnalysis, getJob, isCancelled, listJobs, removeCandidate } from './api.js'
import Working from './Working.jsx'
import FileDrop from './FileDrop.jsx'
import AnalysisResults from './AnalysisResults.jsx'
import Comparison from './Comparison.jsx'
import NewJobForm from './NewJobForm.jsx'
import { announce } from './Announcer.jsx'

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
const letter = (i) => (i < 26 ? String.fromCharCode(65 + i) : `${String.fromCharCode(65 + Math.floor(i / 26) - 1)}${String.fromCharCode(65 + (i % 26))}`)

export default function Provider() {
  const [jobs, setJobs] = useState([])
  const [job, setJob] = useState(null)
  const [creating, setCreating] = useState(false)
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [outcomes, setOutcomes] = useState([])
  const [error, setError] = useState(null)
  const [blind, setBlind] = useState(false)
  const [open, setOpen] = useState(null)
  const [progress, setProgress] = useState(null) // { index, total, name }
  const fileInput = useRef(null)
  const reportRef = useRef(null)
  const controller = useRef(null)

  useEffect(() => {
    listJobs()
      .then((list) => {
        setJobs(list)
        if (list.length === 0) setCreating(true)
      })
      .catch((e) => setError(errorMessage(e)))
  }, [])

  // Blind labels follow upload order, so they don't change when the ranking does.
  const labels = useMemo(() => {
    const ids = (job?.candidates || []).map((c) => c.analysis_id).sort((a, b) => a - b)
    return Object.fromEntries(ids.map((id, i) => [id, letter(i)]))
  }, [job])

  async function selectJob(id) {
    setError(null)
    setOutcomes([])
    setOpen(null)
    if (!id) return setJob(null)
    try {
      setJob(await getJob(id))
      setCreating(false)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  function onCreated(newJob) {
    setJobs((list) => [newJob, ...list])
    setJob(newJob)
    setCreating(false)
    setOutcomes([])
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
        setJobs((list) => list.map((j) => (j.id === res.job.id ? { ...j, candidate_count: res.job.candidate_count } : j)))
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
      const fresh = await getJob(job.id)
      setJob(fresh)
      setJobs((list) => list.map((j) => (j.id === fresh.id ? { ...j, candidate_count: fresh.candidate_count } : j)))
      if (open?.id === c.analysis_id) setOpen(null)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  async function removeJob() {
    const n = job.candidates.length
    const also = n ? ` and its ${n} candidate${n === 1 ? '' : 's'} (their resumes and reports)` : ''
    if (!window.confirm(`Delete the job "${job.title}"${also}? This cannot be undone.`)) return
    setError(null)
    try {
      await deleteJob(job.id)
      const rest = jobs.filter((j) => j.id !== job.id)
      setJobs(rest)
      setJob(null)
      setOpen(null)
      setOutcomes([])
      if (rest.length === 0) setCreating(true)
      announce(`Job "${job.title}" deleted.`)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  async function openReport(analysisId) {
    try {
      setOpen(await getAnalysis(analysisId))
      setTimeout(() => {
        const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
        reportRef.current?.focus({ preventScroll: true })
        reportRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
      }, 50)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  const tooMany = files.length > MAX_FILES
  const problems = fileProblems(files)
  return (
    <>
      <section className="card">
        <h2><Briefcase size={18} aria-hidden="true" /> Job</h2>
        <div className="inline-form">
          <label className="sr-only" htmlFor="job-select">Choose a job</label>
          <select id="job-select" className="text-input" value={job?.id || ''} onChange={(e) => selectJob(Number(e.target.value) || null)}>
            <option value="">{jobs.length ? 'Choose a saved job…' : 'No saved jobs yet'}</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title} ({j.candidate_count} candidate{j.candidate_count === 1 ? '' : 's'})
              </option>
            ))}
          </select>
          <button type="button" className="icon-button" onClick={() => setCreating(true)} disabled={creating}>
            <Plus size={15} aria-hidden="true" /> New job
          </button>
          {job && !creating && (
            <button type="button" className="icon-button icon-button--danger" onClick={removeJob}>
              <Trash2 size={15} aria-hidden="true" /> Delete job
            </button>
          )}
        </div>
        {creating && <NewJobForm onCreated={onCreated} onCancel={jobs.length ? () => setCreating(false) : null} />}
        {job && !creating && (
          <details className="jd-details">
            <summary>Job description ({job.jd_source === 'upload' ? job.jd_filename : 'pasted'})</summary>
            <pre className="raw" tabIndex={0} role="region" aria-label="Job description text">{job.jd_text}</pre>
          </details>
        )}
        {error && <p className="form__error" role="alert">{error}</p>}
      </section>

      {job && (
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
      )}

      {job && job.candidates.length > 0 && (
        <>
          <label className="blind-toggle">
            <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} />
            <EyeOff size={16} aria-hidden="true" /> Blind review: hide file names and show Candidate A, B, C…
          </label>
          <Comparison job={job} blind={blind} labels={labels} onOpen={openReport} onRemove={remove} openId={open?.id} />
        </>
      )}
      {job && job.candidates.length === 0 && !busy && (
        <p className="muted">No candidates yet. Add resumes above to compare them.</p>
      )}

      {open && (
        <section ref={reportRef} className="provider-report" tabIndex={-1} aria-label="Candidate report">
          <h2 className="provider-report__title">
            Full report: {blind ? `Candidate ${labels[open.id]}` : open.resume_filename}
            <button type="button" className="icon-button" onClick={() => setOpen(null)}>Close</button>
          </h2>
          <AnalysisResults key={open.id} result={open} />
        </section>
      )}
    </>
  )
}
