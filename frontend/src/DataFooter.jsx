import { useState } from 'react'
import { ShieldCheck, Trash2 } from 'lucide-react'
import { deleteAllData, errorMessage } from './api.js'

const DONE_KEY = 'data-deleted'
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`

function takeDoneFlag() {
  try {
    const done = sessionStorage.getItem(DONE_KEY)
    sessionStorage.removeItem(DONE_KEY)
    return done
  } catch {
    return null
  }
}

/** Where your data lives, and a way to delete all of it. */
export default function DataFooter() {
  const [done] = useState(takeDoneFlag)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function removeAll() {
    const typed = window.prompt(
      'This permanently deletes every analysis, job and candidate, including all resume text and ' +
        'everything generated from it. It cannot be undone.\n\nType DELETE to confirm.',
    )
    if (typed === null) return
    if (typed.trim().toUpperCase() !== 'DELETE') {
      setError('Nothing was deleted: the confirmation word did not match.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await deleteAllData()
      try {
        sessionStorage.setItem(DONE_KEY, `${plural(res.analyses_deleted, 'analysis', 'analyses')} and ${plural(res.jobs_deleted, 'job', 'jobs')}`)
      } catch {
        /* the page still reloads empty */
      }
      window.location.reload() // start fresh, with nothing left on screen
    } catch (e) {
      setError(errorMessage(e))
      setBusy(false)
    }
  }

  return (
    <footer className="data-footer">
      {done && (
        <p className="info" role="status">
          All your data was deleted ({done}).
        </p>
      )}
      <p className="muted">
        <ShieldCheck size={14} aria-hidden="true" />
        <span>
          Your resumes and results are stored only on this computer (backend\app.db). With AI on, the text is also
          sent to Google&apos;s Gemini to be analysed.
        </span>
      </p>
      <button type="button" className="icon-button icon-button--danger" onClick={removeAll} disabled={busy}>
        <Trash2 size={15} aria-hidden="true" /> Delete all my data
      </button>
      {error && <p className="form__error" role="alert">{error}</p>}
    </footer>
  )
}
