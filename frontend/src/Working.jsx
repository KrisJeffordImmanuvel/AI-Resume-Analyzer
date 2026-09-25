import { useEffect, useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { getHealth } from './api.js'

const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

let limitPromise = null
/** The server's AI time limit (from /health), fetched once. null when AI is off. */
function aiLimit() {
  limitPromise ??= getHealth()
    .then((h) => (h.ai_mode === 'live' ? h.ai_timeout_seconds : null))
    .catch(() => {
      limitPromise = null
      return null
    })
  return limitPromise
}

/**
 * What the app is doing during a slow request: a step, the time so far, how long it can take at most,
 * and an optional Cancel button. Shown instead of a bare spinner.
 */
export default function Working({ step, onCancel, cancelLabel = 'Cancel' }) {
  const [seconds, setSeconds] = useState(0)
  const [limit, setLimit] = useState(null)

  useEffect(() => {
    const started = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000)
    let alive = true
    aiLimit().then((l) => alive && setLimit(l))
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  const hint = limit
    ? `If AI has not answered after ${limit >= 120 ? `${limit / 60} minutes` : `${limit} seconds`}, the app stops waiting and uses its built-in rules.`
    : null
  return (
    <div className="working">
      <p className="working__line">
        <Loader2 size={16} className="spin" aria-hidden="true" />
        <span>{step}</span>
        <span className="working__time">{fmt(seconds)}</span>
        {onCancel && (
          <button type="button" className="icon-button" onClick={onCancel}>
            <X size={15} aria-hidden="true" /> {cancelLabel}
          </button>
        )}
      </p>
      {hint && <p className="muted working__hint">{hint}</p>}
    </div>
  )
}
