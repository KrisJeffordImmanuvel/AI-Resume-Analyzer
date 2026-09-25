import { useState } from 'react'
import { CheckCircle2, XCircle, PlusCircle, Info, Sparkles, Cpu, Briefcase, GraduationCap } from 'lucide-react'
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
      <details className="explain">
        <summary>How is the score calculated?</summary>
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

function SkillSection({ icon: Icon, tone, title, hint, explain, items, render }) {
  return (
    <section className="card">
      <h2 className={`section-title section-title--${tone}`}>
        <Icon size={18} aria-hidden="true" /> {title} <span className="count">{items.length}</span>
      </h2>
      {hint && <p className="muted">{hint}</p>}
      {explain}
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
        <span className="badge badge--plain">{ai ? 'Read by AI, quotes checked' : 'Built-in rules (AI off)'}</span>
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

function FitReport({ result }) {
  const ai = result.sources.extraction === 'ai'
  return (
    <div>
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
