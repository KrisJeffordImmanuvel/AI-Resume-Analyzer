import { useEffect, useState } from 'react'
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts'
import { Info, Briefcase, GraduationCap } from 'lucide-react'
import { errorMessage, getCareer } from './api.js'

/** SVG attributes cannot read CSS variables, so resolve them (and follow light/dark changes). */
function useCssVars(names) {
  const read = () => {
    const style = getComputedStyle(document.documentElement)
    return Object.fromEntries(names.map((n) => [n, style.getPropertyValue(n).trim()]))
  }
  const [vars, setVars] = useState(read)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setVars(read())
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  return vars
}

function RadarTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const r = payload[0].payload
  return (
    <div className="chart-tooltip">
      <strong>{r.name}</strong>
      <div>
        Fit <strong>{r.score}</strong>/100
      </div>
      <div className="muted">
        Required skills: {r.required_matched} of {r.required_total}
        {r.required_related ? ` (+${r.required_related} related)` : ''}
      </div>
    </div>
  )
}

const fmtMonths = (m) => {
  if (m == null) return null
  const y = Math.floor(m / 12)
  const mo = m % 12
  return [y ? `${y} yr` : null, mo ? `${mo} mo` : null].filter(Boolean).join(' ') || '< 1 mo'
}
const fmtYm = (ym, precise) => {
  const [y, m] = ym.split('-').map(Number)
  return precise ? new Date(y, m - 1).toLocaleString(undefined, { month: 'short', year: 'numeric' }) : String(y)
}

function useNarrow(maxWidth = 520) {
  const query = `(max-width: ${maxWidth}px)`
  const [narrow, setNarrow] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const update = () => setNarrow(mq.matches)
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [query])
  return narrow
}

function RoleFit({ roles, label }) {
  const c = useCssVars(['--series-1', '--border', '--muted', '--text'])
  const narrow = useNarrow()
  const sorted = [...roles].sort((a, b) => b.score - a.score)
  return (
    <section className="card">
      <h2>Fit across common roles</h2>
      <p className="method">
        <Info size={14} aria-hidden="true" /> {label}
      </p>
      <div className="radar" role="img" aria-label={`Radar chart of role fit. Highest: ${sorted[0].name} ${sorted[0].score}.`}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={roles} outerRadius={narrow ? '56%' : '68%'}
            margin={narrow ? { top: 8, right: 40, bottom: 8, left: 40 } : { top: 8, right: 24, bottom: 8, left: 24 }}>
            <PolarGrid stroke={c['--border']} />
            <PolarAngleAxis dataKey="short" tick={{ fill: c['--text'], fontSize: narrow ? 10 : 12 }} />
            <PolarRadiusAxis domain={[0, 100]} tickCount={5} angle={90} axisLine={false}
              tick={{ fill: c['--muted'], fontSize: 10 }} />
            <Radar dataKey="score" stroke={c['--series-1']} strokeWidth={2} fill={c['--series-1']} fillOpacity={0.18}
              dot={{ r: 4, fill: c['--series-1'], strokeWidth: 0 }} activeDot={{ r: 6 }} isAnimationActive={false} />
            <Tooltip content={<RadarTooltip />} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="table-scroll">
        <table className="breakdown roles">
          <thead>
            <tr>
              <th>Role</th>
              <th>Fit</th>
              <th>Required</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.id}>
                <td>
                  {r.name}
                  <div className="role-missing">
                    {r.missing_required.length ? `Missing: ${r.missing_required.join(', ')}` : 'All required skills found'}
                  </div>
                </td>
                <td>
                  <div className="fit-cell">
                    <span className="fit-value">{r.score}</span>
                    <span className="fit-bar" aria-hidden="true">
                      <span style={{ width: `${r.score}%` }} />
                    </span>
                  </div>
                </td>
                <td>
                  {r.required_matched} of {r.required_total}
                  {r.required_related > 0 && <span className="role-related"> +{r.required_related} related</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Timeline({ timeline, profileSource }) {
  const items = [...timeline.items].reverse() // newest first
  const gapBefore = Object.fromEntries(timeline.gaps.map((g) => [g.before, g]))
  return (
    <section className="card">
      <h2>Career timeline</h2>
      <p className="muted">
        Built only from dated entries in your resume
        {profileSource === 'ai' ? ' (AI-extracted, quotes verified)' : ' (pattern-based, no AI)'}.
        {timeline.career_span_months != null &&
          ` ${timeline.roles} role(s) over ${fmtMonths(timeline.career_span_months)}.`}
      </p>
      {timeline.notices.length > 0 && (
        <ul className="notices">
          {timeline.notices.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
      {items.length === 0 ? (
        <p className="muted">No dated roles or education were found.</p>
      ) : (
        <ol className="timeline">
          {items.map((i) => (
            <li key={`${i.kind}-${i.start}-${i.evidence.quote}`} className={`tl-item tl-item--${i.kind}`}>
              <span className="tl-dot" aria-hidden="true">
                {i.kind === 'role' ? <Briefcase size={14} /> : <GraduationCap size={14} />}
              </span>
              <div className="tl-body">
                <div className="tl-when">
                  {i.duration_months == null
                    ? fmtYm(i.start, false)
                    : `${fmtYm(i.start, i.month_precision)} – ${i.current ? 'Present' : fmtYm(i.end, i.month_precision)}`}
                  {i.duration_months != null && <span className="tl-duration">· {fmtMonths(i.duration_months)}</span>}
                  {i.current && <span className="badge badge--plain">Current</span>}
                </div>
                {(i.title || i.organization) && (
                  <div>
                    {i.title && <strong>{i.title}</strong>}
                    {i.organization && <span className="muted"> · {i.organization}</span>}
                  </div>
                )}
                <blockquote className="quote">{i.evidence.quote}</blockquote>
                {gapBefore[i.evidence.quote] && (
                  <p className="tl-gap">
                    Gap of {fmtMonths(gapBefore[i.evidence.quote].months)} before this role (from the dates as written).
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export default function Career({ analysisId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    getCareer(analysisId).then(setData).catch((e) => setError(errorMessage(e)))
  }, [analysisId])

  if (error) return <section className="card"><p className="form__error">{error}</p></section>
  if (!data) return <section className="card"><p className="muted">Loading…</p></section>
  return (
    <>
      <RoleFit roles={data.roles} label={data.label} />
      <Timeline timeline={data.timeline} profileSource={data.profile_source} />
    </>
  )
}
