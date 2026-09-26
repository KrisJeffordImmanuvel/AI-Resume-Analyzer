/** Job-description priorities: one set of labels for every screen. */

export const PRIORITY_LABEL = { required: 'Required', standard: 'Mentioned', preferred: 'Nice to have' }
export const PRIORITY_SHORT = { required: 'Req', standard: 'Mid', preferred: 'Nice' }

export const PRIORITY_HELP = {
  required: 'Listed under a heading like "Requirements" or "Must have". Counts 3 points.',
  standard: 'Named elsewhere in the job description. Counts 2 points.',
  preferred: 'Listed under "Preferred", "Nice to have" or "Bonus". Counts 1 point.',
}

export function PriorityBadge({ priority }) {
  return <span className={`badge badge--${priority}`}>{PRIORITY_LABEL[priority]}</span>
}
