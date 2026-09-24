import { CheckCircle2, XCircle, PlusCircle, Info, Sparkles, Cpu, Briefcase, GraduationCap } from 'lucide-react'

const PRIORITY_LABEL = { required: 'Required', standard: 'Mentioned', preferred: 'Nice to have' }

const MATCH_LABEL = {
  exact: { text: 'Exact', title: 'Same wording in both documents' },
  literal: { text: 'Literal', title: 'Same skill, different wording (e.g. JS and JavaScript)' },
  ai_inferred: { text: 'AI-inferred · ½ credit', title: 'AI judged this resume quote to show the skill; the quote is verified' },
  semantic: { text: 'Semantic · ½ credit', title: 'Most similar resume line by local embeddings' },
}

function PriorityBadge({ priority }) {
  return <span className={`badge badge--${priority}`}>{PRIORITY_LABEL[priority]}</span>
}

/** Show a verbatim quote, highlighting the matched wording at its exact position. */
function Quote({ evidence }) {
  const { quote, term, term_offset: i, similarity } = evidence
  const valid = term != null && i != null && quote.slice(i, i + term.length) === term
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
      {similarity != null && <span className="quote__meta"> · similarity {Math.round(similarity * 100)}%</span>}
    </blockquote>
  )
}

function SourcesPanel({ sources }) {
  const ai = sources.extraction === 'ai'
  const semanticText = {
    enabled: `on (threshold ${sources.semantic_threshold})`,
    disabled: 'off',
    unavailable: 'unavailable for this run',
  }[sources.semantic]
  return (
    <section className="card sources">
      <div className="sources__row">
        {ai ? <Sparkles size={16} aria-hidden="true" /> : <Cpu size={16} aria-hidden="true" />}
        <span>
          Resume profile: <strong>{ai ? `AI (${sources.model})` : 'pattern-based fallback (no AI)'}</strong>
        </span>
      </div>
      <div className="sources__row">
        <Cpu size={16} aria-hidden="true" />
        <span>
          Skill matching: <strong>curated skill list</strong> · semantic matching <strong>{semanticText}</strong>
        </span>
      </div>
      {sources.notices.length > 0 && (
        <ul className="notices">
          {sources.notices.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </section>
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
            <th>Named in resume</th>
            <th>Related only</th>
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
              <td>{b.related}</td>
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

function Entry({ heading, sub, evidence }) {
  return (
    <li className="skill">
      {(heading || sub) && (
        <div className="skill__head">
          {heading && <strong>{heading}</strong>}
          {sub && <span className="muted">{sub}</span>}
        </div>
      )}
      <Quote evidence={evidence} />
    </li>
  )
}

function ProfileSection({ profile, ai }) {
  const join = (...parts) => parts.filter(Boolean).join(' · ')
  return (
    <section className="card">
      <h2 className="section-title section-title--neutral">
        <Briefcase size={18} aria-hidden="true" /> Resume profile
        <span className="badge badge--plain">{ai ? 'AI-extracted, quotes verified' : 'Pattern-based (no AI)'}</span>
      </h2>
      {!ai && (
        <p className="muted">
          Without AI, entries are lines found under Experience/Education headings. Titles and employers are not guessed.
        </p>
      )}

      <h3 className="subhead">Experience</h3>
      {profile.experience.length === 0 ? (
        <p className="muted">None found.</p>
      ) : (
        <ul className="skills">
          {profile.experience.map((e) => (
            <Entry key={e.evidence.quote} heading={e.title} sub={join(e.organization, e.dates)} evidence={e.evidence} />
          ))}
        </ul>
      )}

      <h3 className="subhead">
        <GraduationCap size={16} aria-hidden="true" /> Education
      </h3>
      {profile.education.length === 0 ? (
        <p className="muted">None found.</p>
      ) : (
        <ul className="skills">
          {profile.education.map((e) => (
            <Entry key={e.evidence.quote} heading={e.qualification} sub={join(e.institution, e.dates)} evidence={e.evidence} />
          ))}
        </ul>
      )}

      {ai && (
        <>
          <h3 className="subhead">Skills found by AI</h3>
          <ul className="skills">
            {profile.skills.map((s) => (
              <li key={s.name} className="skill skill--compact">
                <details>
                  <summary>
                    <strong>{s.name}</strong>
                    {s.mapped_skill && s.mapped_skill !== s.name && <span className="muted"> · {s.mapped_skill}</span>}
                  </summary>
                  <Quote evidence={s.evidence} />
                </details>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

export default function AnalysisResults({ result }) {
  const ai = result.sources.extraction === 'ai'
  return (
    <div className="results">
      <SourcesPanel sources={result.sources} />

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
        hint="Skills named in the resume earn full credit; related evidence (AI-inferred or semantic) earns half."
        items={result.matched}
        render={(m) => (
          <li key={m.skill} className="skill">
            <div className="skill__head">
              <strong>{m.skill}</strong>
              <PriorityBadge priority={m.priority} />
              <span className={`badge badge--plain${m.credit < 1 ? ' badge--related' : ''}`} title={MATCH_LABEL[m.match_type].title}>
                {MATCH_LABEL[m.match_type].text}
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
        hint="Skills the job description asks for with no supporting evidence in the resume."
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

      <ProfileSection profile={result.profile} ai={ai} />

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
