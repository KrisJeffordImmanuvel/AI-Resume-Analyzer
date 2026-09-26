import { useState } from 'react'
import { Database, LogOut, ShieldCheck, Trash2 } from 'lucide-react'
import { deleteAllData, errorMessage } from '../api.js'
import PageHeader from '../PageHeader.jsx'
import { useAuth } from '../auth.js'

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

/** Settings: where your data lives, and deleting all of it. */
export default function Settings() {
  const [done] = useState(takeDoneFlag)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const auth = useAuth()

  async function logOut() {
    setError(null)
    try {
      await auth.signOut()
    } catch (e) {
      setError(errorMessage(e))
    }
  }

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
    <>
      <PageHeader title="Settings" back={{ to: '/', label: 'Home' }} />
      {done && (
        <p className="info settings-done" role="status">
          All your data was deleted ({done}).
        </p>
      )}
      <section className="card" aria-labelledby="data-title">
        <h2 id="data-title"><Database size={18} aria-hidden="true" /> Your data</h2>
        <p className="settings-note">
          <ShieldCheck size={16} aria-hidden="true" />
          {auth.required ? (
            <span>
              Your resumes and results are stored in this private site&apos;s database, behind its password. With
              AI on, the text is also sent to Google&apos;s Gemini to be analysed.
            </span>
          ) : (
            <span>
              Your resumes and results are stored only on this computer (backend\app.db). With AI on, the text is
              also sent to Google&apos;s Gemini to be analysed.
            </span>
          )}
        </p>
        <div className="danger-zone">
          <div>
            <strong>Delete all my data</strong>
            <p className="muted">
              Permanently deletes every analysis, job and candidate, including all resume text and everything
              generated from it. You are asked to type DELETE first.
            </p>
          </div>
          <button type="button" className="icon-button icon-button--danger" onClick={removeAll} disabled={busy}>
            <Trash2 size={15} aria-hidden="true" /> Delete all my data
          </button>
        </div>
        {error && <p className="form__error" role="alert">{error}</p>}
      </section>
      {auth.required && (
        <section className="card" aria-labelledby="session-title">
          <h2 id="session-title"><LogOut size={18} aria-hidden="true" /> Sign out</h2>
          <div className="settings-row">
            <p className="muted">Signs this browser out of the private site. You need the password to come back in.</p>
            <button type="button" className="icon-button" onClick={logOut}>
              <LogOut size={15} aria-hidden="true" /> Sign out
            </button>
          </div>
        </section>
      )}
    </>
  )
}
