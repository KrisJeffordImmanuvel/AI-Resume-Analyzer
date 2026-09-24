import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Sparkles, Database, Network } from 'lucide-react'
import { API_BASE_URL, getHealth } from './api.js'

const FALLBACK_REASONS = {
  no_api_key: 'No GOOGLE_API_KEY set in backend\\.env',
  demo_mode: 'DEMO_MODE=true in backend\\.env',
}

function Row({ icon: Icon, tone, label, value, hint }) {
  return (
    <div className={`row row--${tone}`}>
      <Icon size={18} aria-hidden="true" />
      <span className="row__label">{label}</span>
      <span className="row__value">{value}</span>
      {hint && <span className="row__hint">{hint}</span>}
    </div>
  )
}

export default function HealthStatus() {
  const [state, setState] = useState({ loading: true, health: null, error: null })

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }))
    try {
      setState({ loading: false, health: await getHealth(), error: null })
    } catch (err) {
      setState({ loading: false, health: null, error: err.message || 'Request failed' })
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const { loading, health, error } = state
  const aiLive = health?.ai_mode === 'live'

  return (
    <section className="card" aria-live="polite">
      <header className="card__header">
        <h2>System status</h2>
        <button type="button" onClick={load} disabled={loading}>
          <RefreshCw size={16} aria-hidden="true" /> {loading ? 'Checking…' : 'Recheck'}
        </button>
      </header>

      {error && (
        <Row
          icon={XCircle}
          tone="bad"
          label="Backend"
          value="Not reachable"
          hint={`Could not reach ${API_BASE_URL}/health (${error}). Is uvicorn running?`}
        />
      )}

      {health && (
        <>
          <Row icon={CheckCircle2} tone="good" label="Backend" value={`Connected (v${health.version})`} />
          <Row
            icon={Database}
            tone={health.database === 'ok' ? 'good' : 'bad'}
            label="Database"
            value={health.database === 'ok' ? 'OK' : 'Error'}
          />
          <Row
            icon={aiLive ? Sparkles : AlertTriangle}
            tone={aiLive ? 'good' : 'warn'}
            label="AI"
            value={aiLive ? 'Live (Gemini configured)' : 'Fallback mode'}
            hint={aiLive ? `Model: ${health.ai_model}` : FALLBACK_REASONS[health.fallback_reason]}
          />
          <Row
            icon={Network}
            tone={health.semantic_matching === 'enabled' ? 'good' : 'neutral'}
            label="Semantic"
            value={health.semantic_matching === 'enabled' ? 'Enabled' : 'Off'}
            hint={
              health.semantic_matching === 'enabled'
                ? 'The model downloads on the first analysis (~90 MB).'
                : 'Off by default. Set SEMANTIC_MATCHING=true in backend\\.env to experiment.'
            }
          />
        </>
      )}
    </section>
  )
}
