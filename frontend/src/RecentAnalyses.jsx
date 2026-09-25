import { useEffect, useState } from 'react'
import { History, FolderOpen, Trash2, Sparkles } from 'lucide-react'
import { deleteAnalysis, errorMessage, getAnalysis, listAnalyses } from './api.js'

const fmt = (iso) =>
  new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

/** Saved Job Seeker analyses, with open and permanent delete. `refreshKey` reloads the list. */
export default function RecentAnalyses({ refreshKey, currentId, onOpen, onDeleted }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    listAnalyses().then(setItems).catch((e) => setError(errorMessage(e)))
  }, [refreshKey])

  async function open(id) {
    setError(null)
    try {
      onOpen(await getAnalysis(id))
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  async function remove(item) {
    if (!window.confirm(`Delete the analysis of "${item.resume_filename}"? This permanently removes the resume text and everything generated from it.`)) return
    try {
      await deleteAnalysis(item.id)
      setItems((list) => list.filter((a) => a.id !== item.id))
      onDeleted(item.id)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  if (!items || items.length === 0) return error ? <p className="form__error" role="alert">{error}</p> : null
  return (
    <details className="card recent">
      <summary>
        <History size={16} aria-hidden="true" /> Recent analyses <span className="count">{items.length}</span>
      </summary>
      {error && <p className="form__error" role="alert">{error}</p>}
      <ul className="recent__list">
        {items.map((a) => (
          <li key={a.id} className={a.id === currentId ? 'recent__item recent__item--open' : 'recent__item'}>
            <div className="recent__main">
              <strong>{a.resume_filename}</strong>
              <span className="muted"> vs {a.jd_title || 'job description'}</span>
              <div className="muted recent__meta">
                {fmt(a.created_at)} · score {a.score ?? '—'}
                {a.extraction === 'ai' && <> · <Sparkles size={12} aria-hidden="true" /> AI</>}
              </div>
            </div>
            <div className="recent__actions">
              <button type="button" className="icon-button" onClick={() => open(a.id)} disabled={a.id === currentId}>
                <FolderOpen size={15} aria-hidden="true" /> {a.id === currentId ? 'Showing' : 'Open'}
              </button>
              <button type="button" className="icon-button" onClick={() => remove(a)} aria-label={`Delete ${a.resume_filename}`}>
                <Trash2 size={15} aria-hidden="true" />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </details>
  )
}
