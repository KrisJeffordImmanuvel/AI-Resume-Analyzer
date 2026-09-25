import { useRef, useState } from 'react'
import { FileText, Upload, ClipboardPaste, Search, FlaskConical } from 'lucide-react'
import { MAX_TEXT_CHARS, createAnalysis, errorMessage, getSamples, isCancelled } from './api.js'
import Working from './Working.jsx'
import { announce } from './Announcer.jsx'
import { TabList, TabPanel } from './Tabs.jsx'

const RESUME_TYPES = '.pdf,.docx,.txt'
const MAX_MB = 5

function checkFile(file, allowed) {
  if (!file) return null
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (!allowed.includes(ext)) return `"${file.name}" is not a supported file type (${allowed.join(', ')}).`
  if (file.size > MAX_MB * 1024 * 1024) return `"${file.name}" is larger than ${MAX_MB} MB.`
  return null
}

export default function AnalyzeForm({ onResult }) {
  const [resumeFile, setResumeFile] = useState(null)
  const [jdMode, setJdMode] = useState('paste')
  const [jdText, setJdText] = useState('')
  const [jdFile, setJdFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [usingSample, setUsingSample] = useState(false)
  const [step, setStep] = useState('')
  const [cancelled, setCancelled] = useState(false)
  const resumeInput = useRef(null)
  const controller = useRef(null)

  const jdReady = jdMode === 'paste' ? jdText.trim().length > 0 : Boolean(jdFile)
  const canSubmit = resumeFile && jdReady && !busy

  async function run(input) {
    controller.current = new AbortController()
    setBusy(true)
    setError(null)
    setCancelled(false)
    setStep('Sending your documents…')
    announce('Analyzing. You can cancel at any time.')
    try {
      const result = await createAnalysis(input, {
        signal: controller.current.signal,
        onSent: () => setStep('Reading and scoring your documents…'),
      })
      onResult(result)
    } catch (err) {
      if (isCancelled(err)) {
        setCancelled(true)
        announce('Analysis cancelled. Nothing was saved.')
      } else {
        setError(errorMessage(err))
      }
    } finally {
      setBusy(false)
    }
  }

  function cancel() {
    controller.current?.abort()
  }

  function handleSubmit(event) {
    event.preventDefault()
    const problem =
      checkFile(resumeFile, ['.pdf', '.docx', '.txt']) ||
      (jdMode === 'upload' && checkFile(jdFile, ['.txt'])) ||
      (jdMode === 'paste' && jdText.length > MAX_TEXT_CHARS &&
        `The job description is too long (${jdText.length.toLocaleString('en-US')} characters). Please shorten it to under ${MAX_TEXT_CHARS.toLocaleString('en-US')}.`)
    if (problem) {
      setError(problem)
      return
    }
    run({ resumeFile, jdFile: jdMode === 'upload' ? jdFile : null, jdText: jdMode === 'paste' ? jdText : null })
  }

  /** Fill the form with the fictional sample documents and analyze them straight away. */
  async function trySample() {
    setError(null)
    let samples
    try {
      samples = await getSamples()
    } catch (err) {
      setError(errorMessage(err))
      return
    }
    const file = new File([samples.resume.text], samples.resume.filename, { type: 'text/plain' })
    try {
      // Show the sample's name in the file box too, so the form matches what is analyzed.
      const transfer = new DataTransfer()
      transfer.items.add(file)
      resumeInput.current.files = transfer.files
    } catch {
      /* older browsers: the note below the form still says a sample is used */
    }
    setResumeFile(file)
    setJdMode('paste')
    setJdText(samples.job_description.text)
    setUsingSample(true)
    run({ resumeFile: file, jdFile: null, jdText: samples.job_description.text })
  }

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <div className="form__head">
        <h2>Analyze a resume against a job description</h2>
        <button type="button" className="secondary" onClick={trySample} disabled={busy}>
          <FlaskConical size={16} aria-hidden="true" /> Try with sample data
        </button>
      </div>
      {usingSample && (
        <p className="info">
          Using the fictional sample resume and job description. Choose your own files below to analyze yours.
        </p>
      )}

      <label className="field">
        <span className="field__label">
          <FileText size={16} aria-hidden="true" /> Resume <small>(PDF, DOCX or TXT, up to {MAX_MB} MB)</small>
        </span>
        <input
          ref={resumeInput}
          type="file"
          accept={RESUME_TYPES}
          onChange={(e) => {
            setResumeFile(e.target.files[0] || null)
            setUsingSample(false)
          }}
        />
      </label>

      <fieldset className="field">
        <legend className="field__label">Job description</legend>
        <TabList
          id="jd"
          label="How to add the job description"
          tabs={[['paste', 'Paste text', ClipboardPaste], ['upload', 'Upload .txt', Upload]]}
          value={jdMode}
          onChange={setJdMode}
        />
        <TabPanel id="jd" value={jdMode} className="field">
          {jdMode === 'paste' ? (
            <textarea
              rows={10}
              aria-label="Job description text"
              placeholder="Paste the full job description here…"
              value={jdText}
              onChange={(e) => {
                setJdText(e.target.value)
                setUsingSample(false)
              }}
            />
          ) : (
            <input
              type="file"
              accept=".txt"
              aria-label="Job description file (.txt)"
              onChange={(e) => {
                setJdFile(e.target.files[0] || null)
                setUsingSample(false)
              }}
            />
          )}
        </TabPanel>
      </fieldset>

      {error && (
        <p className="form__error" role="alert">
          {error}
        </p>
      )}

      <div className="form__actions">
        <button type="submit" className="primary" disabled={!canSubmit}>
          <Search size={16} aria-hidden="true" />
          {busy ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>
      {busy && <Working step={step} onCancel={cancel} />}
      {cancelled && !busy && <p className="info">Analysis cancelled. Nothing was saved.</p>}
    </form>
  )
}
