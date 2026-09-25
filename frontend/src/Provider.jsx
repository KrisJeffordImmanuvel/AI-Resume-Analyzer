import { useEffect, useMemo, useRef, useState } from 'react'
import { Briefcase, ClipboardPaste, EyeOff, FileText, Loader2, Plus, Trash2, Upload, Users, Check, Minus, X, Info } from 'lucide-react'
import { addCandidates, createJob, deleteJob, errorMessage, getAnalysis, getJob, isCancelled, listJobs, removeCandidate } from './api.js'
import Working from './Working.jsx'
import AnalysisResults from './AnalysisResults.jsx'
import { announce } from './Announcer.jsx'
import { TabList, TabPanel } from './Tabs.jsx'

const PRIORITY_LABEL = { required: 'Required', standard: 'Mentioned', preferred: 'Nice to have' }
const PRIORITY_SHORT = { required: 'Req', standard: 'Mid', preferred: 'Nice' }
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

function NewJobForm({ onCreated, onCancel }) {
  const [title, setTitle] = useState('')
  const [mode, setMode] = useState('paste')
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const ready = mode === 'paste' ? text.trim() : file

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const created = await createJob({ title: title.trim(), jdFile: mode === 'upload' ? file : null, jdText: text })
      announce(`Job "${created.title}" created. You can now add candidates.`)
      onCreated(created)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="form" onSubmit={submit}>
      <label className="field">
        <span className="field__label">Job title <small>(optional; defaults to the first line)</small></span>
        <input className="text-input" type="text" maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <fieldset className="field">
        <legend className="field__label">Job description</legend>
        <TabList
          id="job-jd"
          label="How to add the job description"
          tabs={[['paste', 'Paste text', ClipboardPaste], ['upload', 'Upload .txt', Upload]]}
          value={mode}
          onChange={setMode}
        />
        <TabPanel id="job-jd" value={mode} className="field">
          {mode === 'paste' ? (
            <textarea rows={8} value={text} onChange={(e) => setText(e.target.value)} aria-label="Job description text"
              placeholder="Paste the full job description…" />
          ) : (
            <input type="file" accept=".txt" aria-label="Job description file (.txt)" onChange={(e) => setFile(e.target.files[0] || null)} />
          )}
        </TabPanel>
      </fieldset>
      {error && <p className="form__error" role="alert">{error}</p>}
      <div className="form__actions">
        <button type="submit" className="primary" disabled={busy || !ready}>
          {busy ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Plus size={16} aria-hidden="true" />}
          Create job
        </button>
        {onCancel && (
          <button type="button" className="icon-button" onClick={onCancel}>Cancel</button>
        )}
      </div>
    </form>
  )
}

const CELL = {
  named: [Check, 'Named', 'cell--named'],
  related: [Minus, 'Related (half)', 'cell--related'],
  missing: [X, 'Missing', 'cell--missing'],
}

/** A matrix cell. With resume evidence it is a button that shows the quote below the table (keyboard and touch too). */
function Cell({ cell, skill, candidate, shown, onShow }) {
  const [Icon, text, cls] = CELL[cell.status]
  const content = (
    <>
      <Icon size={14} aria-hidden="true" />
      <span className="matrix-cell__text">{text}</span>
    </>
  )
  if (!cell.quote) return <span className={`matrix-cell ${cls}`}>{content}</span>
  return (
    <button
      type="button"
      className={`matrix-cell matrix-cell--button ${cls}${shown ? ' matrix-cell--shown' : ''}`}
      title={`“${cell.quote}”`}
      aria-label={`${skill}, ${candidate}: ${text}. Show the resume line`}
      aria-expanded={shown}
      aria-controls="matrix-quote"
      onClick={onShow}
    >
      {content}
    </button>
  )
}

