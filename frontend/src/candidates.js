// Blind review: candidates are "Candidate A, B, C…" in upload order, so the letters
// stay the same when the ranking changes.
const letter = (i) =>
  i < 26 ? String.fromCharCode(65 + i) : `${String.fromCharCode(65 + Math.floor(i / 26) - 1)}${String.fromCharCode(65 + (i % 26))}`

/** { analysis_id: "A" | "B" | … } for a job's candidates. */
export function candidateLetters(job) {
  const ids = (job?.candidates || []).map((c) => c.analysis_id).sort((a, b) => a - b)
  return Object.fromEntries(ids.map((id, i) => [id, letter(i)]))
}
