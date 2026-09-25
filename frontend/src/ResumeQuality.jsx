import { useEffect, useRef, useState } from 'react'
import { Loader2, Wand2, Copy, Check, AlertCircle, CheckCircle2 } from 'lucide-react'
import { errorMessage, getQuality, listRewrites, rewriteBullet } from './api.js'
import SourceNote from './SourceNote.jsx'

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 }

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard may be blocked; the text is still selectable */
    }
  }
  return (
    <button type="button" className="icon-button" onClick={copy} aria-label="Copy suggestion">
      {copied ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

/** Highlight [placeholders] the user still has to fill in. */
function WithPlaceholders({ text }) {
  const parts = text.split(/(\[[^[\]]{1,30}\])/g)
  return parts.map((p, i) => (/^\[.*\]$/.test(p) ? <mark key={i} className="placeholder">{p}</mark> : p))
}

function RewriteResult({ r }) {
  return (
    <div className="rewrite">
      <SourceNote
        source={r.source}
        model={r.model}
        fallbackReason={r.fallback_reason}
        notices={r.notices}
        fallbackLabel="Rewritten using the app's built-in rules (no AI)"
      />
      <div className="before-after">
        <div>
          <span className="evidence__label">Before</span>
          <blockquote className="quote">{r.bullet}</blockquote>
        </div>
        <div>
          <span className="evidence__label">After</span>
          {r.variants.map((v) => (
            <div key={v.text} className="variant">
              <blockquote className="quote quote--after">
                <WithPlaceholders text={v.text} />
              </blockquote>
              <div className="variant__meta">
                <span className="muted">{v.note}</span>
                <CopyButton text={v.text} />
              </div>
            </div>
          ))}
        </div>
      </div>
      {r.variants.some((v) => v.placeholders.length > 0) && (
        <p className="muted">Highlighted [brackets] are gaps to fill with your real numbers before using a suggestion.</p>
      )}
    </div>
  )
}

export default function ResumeQuality({ analysisId }) {
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [history, setHistory] = useState([])
  const workspace = useRef(null)

  useEffect(() => {
    getQuality(analysisId).then(setReport).catch((e) => setError(errorMessage(e)))
    listRewrites(analysisId).then(setHistory).catch(() => {})
  }, [analysisId])

  function loadBullet(text) {
    setDraft(text)
    workspace.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  async function rewrite() {
    setBusy(true)
    setError(null)
    try {
      const r = await rewriteBullet(analysisId, draft)
      setHistory((h) => [r, ...h])
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const s = report?.summary
  return (
    <>
      <section className="card">
        <h2>Bullet quality</h2>
        <p className="muted">Rule-based checks (no AI): numbers, action verbs, length, first person and filler.</p>
        {error && <p className="form__error">{error}</p>}
        {!report && !error && <p className="muted">Checking…</p>}
        {report && (
          <>
            {report.notices.map((n) => (
              <p key={n} className="info">{n}</p>
            ))}
            {s.bullets > 0 && (
              <div className="stat-row">
                <div className="stat"><strong>{s.bullets}</strong><span>bullets</span></div>
                <div className="stat"><strong>{s.quantified}</strong><span>with a number</span></div>
                <div className="stat"><strong>{s.strong_verb}</strong><span>strong verb</span></div>
                <div className="stat"><strong>{s.with_issues}</strong><span>to improve</span></div>
              </div>
            )}
            <ul className="skills">
              {report.bullets.map((b) => (
                <li key={b.text} className="skill">
                  <div className="bullet-row">
                    {b.issues.length === 0 ? (
                      <CheckCircle2 size={18} className="ok-icon" aria-label="No issues" />
                    ) : (
                      <AlertCircle size={18} className="warn-icon" aria-label="Has issues" />
                    )}
                    <span className="bullet-text">{b.text}</span>
                    <button type="button" className="icon-button" onClick={() => loadBullet(b.text)}>
                      <Wand2 size={15} aria-hidden="true" /> Rewrite
                    </button>
                  </div>
                  {b.issues.length > 0 && (
                    <ul className="issues">
                      {[...b.issues]
                        .sort((a, z) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[z.severity])
                        .map((i) => (
                          <li key={i.code} className={`issue issue--${i.severity}`}>{i.message}</li>
                        ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="card" ref={workspace}>
        <h2>Rewrite workspace</h2>
        <p className="muted">
          Pick a bullet above or paste one. Suggestions never add numbers or skills that are not in your bullet or
          resume; where a metric would help you get a [placeholder] to fill in.
        </p>
        <textarea rows={3} maxLength={600} value={draft} onChange={(e) => setDraft(e.target.value)}
          placeholder="- Responsible for building internal dashboards…" />
        <div className="form__actions">
          <button type="button" className="primary" onClick={rewrite} disabled={busy || !draft.trim()}>
            {busy ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Wand2 size={16} aria-hidden="true" />}
            {busy ? 'Rewriting…' : 'Suggest rewrites'}
          </button>
        </div>
        {history.map((r) => (
          <RewriteResult key={r.id} r={r} />
        ))}
      </section>
    </>
  )
}