function Comparison({ job, blind, labels, onOpen, onRemove, openId }) {
  const [picked, setPicked] = useState(null) // { skill, id }
  const name = (c) => (blind ? `Candidate ${labels[c.analysis_id]}` : c.filename)
  const pickedCandidate = picked && job.candidates.find((c) => c.analysis_id === picked.id)
  const pickedCell = pickedCandidate?.cells[picked.skill]
  const short = (c) => (blind ? labels[c.analysis_id] : c.filename.replace(/\.(pdf|docx|txt)$/i, ''))
  return (
    <>
      <section className="card">
        <h2>Ranking</h2>
        <p className="method"><Info size={14} aria-hidden="true" /> {job.label}</p>
        <div className="table-scroll">
          <table className="breakdown roles ranking">
            <thead>
              <tr>
                <th>#</th>
                <th>Candidate</th>
                <th>Fit</th>
                <th className="hide-narrow">Required</th>
                <th className="hide-narrow"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {job.candidates.map((c) => (
                <tr key={c.analysis_id} className={openId === c.analysis_id ? 'row-open' : ''}>
                  <td>{c.rank}</td>
                  <td>
                    {name(c)}
                    <div className="role-missing">
                      {c.missing_required.length ? `Missing: ${c.missing_required.join(', ')}` : 'All required skills found'}
                      {c.extraction === 'ai' ? ' · AI profile' : ''}
                    </div>
                    <div className="only-narrow narrow-meta">
                      Required {c.required_matched} of {c.required_total}
                      {c.required_related > 0 && ` (+${c.required_related} related)`}
                      <span className="narrow-actions">
                        <button type="button" className="icon-button" onClick={() => onOpen(c.analysis_id)}>
                          <FileText size={15} aria-hidden="true" /> Report
                        </button>
                        <button type="button" className="icon-button" onClick={() => onRemove(c)} aria-label={`Remove ${name(c)}`}>
                          <Trash2 size={15} aria-hidden="true" />
                        </button>
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="fit-cell">
                      <span className="fit-value">{c.score ?? '—'}</span>
                      <span className="fit-bar" aria-hidden="true"><span style={{ width: `${c.score || 0}%` }} /></span>
                    </div>
                  </td>
                  <td className="hide-narrow">
                    {c.required_matched} of {c.required_total}
                    {c.required_related > 0 && <span className="role-related"> +{c.required_related} related</span>}
                  </td>
                  <td className="actions hide-narrow">
                    <button type="button" className="icon-button" onClick={() => onOpen(c.analysis_id)}>
                      <FileText size={15} aria-hidden="true" /> Report
                    </button>
                    <button type="button" className="icon-button" onClick={() => onRemove(c)} aria-label={`Remove ${name(c)}`}>
                      <Trash2 size={15} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Skill matrix</h2>
        <p className="muted">
          Each job skill against each candidate. Named: the resume names the skill (full credit). Related: the resume only relates to it (half credit). Missing: no evidence. Select a Named or Related cell to see the resume line it is based on.
        </p>
        {!blind && (
          <p className="muted matrix-key only-narrow">
            {job.candidates.map((c) => `${labels[c.analysis_id]} = ${c.filename}`).join(' · ')}
          </p>
        )}
        <div className="table-scroll matrix-scroll" role="region" aria-label="Skill matrix table" tabIndex={0}>
          <table className="matrix">
            <thead>
              <tr>
                <th className="matrix-skill">Skill</th>
                {job.candidates.map((c) => (
                  <th key={c.analysis_id} title={name(c)}>
                    <span className="matrix-head hide-narrow">{short(c)}</span>
                    <span className="only-narrow">{labels[c.analysis_id]}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {job.skills.map((s) => (
                <tr key={s.skill}>
                  <th className="matrix-skill" scope="row">
                    {s.skill}{' '}
                    <span className={`badge badge--${s.priority}`} title={PRIORITY_LABEL[s.priority]}>
                      <span className="hide-narrow">{PRIORITY_LABEL[s.priority]}</span>
                      <span className="only-narrow" aria-hidden="true">{PRIORITY_SHORT[s.priority]}</span>
                      <span className="sr-only only-narrow-sr">{PRIORITY_LABEL[s.priority]}</span>
                    </span>
                  </th>
                  {job.candidates.map((c) => (
                    <td key={c.analysis_id}>
                      <Cell
                        cell={c.cells[s.skill]}
                        skill={s.skill}
                        candidate={name(c)}
                        shown={picked?.skill === s.skill && picked?.id === c.analysis_id}
                        onShow={() =>
                          setPicked((p) => (p?.skill === s.skill && p?.id === c.analysis_id ? null : { skill: s.skill, id: c.analysis_id }))
                        }
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div id="matrix-quote" className="matrix-quote" aria-live="polite">
          {pickedCell?.quote && (
            <>
              <p>
                <strong>{picked.skill}</strong> · {name(pickedCandidate)} · {CELL[pickedCell.status][1]}
              </p>
              <blockquote className="quote">{pickedCell.quote}</blockquote>
            </>
          )}
        </div>
      </section>
    </>
  )
}

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
          <input ref={fileInput} type="file" multiple accept=".pdf,.docx,.txt" aria-label={`Candidate resumes (up to ${MAX_FILES})`}
            onChange={(e) => setFiles([...e.target.files])} />
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
