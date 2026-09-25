import { Sparkles, Info } from 'lucide-react'

/**
 * One-line label saying whether content came from AI or the app's built-in rules, plus any notices.
 * AI being off is a normal state (the header says so), so it is stated plainly, not as a warning;
 * only a failed AI request shows its notices in amber.
 */
export default function SourceNote({ source, model, fallbackReason, notices = [], fallbackLabel }) {
  const ai = source === 'ai'
  return (
    <div className="source-note">
      <p className="source-note__line">
        {ai ? <Sparkles size={15} aria-hidden="true" /> : <Info size={15} aria-hidden="true" />}
        {ai ? (
          <span>
            AI-generated ({model}). Treat as suggestions.
          </span>
        ) : (
          <span>{fallbackLabel}.</span>
        )}
      </p>
      {notices.length > 0 && (
        <ul className={fallbackReason === 'provider_error' ? 'notices notices--warn' : 'notices'}>
          {notices.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
