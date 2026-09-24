import { Sparkles, Cpu } from 'lucide-react'

const REASON = {
  no_api_key: 'no GOOGLE_API_KEY is set',
  demo_mode: 'DEMO_MODE is on',
  provider_error: 'the AI request failed',
}

/** One-line label saying whether content came from AI or a fallback, plus any notices. */
export default function SourceNote({ source, model, fallbackReason, notices = [], fallbackLabel }) {
  const ai = source === 'ai'
  return (
    <div className="source-note">
      <p className="source-note__line">
        {ai ? <Sparkles size={15} aria-hidden="true" /> : <Cpu size={15} aria-hidden="true" />}
        {ai ? (
          <span>
            AI-generated ({model}). Treat as suggestions.
          </span>
        ) : (
          <span>
            {fallbackLabel}
            {fallbackReason && fallbackReason !== 'provider_error' ? ` (AI off: ${REASON[fallbackReason]}).` : '.'}
          </span>
        )}
      </p>
      {notices.length > 0 && (
        <ul className="notices">
          {notices.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
