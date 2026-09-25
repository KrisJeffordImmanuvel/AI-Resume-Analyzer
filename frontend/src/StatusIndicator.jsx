import { useCallback, useEffect, useRef, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { getHealth } from './api.js'

const OFFLINE_RETRY_MS = 5000

/** Compact status in the page header; details open on click. */
export default function StatusIndicator() {
  const [state, setState] = useState({ checking: true, health: null, offline: false })
  const retryTimer = useRef(null)

  const check = useCallback(async () => {
    clearTimeout(retryTimer.current)
    setState((s) => ({ ...s, checking: true }))
    try {
      const health = await getHealth()
      setState({ checking: false, health, offline: false })
    } catch {
      setState({ checking: false, health: null, offline: true })
      // The server may still be starting; keep trying quietly.
      retryTimer.current = setTimeout(check, OFFLINE_RETRY_MS)
    }
  }, [])

  useEffect(() => {
    check()
    const onFocus = () => check()
    window.addEventListener('focus', onFocus)
    return () => {
      clearTimeout(retryTimer.current)
      window.removeEventListener('focus', onFocus)
    }
  }, [check])

  const { checking, health, offline } = state
  let tone, label, detail
  if (offline) {
    tone = 'bad'
    label = 'Server offline'
    detail = 'The app server is not responding. If you closed its window, run start.ps1 again. This page reconnects automatically.'
  } else if (!health) {
    tone = 'neutral'
    label = 'Connecting…'
    detail = 'Checking the app server.'
  } else if (health.database !== 'ok') {
    tone = 'bad'
    label = 'Storage problem'
    detail = 'The app cannot read its saved data. Restart it; if this continues, see Troubleshooting in the README.'
  } else if (health.ai_mode === 'live') {
    tone = 'good'
    label = 'AI on'
    detail = `AI features are on (${health.ai_model}). Every AI result is checked against your documents.`
  } else {
    tone = 'neutral'
    label = 'AI off'
    detail =
      health.fallback_reason === 'demo_mode'
        ? 'AI features are switched off (demo mode). Everything still works using built-in rules.'
        : 'AI features are off because no Gemini key is set. Everything still works using built-in rules. To turn AI on, see "Settings" in the README.'
  }

  return (
    <details className="status">
      <summary className={`status__pill status__pill--${tone}`} aria-live="polite">
        <span className="status__dot" aria-hidden="true" />
        {label}
      </summary>
      <div className="status__panel">
        <p>{detail}</p>
        {health && <p className="muted">Version {health.version}</p>}
        <button type="button" className="icon-button" onClick={check} disabled={checking}>
          <RefreshCw size={14} aria-hidden="true" className={checking ? 'spin' : ''} /> Check again
        </button>
      </div>
    </details>
  )
}
