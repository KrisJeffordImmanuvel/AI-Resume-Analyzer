import { useState } from 'react'
import { Check, FileText, Info, Minus, Trash2, X } from 'lucide-react'
import { PRIORITY_LABEL, PRIORITY_SHORT } from './Priority.jsx'

const CELL = {
  named: [Check, 'Named', 'cell--named'],
  related: [Minus, 'Related (half)', 'cell--related'],
  missing: [X, 'Missing', 'cell--missing'],
}

/** A matrix cell. With resume evidence it is a button that shows the quote below the table (keyboard and touch too). */
function Cell({ cell, skill, candidate, shown, onShow }) {
  const [Icon, text, cls] = CELL[cell.status]
  const content = (
    <>
      <Icon size={14} aria-hidden="true" />
      <span className="matrix-cell__text">{text}</span>
    </>
  )
  if (!cell.quote) return <span className={`matrix-cell ${cls}`}>{content}</span>
  return (
    <button
      type="button"
      className={`matrix-cell matrix-cell--button ${cls}${shown ? ' matrix-cell--shown' : ''}`}
      title={`“${cell.quote}”`}
      aria-label={`${skill}, ${candidate}: ${text}. Show the resume line`}
      aria-expanded={shown}
      aria-controls="matrix-quote"
      onClick={onShow}
    >
      {content}
    </button>
  )
}

/** Ranking and skill matrix for the candidates of one job. */
export default function Comparison({ job, blind, labels, onOpen, onRemove, openId }) {
  const [picked, setPicked] = useState(null) // { skill, id }
  const name = (c) => (blind ? `Candidate ${labels[c.analysis_id]}` : c.filename)
  const pickedCandidate = picked && job.candidates.find((c) => c.analysis_id === picked.id)
  const pickedCell = pickedCandidate?.cells[picked.skill]
  const short = (c) => (blind ? labels[c.analysis_id] : c.filename.replace(/\.(pdf|docx|txt)$/i, ''))
  return (
    <>
      <section className="card">
        <h2>Ranking</h2>
        <p className="method"><Info size={14} aria-hidden="true" /> {job.label}</p>
        <div className="table-scroll">
          <table className="breakdown roles ranking">
            <thead>
              <tr>
                <th>#</th>
                <th>Candidate</th>
                <th>Fit</th>
                <th className="hide-narrow">Required</th>
                <th className="hide-narrow"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {job.candidates.map((c) => (
                <tr key={c.analysis_id} className={openId === c.analysis_id ? 'row-open' : ''}>
                  <td>{c.rank}</td>
                  <td>
                    {name(c)}
                    <div className="role-missing">
                      {c.missing_required.length ? `Missing: ${c.missing_required.join(', ')}` : 'All required skills found'}
                      {c.extraction === 'ai' ? ' · AI profile' : ''}
                    </div>
                    <div className="only-narrow narrow-meta">
                      Required {c.required_matched} of {c.required_total}
                      {c.required_related > 0 && ` (+${c.required_related} related)`}
                      <span className="narrow-actions">
                        <button type="button" className="icon-button" onClick={() => onOpen(c.analysis_id)}>
                          <FileText size={15} aria-hidden="true" /> Report
                        </button>
                        <button type="button" className="icon-button" onClick={() => onRemove(c)} aria-label={`Remove ${name(c)}`}>
                          <Trash2 size={15} aria-hidden="true" />
                        </button>
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="fit-cell">
                      <span className="fit-value">{c.score ?? '—'}</span>
                      <span className="fit-bar" aria-hidden="true"><span style={{ width: `${c.score || 0}%` }} /></span>
                    </div>
                  </td>
                  <td className="hide-narrow">
                    {c.required_matched} of {c.required_total}
                    {c.required_related > 0 && <span className="role-related"> +{c.required_related} related</span>}
                  </td>
                  <td className="actions hide-narrow">
                    <button type="button" className="icon-button" onClick={() => onOpen(c.analysis_id)}>
                      <FileText size={15} aria-hidden="true" /> Report
                    </button>
                    <button type="button" className="icon-button" onClick={() => onRemove(c)} aria-label={`Remove ${name(c)}`}>
                      <Trash2 size={15} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Skill matrix</h2>
        <p className="muted">
          Each job skill against each candidate. Named: the resume names the skill (full credit). Related: the resume only relates to it (half credit). Missing: no evidence. Select a Named or Related cell to see the resume line it is based on.
        </p>
        {!blind && (
          <p className="muted matrix-key only-narrow">
            {job.candidates.map((c) => `${labels[c.analysis_id]} = ${c.filename}`).join(' · ')}
          </p>
        )}
        <div className="table-scroll matrix-scroll" role="region" aria-label="Skill matrix table" tabIndex={0}>
          <table className="matrix">
            <thead>
              <tr>
                <th className="matrix-skill">Skill</th>
                {job.candidates.map((c) => (
                  <th key={c.analysis_id} title={name(c)}>
                    <span className="matrix-head hide-narrow">{short(c)}</span>
                    <span className="only-narrow">{labels[c.analysis_id]}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {job.skills.map((s) => (
                <tr key={s.skill}>
                  <th className="matrix-skill" scope="row">
                    {s.skill}{' '}
                    <span className={`badge badge--${s.priority}`} title={PRIORITY_LABEL[s.priority]}>
                      <span className="hide-narrow">{PRIORITY_LABEL[s.priority]}</span>
                      <span className="only-narrow" aria-hidden="true">{PRIORITY_SHORT[s.priority]}</span>
                      <span className="sr-only only-narrow-sr">{PRIORITY_LABEL[s.priority]}</span>
                    </span>
                  </th>
                  {job.candidates.map((c) => (
                    <td key={c.analysis_id}>
                      <Cell
                        cell={c.cells[s.skill]}
                        skill={s.skill}
                        candidate={name(c)}
                        shown={picked?.skill === s.skill && picked?.id === c.analysis_id}
                        onShow={() =>
                          setPicked((p) => (p?.skill === s.skill && p?.id === c.analysis_id ? null : { skill: s.skill, id: c.analysis_id }))
                        }
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div id="matrix-quote" className="matrix-quote" aria-live="polite">
          {pickedCell?.quote && (
            <>
              <p>
                <strong>{picked.skill}</strong> · {name(pickedCandidate)} · {CELL[pickedCell.status][1]}
              </p>
              <blockquote className="quote">{pickedCell.quote}</blockquote>
            </>
          )}
        </div>
      </section>
    </>
  )
}
