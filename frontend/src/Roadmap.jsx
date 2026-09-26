import { useEffect, useState } from 'react'
import { ExternalLink, Loader2, RefreshCw, Hammer } from 'lucide-react'
import { errorMessage, getRoadmap } from './api.js'
import SourceNote from './SourceNote.jsx'
import { PRIORITY_LABEL } from './Priority.jsx'
import Working from './Working.jsx'

// Display only: drop a leading bullet from a quoted line (the stored quote stays verbatim).
const clean = (quote) => quote.replace(/^[-*•·–]\s+/, '')


export default function Roadmap({ analysisId }) {
  const [state, setState] = useState({ loading: true, data: null, error: null })

  const [request, setRequest] = useState({ refresh: false }) // a new object asks again

  useEffect(() => {
    let alive = true // ignore an answer that arrives after leaving the tab
    getRoadmap(analysisId, request.refresh).then(
      (data) => alive && setState({ loading: false, data, error: null }),
      (err) => alive && setState({ loading: false, data: null, error: errorMessage(err) }),
    )
    return () => {
      alive = false
    }
  }, [analysisId, request])

  function load(refresh = false) {
    setState((s) => ({ ...s, loading: true, error: null }))
    setRequest({ refresh })
  }

  const { loading, data, error } = state
  return (
    <section className="card">
      <header className="card__header">
        <h2>Learning roadmap</h2>
        <button type="button" onClick={() => load(true)} disabled={loading}>
          {loading ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <RefreshCw size={16} aria-hidden="true" />}
          {loading ? 'Working…' : 'Regenerate'}
        </button>
      </header>
      {loading && <Working step="Writing your learning roadmap…" />}
      {error && <p className="form__error" role="alert">{error}</p>}
      {data && (
        <>
          <SourceNote
            source={data.source}
            model={data.model}
            fallbackReason={data.fallback_reason}
            notices={data.notices}
            fallbackLabel="Standard learning steps (no AI)"
          />
          {data.items.length === 0 ? (
            <p className="muted">No skill gaps: every skill in the job description is named in the resume.</p>
          ) : (
            <ol className="roadmap">
              {data.items.map((item) => (
                <li key={item.skill} className="roadmap__item">
                  <div className="skill__head">
                    <strong>{item.skill}</strong>
                    <span className={`badge badge--${item.priority}`}>{PRIORITY_LABEL[item.priority]}</span>
                    <span className="badge badge--plain">{item.kind === 'learn' ? 'Learn' : 'Strengthen'}</span>
                    {item.steps_source === 'template' && data.source === 'ai' && (
                      <span className="badge badge--plain">Template</span>
                    )}
                  </div>
                  {item.jd_evidence[0] && (
                    <p className="muted roadmap__why">
                      Why: the job description says “{clean(item.jd_evidence[0].quote)}”
                    </p>
                  )}
                  {item.kind === 'strengthen' && item.resume_evidence[0] && (
                    <p className="muted roadmap__why">Related evidence in your resume: “{clean(item.resume_evidence[0].quote)}”</p>
                  )}
                  <ol className="steps">
                    {item.steps.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ol>
                  {item.project_idea && (
                    <p className="project">
                      <Hammer size={15} aria-hidden="true" /> <span>Project idea: {item.project_idea}</span>
                    </p>
                  )}
                  <a className="yt" href={item.youtube_url} target="_blank" rel="noreferrer">
                    <ExternalLink size={15} aria-hidden="true" /> Search YouTube for “{item.skill} tutorial”
                  </a>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  )
}
