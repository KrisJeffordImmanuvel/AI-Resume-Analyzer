import { CheckCircle2, XCircle, PlusCircle, Info } from 'lucide-react'

const PRIORITY_LABEL = { required: 'Required', standard: 'Mentioned', preferred: 'Nice to have' }

function PriorityBadge({ priority }) {
  return <span className={`badge badge--${priority}`}>{PRIORITY_LABEL[priority]}</span>
}

/** Show a verbatim quote with the matched wording highlighted at its exact position. */
function Quote({ evidence }) {
  const { quote, term, term_offset: i } = evidence
  const valid = quote.slice(i, i + term.length) === term
  return (
    <blockquote className="quote">
      {valid ? (
        <>
          {quote.slice(0, i)}
          <mark>{term}</mark>
          {quote.slice(i + term.length)}
        </>
      ) : (
        quote
      )}
    </blockquote>
  )
}

function ScoreCard({ score }) {
  return (
    <section className="card score">
      <div className="score__main">
        {score.value === null ? (
          <span className="score__value score__value--none">—</span>
        ) : (
          <span className="score__value">
            {score.value}
            <small>/100</small>
          </span>
        )}
        <div>
          <h2>Job-fit score</h2>
          <p className="score__label">
            <Info size={14} aria-hidden="true" /> {score.label}
          </p>
        </div>
      </div>
      {score.value !== null && (
        <div className="meter" role="img" aria-label={`Score ${score.value} out of 100`}>
          <div className="meter__fill" style={{ width: `${score.value}%` }} />
        </div>
      )}
      <table className="breakdown">
        <thead>
          <tr>
            <th>Priority</th>
            <th>Weight</th>
            <th>Matched</th>
          </tr>
        </thead>
        <tbody>
          {score.breakdown.map((b) => (
            <tr key={b.priority}>
              <td>
                <PriorityBadge priority={b.priority} />
              </td>
              <td>×{b.weight}</td>
              <td>
                {b.matched} of {b.total}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function SkillSection({ icon: Icon, tone, title, hint, items, render }) {
  return (
    <section className="card">
      <h2 className={`section-title section-title--${tone}`}>
        <Icon size={18} aria-hidden="true" /> {title} <span className="count">{items.length}</span>
      </h2>
      {hint && <p className="muted">{hint}</p>}
      {items.length === 0 ? <p className="muted">None.</p> : <ul className="skills">{items.map(render)}</ul>}
    </section>
  )
}

export default function AnalysisResults({ result }) {
  return (
    <div className="results">
      <p className="method">
        Method: <strong>deterministic keyword match</strong> against a curated skill list. Every item below quotes the
        exact text it was found in. AI-assisted analysis arrives in a later phase.
      </p>

      {result.warnings.map((w) => (
        <p key={w} className="warning" role="status">
          {w}
        </p>
      ))}

      <ScoreCard score={result.score} />

      <SkillSection
        icon={CheckCircle2}
        tone="good"
        title="Matched skills"
        items={result.matched}
        render={(m) => (
          <li key={m.skill} className="skill">
            <div className="skill__head">
              <strong>{m.skill}</strong>
              <PriorityBadge priority={m.priority} />
              <span className="badge badge--plain" title={m.match_type === 'exact' ? 'Same wording in both' : 'Same skill, different wording'}>
                {m.match_type === 'exact' ? 'Exact' : 'Literal'}
              </span>
            </div>
            <div className="evidence">
              <span className="evidence__label">Resume</span>
              {m.resume_evidence.map((e) => (
                <Quote key={e.quote} evidence={e} />
              ))}
              <span className="evidence__label">Job description</span>
              {m.jd_evidence.map((e) => (
                <Quote key={e.quote} evidence={e} />
              ))}
            </div>
          </li>
        )}
      />

      <SkillSection
        icon={XCircle}
        tone="bad"
        title="Missing skills"
        hint="Skills the job description asks for that were not found in the resume text."
        items={result.missing}
        render={(m) => (
          <li key={m.skill} className="skill">
            <div className="skill__head">
              <strong>{m.skill}</strong>
              <PriorityBadge priority={m.priority} />
            </div>
            <div className="evidence">
              <span className="evidence__label">Job description</span>
              {m.jd_evidence.map((e) => (
                <Quote key={e.quote} evidence={e} />
              ))}
            </div>
          </li>
        )}
      />

      <SkillSection
        icon={PlusCircle}
        tone="neutral"
        title="Other skills in the resume"
        hint="Found in the resume but not mentioned in this job description."
        items={result.additional}
        render={(a) => (
          <li key={a.skill} className="skill skill--compact">
            <details>
              <summary>
                <strong>{a.skill}</strong> <span className="muted">· {a.category}</span>
              </summary>
              {a.resume_evidence.map((e) => (
                <Quote key={e.quote} evidence={e} />
              ))}
            </details>
          </li>
        )}
      />
    </div>
  )
}
