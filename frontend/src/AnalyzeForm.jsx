import { useState } from 'react'
import { FileText, Upload, ClipboardPaste, Loader2, Search } from 'lucide-react'
import { createAnalysis, errorMessage } from './api.js'

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

  const jdReady = jdMode === 'paste' ? jdText.trim().length > 0 : Boolean(jdFile)
  const canSubmit = resumeFile && jdReady && !busy

  async function handleSubmit(event) {
    event.preventDefault()
    const problem =
      checkFile(resumeFile, ['.pdf', '.docx', '.txt']) || (jdMode === 'upload' && checkFile(jdFile, ['.txt']))
    if (problem) {
      setError(problem)
      return
    }
    setBusy(true)
    setError(null)
    try {
      const result = await createAnalysis({
        resumeFile,
        jdFile: jdMode === 'upload' ? jdFile : null,
        jdText: jdMode === 'paste' ? jdText : null,
      })
      onResult(result)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <h2>Analyze a resume against a job description</h2>

      <label className="field">
        <span className="field__label">
          <FileText size={16} aria-hidden="true" /> Resume <small>(PDF, DOCX or TXT, up to {MAX_MB} MB)</small>
        </span>
        <input type="file" accept={RESUME_TYPES} onChange={(e) => setResumeFile(e.target.files[0] || null)} />
      </label>

      <fieldset className="field">
        <legend className="field__label">Job description</legend>
        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={jdMode === 'paste'}
            className={jdMode === 'paste' ? 'tab tab--active' : 'tab'}
            onClick={() => setJdMode('paste')}
          >
            <ClipboardPaste size={16} aria-hidden="true" /> Paste text
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={jdMode === 'upload'}
            className={jdMode === 'upload' ? 'tab tab--active' : 'tab'}
            onClick={() => setJdMode('upload')}
          >
            <Upload size={16} aria-hidden="true" /> Upload .txt
          </button>
        </div>
        {jdMode === 'paste' ? (
          <textarea
            rows={10}
            placeholder="Paste the full job description here…"
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
          />
        ) : (
          <input type="file" accept=".txt" onChange={(e) => setJdFile(e.target.files[0] || null)} />
        )}
      </fieldset>

      {error && (
        <p className="form__error" role="alert">
          {error}
        </p>
      )}

      <button type="submit" className="primary" disabled={!canSubmit}>
        {busy ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Search size={16} aria-hidden="true" />}
        {busy ? 'Analyzing…' : 'Analyze'}
      </button>
    </form>
  )
}
