import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Info } from 'lucide-react'
import { errorMessage, getAts } from './api.js'

function Yes({ ok }) {
  return ok ? (
    <CheckCircle2 size={16} className="ok-icon" aria-label="yes" />
  ) : (
    <XCircle size={16} className="bad-icon" aria-label="no" />
  )
}

export default function AtsView({ analysisId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getAts(analysisId).then(setData).catch((e) => setError(errorMessage(e)))
  }, [analysisId])

  if (error) return <section className="card"><p className="form__error">{error}</p></section>
  if (!data) return <section className="card"><p className="muted">Loading…</p></section>
  const { parse, keywords, scan } = data
  return (
    <>
      <p className="method">
        <Info size={14} aria-hidden="true" /> {data.label}
      </p>

      <section className="card">
        <h2>6-second scan</h2>
        <p className="muted">What a recruiter likely takes in from the top of page one (a rough estimate).</p>
        <ul className="checklist">
          {scan.checks.map((c) => (
            <li key={c.label}>
              <Yes ok={c.passed} />
              <div>
                <strong>{c.label}</strong>
                <p className="muted">{c.detail}</p>
              </div>
            </li>
          ))}
        </ul>
        <span className="evidence__label">Top of your resume</span>
        <pre className="raw raw--short">{scan.top_lines.join('\n')}</pre>
      </section>

      <section className="card">
        <h2>Keyword match</h2>
        <p className="muted">
          Exact-wording check, like a simple ATS keyword filter. {keywords.summary.exact_in_resume} of{' '}
          {keywords.summary.total} job-description keywords appear word-for-word in your resume.
          {keywords.summary.different_wording > 0 &&
            ` ${keywords.summary.different_wording} skill(s) are in your resume under different wording; consider using the job's wording too.`}
        </p>
        <div className="table-scroll">
          <table className="breakdown keywords">
            <thead>
              <tr>
                <th>Keyword (job's wording)</th>
                <th>In job</th>
                <th>Exact in resume</th>
                <th>Skill in resume</th>
              </tr>
            </thead>
            <tbody>
              {keywords.keywords.map((k) => (
                <tr key={k.keyword} className={k.exact_in_resume ? '' : 'row-missing'}>
                  <td>
                    {k.keyword} {k.kind === 'term' && <span className="muted">· term</span>}
                  </td>
                  <td>×{k.jd_count}</td>
                  <td><Yes ok={k.exact_in_resume} /></td>
                  <td>{k.skill_in_resume === null ? <span className="muted">n/a</span> : <Yes ok={k.skill_in_resume} />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Raw parse preview</h2>
        <p className="muted">
          Exactly the text this app extracted: {parse.stats.words} words, {parse.stats.lines} lines. If something
          you can see in your file is missing here, software may miss it too.
        </p>
        <div className="stat-row">
          {['email', 'phone', 'linkedin', 'github'].map((k) => (
            <div key={k} className="stat stat--inline">
              <Yes ok={parse.contact[k]} /> <span>{k === 'linkedin' ? 'LinkedIn' : k === 'github' ? 'GitHub' : k}</span>
            </div>
          ))}
        </div>
        <p className="muted">Headings recognised: {parse.headings.length ? parse.headings.join(', ') : 'none'}</p>
        {parse.issues.length > 0 && (
          <ul className="notices notices--warn">
            {parse.issues.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        )}
        <pre className="raw">{parse.text}</pre>
      </section>
    </>
  )
}
