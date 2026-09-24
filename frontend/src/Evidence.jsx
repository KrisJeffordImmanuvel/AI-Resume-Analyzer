import { useEffect, useState } from 'react'
import { CheckCircle2, CircleDashed, ExternalLink, Info, Loader2, Search, Scale, AlertTriangle } from 'lucide-react'
import { errorMessage, getEvidence, getFairness, runGithub, runLinkedin } from './api.js'
import SourceNote from './SourceNote.jsx'

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short' }) : '')

function GitHubCard({ analysisId, detected, initial }) {
  const [username, setUsername] = useState(initial?.username || detected || '')
  const [data, setData] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function run() {
    setBusy(true)
    setError(null)
    try {
      setData(await runGithub(analysisId, username.trim()))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const seen = data?.resume_claims.filter((c) => c.status === 'seen') || []
  const notSeen = data?.resume_claims.filter((c) => c.status === 'not_seen') || []
  return (
    <section className="card">
      <h2>GitHub check</h2>
      <p className="muted">
        Reads public data from GitHub (only the username is sent). Shows which of your resume skills appear in your
        public repositories.
        {detected && ` Found github.com/${detected} in your resume.`}
      </p>
      <div className="inline-form">
        <label className="sr-only" htmlFor="gh-user">GitHub username</label>
        <input id="gh-user" type="text" value={username} placeholder="GitHub username" maxLength={39}
          onChange={(e) => setUsername(e.target.value)} />
        <button type="button" className="primary" onClick={run} disabled={busy || !username.trim()}>
          {busy ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Search size={16} aria-hidden="true" />}
          {busy ? 'Checking…' : data ? 'Check again' : 'Check GitHub'}
        </button>
      </div>
      {error && <p className="form__error">{error}</p>}
      {data && (
        <>
          <p className="method"><Info size={14} aria-hidden="true" /> {data.label}</p>
          <div className="stat-row">
            <div className="stat"><strong>{data.repos_analyzed}</strong><span>own public repos</span></div>
            <div className="stat"><strong>{data.recently_active_repos}</strong><span>updated in last year</span></div>
            <div className="stat"><strong>{seen.length}</strong><span>resume skills seen</span></div>
          </div>
          <p>
            <a className="yt" href={data.profile_url} target="_blank" rel="noreferrer">
              <ExternalLink size={15} aria-hidden="true" /> {data.name ? `${data.name} · ` : ''}github.com/{data.username}
            </a>
          </p>
          <h3 className="subhead">Seen in public repos</h3>
          {seen.length === 0 ? <p className="muted">None of your resume's technical skills appear in public repos.</p> : (
            <ul className="skills">
              {seen.map((c) => (
                <li key={c.skill} className="skill skill--compact">
                  <div className="skill__head">
                    <CheckCircle2 size={16} className="ok-icon" aria-hidden="true" />
                    <strong>{c.skill}</strong>
                    <span className="muted">{c.repos} repo{c.repos === 1 ? '' : 's'}</span>
                  </div>
                  <ul className="repo-list">
                    {c.examples.map((r) => (
                      <li key={r.name}>
                        <a href={r.url} target="_blank" rel="noreferrer">{r.name}</a>
                        <span className="muted"> · {r.via}{r.pushed_at ? ` · updated ${fmtDate(r.pushed_at)}` : ''}</span>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
          {notSeen.length > 0 && (
            <>
              <h3 className="subhead">Not seen in public repos</h3>
              <p className="muted">
                <CircleDashed size={14} aria-hidden="true" /> {notSeen.map((c) => c.skill).join(', ')}. This is normal for
                work done in private or company repositories.
              </p>
            </>
          )}
          {data.not_on_resume.length > 0 && (
            <p className="muted">
              On GitHub but not on your resume: {data.not_on_resume.map((l) => `${l.skill} (${l.repos})`).join(', ')}.
              Consider adding them if they are relevant.
            </p>
          )}
        </>
      )}
    </section>
  )
}

const ROLE_STATUS = {
  consistent: ['Consistent', 'ok'],
  date_mismatch: ['Dates differ', 'bad'],
  only_resume: ['Only on resume', 'warn'],
  only_linkedin: ['Only on LinkedIn', 'warn'],
}

function LinkedInCard({ analysisId, initial }) {
  const [text, setText] = useState('')
  const [data, setData] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function run() {
    setBusy(true)
    setError(null)
    try {
      setData(await runLinkedin(analysisId, text))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <h2>LinkedIn consistency check</h2>
      <p className="muted">
        Nothing is fetched from LinkedIn. Open your LinkedIn profile, select the <strong>Experience</strong> section
        (titles, companies and dates) and optionally <strong>Skills</strong>, copy, and paste below. The app compares
        roles, dates and skills with your resume.
      </p>
      <textarea rows={8} maxLength={50000} value={text} onChange={(e) => setText(e.target.value)}
        placeholder={'Experience\nSoftware Engineer\nExample Fintech Pvt Ltd · Full-time\nJan 2022 - Present · 2 yrs 9 mos'} />
      <div className="form__actions">
        <button type="button" className="primary" onClick={run} disabled={busy || !text.trim()}>
          {busy ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Search size={16} aria-hidden="true" />}
          {busy ? 'Comparing…' : 'Compare with resume'}
        </button>
      </div>
      {error && <p className="form__error">{error}</p>}
      {data && (
        <div className="li-result">
          <SourceNote source={data.source} model={data.model} fallbackReason={data.fallback_reason}
            notices={data.notices} fallbackLabel="Pattern-based comparison (no AI)" />
          <p className="method"><Info size={14} aria-hidden="true" /> {data.label}</p>
          <h3 className="subhead">Roles</h3>
          {data.roles.length === 0 ? <p className="muted">No dated roles found on either side.</p> : (
            <ul className="skills">
              {data.roles.map((r, i) => (
                <li key={i} className="skill">
                  <div className="skill__head">
                    <span className={`badge badge--status-${ROLE_STATUS[r.status][1]}`}>{ROLE_STATUS[r.status][0]}</span>
                    {r.detail && <span className="muted">{r.detail}</span>}
                  </div>
                  <div className="before-after">
                    <div>
                      <span className="evidence__label">Resume</span>
                      {r.resume ? <blockquote className="quote">{r.resume}</blockquote> : <p className="muted">Not found</p>}
                    </div>
                    <div>
                      <span className="evidence__label">LinkedIn</span>
                      {r.linkedin ? <blockquote className="quote">{r.linkedin}</blockquote> : <p className="muted">Not found</p>}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <h3 className="subhead">Skills</h3>
          <p className="muted">In both: {data.skills.both.join(', ') || 'none'}</p>
          {data.skills.only_linkedin.length > 0 && (
            <p className="muted">
              Only on LinkedIn: {data.skills.only_linkedin.map((s) => s.skill).join(', ')}. Add to your resume if you can
              back them up.
            </p>
          )}
          {data.skills.only_resume.length > 0 && (
            <p className="muted">Only on resume: {data.skills.only_resume.join(', ')}</p>
          )}
        </div>
      )}
    </section>
  )
}

function FairnessList({ title, items, empty }) {
  return (
    <>
      <h3 className="subhead">{title}</h3>
      {items.length === 0 ? <p className="muted">{empty}</p> : (
        <ul className="skills">
          {items.map((f) => (
            <li key={f.category + f.quote} className="skill">
              <div className="skill__head">
                <AlertTriangle size={16} className="warn-icon" aria-hidden="true" />
                <strong>{f.category}</strong>
                <span className="muted">{f.terms.map((t) => `“${t}”`).join(', ')}</span>
              </div>
              <blockquote className="quote">{f.quote}</blockquote>
              <p className="muted fair-suggestion">{f.suggestion}</p>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function FairnessCard({ analysisId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    getFairness(analysisId).then(setData).catch((e) => setError(errorMessage(e)))
  }, [analysisId])
  return (
    <section className="card">
      <h2><Scale size={18} aria-hidden="true" /> Fairness scan</h2>
      {error && <p className="form__error">{error}</p>}
      {!data && !error && <p className="muted">Scanning…</p>}
      {data && (
        <>
          <p className="method"><Info size={14} aria-hidden="true" /> {data.label}</p>
          <FairnessList title="Job description wording" items={data.job_description}
            empty="Nothing flagged in the job description." />
          <FairnessList title="Personal details in your resume" items={data.resume}
            empty="No unnecessary personal details found." />
          <p className="muted">{data.scoring_note}</p>
        </>
      )}
    </section>
  )
}

export default function Evidence({ analysisId }) {
  const [saved, setSaved] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    getEvidence(analysisId).then(setSaved).catch((e) => setError(errorMessage(e)))
  }, [analysisId])
  if (error) return <section className="card"><p className="form__error">{error}</p></section>
  if (!saved) return <section className="card"><p className="muted">Loading…</p></section>
  return (
    <>
      <GitHubCard analysisId={analysisId} detected={saved.detected_github_username} initial={saved.github} />
      <LinkedInCard analysisId={analysisId} initial={saved.linkedin} />
      <FairnessCard analysisId={analysisId} />
    </>
  )
}
