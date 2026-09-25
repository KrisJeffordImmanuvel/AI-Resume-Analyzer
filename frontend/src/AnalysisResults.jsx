import { useState } from 'react'
import { CheckCircle2, ChevronDown, XCircle, PlusCircle, Info, Sparkles, Cpu, Briefcase, GraduationCap } from 'lucide-react'
import Roadmap from './Roadmap.jsx'
import Interview from './Interview.jsx'
import ResumeQuality from './ResumeQuality.jsx'
import AtsView from './AtsView.jsx'
import Career from './Career.jsx'
import Evidence from './Evidence.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import { TabList, TabPanel } from './Tabs.jsx'

const PRIORITY_LABEL = { required: 'Required', standard: 'Mentioned', preferred: 'Nice to have' }

const PRIORITY_HELP = {
  required: 'Listed under a heading like "Requirements" or "Must have". Counts 3 points.',
  standard: 'Named elsewhere in the job description. Counts 2 points.',
  preferred: 'Listed under "Preferred", "Nice to have" or "Bonus". Counts 1 point.',
}

const MATCH_LABEL = {
  exact: { text: 'Same wording', title: 'Both documents use the same words for this skill. Full credit.' },
  literal: { text: 'Other wording', title: 'Same skill, written differently (for example "JS" and "JavaScript"). Full credit.' },
  ai_inferred: { text: 'Related (AI) · half credit', title: 'AI judged that this resume line shows the skill without naming it. The line is checked to be in your resume. Half credit.' },
  semantic: { text: 'Similar meaning · half credit', title: 'The resume line closest in meaning to the skill. Half credit.' },
}

