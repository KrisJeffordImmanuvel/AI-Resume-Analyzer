import { useState } from 'react'
import { ClipboardPaste, Loader2, Plus } from 'lucide-react'
import { createJob, errorMessage } from './api.js'
import { announce } from './Announcer.jsx'
import FileDrop from './FileDrop.jsx'
import { TabList, TabPanel } from './Tabs.jsx'

/** Create a job: a title and the job description (pasted or a .txt file). */
export default function NewJobForm({ onCreated, onCancel }) {
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
      <div className="field" role="group" aria-labelledby="job-jd-label">
        <div className="field__row">
          <span className="field__label" id="job-jd-label">
            <ClipboardPaste size={16} aria-hidden="true" /> Job description
          </span>
          <TabList
            className="toggle"
            id="job-jd"
            label="How to add the job description"
            tabs={[['paste', 'Paste text'], ['upload', 'Upload .txt']]}
            value={mode}
            onChange={setMode}
          />
        </div>
        <TabPanel id="job-jd" value={mode} className="field">
          {mode === 'paste' ? (
            <textarea rows={8} value={text} onChange={(e) => setText(e.target.value)} aria-label="Job description text"
              placeholder="Paste the full job description…" />
          ) : (
            <FileDrop id="job-jd-file" label="Job description file (.txt)" hint="A .txt file" accept=".txt"
              files={[file]} onFiles={(list) => setFile(list[0] || null)} />
          )}
        </TabPanel>
      </div>
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
