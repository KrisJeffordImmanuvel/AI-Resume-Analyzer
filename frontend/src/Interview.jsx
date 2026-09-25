import { useEffect, useState } from 'react'
import { Loader2, RefreshCw, Send, MessageSquareQuote } from 'lucide-react'
import { errorMessage, getInterview, submitAnswer } from './api.js'
import SourceNote from './SourceNote.jsx'

const TYPE_LABEL = { skill: 'Your skill', gap: 'Skill gap', experience: 'Your experience', behavioral: 'Behavioral' }

function Feedback({ fb }) {
  return (
    <div className="feedback">
      <SourceNote
        source={fb.source}
        model={fb.model}
        fallbackReason={fb.fallback_reason}
        notices={fb.notices}
        fallbackLabel="Feedback from the app's built-in checks (no AI)"
      />
      {fb.rating != null && (
        <p className="feedback__rating">
          AI rating: <strong>{fb.rating}/5</strong> <span className="muted">(an estimate)</span>
        </p>
      )}
      {fb.summary && <p>{fb.summary}</p>}
      {[
        ['Strengths', fb.strengths, 'good'],
        ['To improve', fb.improvements, 'bad'],
      ].map(([title, points, tone]) =>
        points.length > 0 ? (
          <div key={title}>
            <h4 className={`feedback__title feedback__title--${tone}`}>{title}</h4>
            <ul className="feedback__points">
              {points.map((p) => (
                <li key={p.point}>
                  {p.point}
                  {p.answer_quote && <blockquote className="quote">{p.answer_quote}</blockquote>}
                </li>
              ))}
            </ul>
          </div>
        ) : null,
      )}
      <p className="feedback__followup">
        <MessageSquareQuote size={16} aria-hidden="true" /> <span>Follow-up: {fb.follow_up_question}</span>
      </p>
    </div>
  )
}

function QuestionCard({ q, index }) {
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [feedback, setFeedback] = useState(null)

  async function send() {
    setBusy(true)
    setError(null)
    try {
      setFeedback(await submitAnswer(q.id, answer))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="question">
      <div className="skill__head">
        <strong>Q{index + 1}.</strong>
        <span className="badge badge--plain">{TYPE_LABEL[q.type]}</span>
        {q.skill && <span className="badge badge--plain">{q.skill}</span>}
      </div>
      <p className="question__text">{q.question}</p>
      {q.grounding && (
        <p className="muted">
          Based on your {q.grounding.source === 'resume' ? 'resume' : 'job description'}: “{q.grounding.quote.replace(/^[-*•·–]\s+/, '')}”
        </p>
      )}
      <textarea
        rows={5}
        maxLength={5000}
        aria-label={`Your answer to question ${index + 1}`}
        placeholder="Type your answer as you would say it…"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
      />
      <div className="form__actions">
        <button type="button" className="primary" onClick={send} disabled={busy || !answer.trim()}>
          {busy ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
          {busy ? 'Reviewing…' : feedback ? 'Get feedback again' : 'Get feedback'}
        </button>
        <span className="muted">{answer.trim() ? `${answer.trim().split(/\s+/).length} words` : ''}</span>
      </div>
      {error && <p className="form__error" role="alert">{error}</p>}
      {feedback && <Feedback fb={feedback} />}
    </li>
  )
}

export default function Interview({ analysisId }) {
  const [state, setState] = useState({ loading: true, data: null, error: null })

  async function load(refresh = false) {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      setState({ loading: false, data: await getInterview(analysisId, refresh), error: null })
    } catch (err) {
      setState({ loading: false, data: null, error: errorMessage(err) })
    }
  }

  useEffect(() => {
    load()
  }, [analysisId]) // eslint-disable-line react-hooks/exhaustive-deps

  const { loading, data, error } = state
  return (
    <section className="card">
      <header className="card__header">
        <h2>Mock interview</h2>
        <button type="button" onClick={() => load(true)} disabled={loading}>
          {loading ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <RefreshCw size={16} aria-hidden="true" />}
          {loading ? 'Working…' : 'New questions'}
        </button>
      </header>
      {error && <p className="form__error" role="alert">{error}</p>}
      {data && (
        <>
          <SourceNote
            source={data.source}
            model={data.model}
            fallbackReason={data.fallback_reason}
            notices={data.notices}
            fallbackLabel="Standard questions based on your documents (no AI)"
          />
          <ol className="questions">
            {data.questions.map((q, i) => (
              <QuestionCard key={q.id} q={q} index={i} />
            ))}
          </ol>
        </>
      )}
    </section>
  )
}