const REASON = {
  no_api_key: 'AI is off, so the app read your resume with its built-in rules.',
  demo_mode: 'AI is off (demo mode), so the app read your resume with its built-in rules.',
  provider_error: 'The AI request failed, so the app read your resume with its built-in rules instead.',
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

/** How this report was produced, in plain words. AI being off is normal, so it is shown calmly. */
function SourcesPanel({ sources }) {
  const ai = sources.extraction === 'ai'
  const failed = sources.fallback_reason === 'provider_error'
  const semanticText = {
    enabled: 'Resume lines with a similar meaning also count, for half credit.',
    unavailable: 'Similar-meaning matching could not run this time.',
  }[sources.semantic]
  return (
    <section className="card sources" aria-label="How this report was made">
      <div className="sources__row">
        {ai ? <Sparkles size={16} aria-hidden="true" /> : <Info size={16} aria-hidden="true" />}
        <span>
          {ai
            ? `AI read your resume (${sources.model}). Every quote shown was checked against your document.`
            : REASON[sources.fallback_reason] || 'The app read your resume with its built-in rules.'}{' '}
          Everything below comes from your own documents.
        </span>
      </div>
      <div className="sources__row">
        <Cpu size={16} aria-hidden="true" />
        <span>
          Skills are recognised from the app&apos;s list of known skills.{semanticText && ` ${semanticText}`}
        </span>
      </div>
      {sources.notices.length > 0 && (
        <ul className={failed ? 'notices notices--warn' : 'notices'}>
          {sources.notices.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </section>
  )
}

function ScoreRing({ value }) {
  const r = 44
  const circumference = 2 * Math.PI * r
  return (
    <div className="ring" role="img" aria-label={value === null ? 'No score' : `Score ${value} out of 100`}>
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <circle className="ring__track" cx="50" cy="50" r={r} />
        {value !== null && (
          <circle className="ring__fill" cx="50" cy="50" r={r} transform="rotate(-90 50 50)"
            strokeDasharray={`${(circumference * value) / 100} ${circumference}`} />
        )}
      </svg>
      <span className={value === null ? 'score__value score__value--none' : 'score__value'} aria-hidden="true">
        {value ?? '—'}
        {value !== null && <small>/100</small>}
      </span>
    </div>
  )
}

/** The answer first: score, what it is based on, and the gaps that matter most. */
function Summary({ result }) {
  const { score, matched, missing } = result
  const total = matched.length + missing.length
  const required = score.breakdown.find((b) => b.priority === 'required')
  const related = matched.filter((m) => m.credit < 1).length
  const missingRequired = missing.filter((m) => m.priority === 'required').map((m) => m.skill)
  return (
    <section className="card summary score" aria-labelledby="summary-title">
      <div className="summary__top">
        <ScoreRing value={score.value} />
        <div className="summary__text">
          <h2 id="summary-title">Job-fit score</h2>
          <p className="summary__headline">
            {total
              ? `Your resume shows ${matched.length} of the ${total} skills this job asks for.`
              : 'The job description names no skills the app recognises, so there is no score.'}
          </p>
          <p className="score__label">
            <Info size={14} aria-hidden="true" /> {score.label}
          </p>
        </div>
      </div>
      {total > 0 && (
        <dl className="summary__stats">
          {required && required.total > 0 && (
            <div className="stat">
              <dt>Required skills</dt>
              <dd>{required.matched} <small>of {required.total}</small></dd>
            </div>
          )}
          <div className="stat">
            <dt>Matched</dt>
            <dd>{matched.length}{related > 0 && <small> ({related} related)</small>}</dd>
          </div>
          <div className="stat">
            <dt>Missing</dt>
            <dd>{missing.length}</dd>
          </div>
        </dl>
      )}
      {missingRequired.length > 0 && (
        <div className="summary__gaps">
          <span>Missing required skills:</span>
          <ul className="chips">
            {missingRequired.map((skill) => (
              <li key={skill} className="chip">{skill}</li>
            ))}
          </ul>
        </div>
      )}
      <details className="explain">
        <summary>Score breakdown and how it is calculated</summary>
        <table className="breakdown">
          <thead>
            <tr>
              <th>Priority</th>
              <th>Points each</th>
              <th>Named in resume</th>
              <th>Related only (half)</th>
            </tr>
          </thead>
          <tbody>
            {score.breakdown.map((b) => (
              <tr key={b.priority}>
                <td>
                  <PriorityBadge priority={b.priority} />
                </td>
                <td>{b.weight}</td>
                <td>
                  {b.matched} of {b.total}
                </td>
                <td>{b.related}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p>
          Each skill the job description asks for is worth points by priority. Your score is the points for skills
          your resume shows, divided by all the points, times 100. A skill your resume only relates to (without
          naming it) earns half its points.
        </p>
        <dl>
          {['required', 'standard', 'preferred'].map((p) => (
            <div key={p}>
              <dt><PriorityBadge priority={p} /></dt>
              <dd>{PRIORITY_HELP[p]}</dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  )
}

/** A report section that can be collapsed, so the report stays short. */
function Section({ icon: Icon, tone, title, count, badge, defaultOpen = false, children }) {
  return (
    <details className="card section" open={defaultOpen}>
      <summary className="section__summary">
        <h2 className={`section-title section-title--${tone}`}>
          <Icon size={18} aria-hidden="true" /> {title}
          {count !== undefined && <span className="count">{count}</span>}
          {badge}
        </h2>
        <ChevronDown size={18} aria-hidden="true" className="section__chevron" />
      </summary>
      <div className="section__body">{children}</div>
    </details>
  )
}

function SkillSection({ icon, tone, title, hint, explain, items, render, defaultOpen }) {
  return (
    <Section icon={icon} tone={tone} title={title} count={items.length} defaultOpen={defaultOpen}>
      {hint && <p className="muted">{hint}</p>}
      {explain}
      {items.length === 0 ? <p className="muted">None.</p> : <ul className="skills">{items.map(render)}</ul>}
    </Section>
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
    <Section icon={Briefcase} tone="neutral" title="Resume profile"
      badge={<span className="badge badge--plain">{ai ? 'Read by AI, quotes checked' : 'Built-in rules (AI off)'}</span>}>
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
    </Section>
  )
}

function FitReport({ result }) {
  const ai = result.sources.extraction === 'ai'
  return (
    <div>
      <Summary result={result} />

      {result.warnings.map((w) => (
        <p key={w} className="warning" role="status">
          {w}
        </p>
      ))}

      <SourcesPanel sources={result.sources} />

      <SkillSection
        icon={CheckCircle2}
        tone="good"
        title="Matched skills"
        hint="Skills your resume names earn full credit. Skills it only relates to earn half."
        items={result.matched}
        explain={
          <details className="explain">
            <summary>What do the labels mean?</summary>
            <dl>
              {Object.entries(MATCH_LABEL).map(([k, v]) => (
                <div key={k}>
                  <dt><span className="badge badge--plain">{v.text}</span></dt>
                  <dd>{v.title}</dd>
                </div>
              ))}
            </dl>
          </details>
        }
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
        defaultOpen
        hint="Skills the job description asks for that your resume does not show."
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

const TABS = [
  ['report', 'Fit report'],
  ['roadmap', 'Learning roadmap'],
  ['interview', 'Mock interview'],
  ['quality', 'Resume quality'],
  ['ats', 'ATS view'],
  ['career', 'Career'],
  ['evidence', 'Evidence'],
]

export default function AnalysisResults({ result }) {
  const [tab, setTab] = useState('report')
  return (
    <div className="results">
      <TabList id="report" label="Report sections" className="tabs tabs--results" tabs={TABS} value={tab} onChange={setTab} />
      <TabPanel id="report" value={tab}>
        {/* key={tab}: switching tabs clears an error shown by the previous tab */}
        <ErrorBoundary key={tab}>
          {tab === 'report' && <FitReport result={result} />}
          {tab === 'roadmap' && <Roadmap analysisId={result.id} />}
          {tab === 'interview' && <Interview analysisId={result.id} />}
          {tab === 'quality' && <ResumeQuality analysisId={result.id} />}
          {tab === 'ats' && <AtsView analysisId={result.id} />}
          {tab === 'career' && <Career analysisId={result.id} />}
          {tab === 'evidence' && <Evidence analysisId={result.id} />}
        </ErrorBoundary>
      </TabPanel>
    </div>
  )
}
