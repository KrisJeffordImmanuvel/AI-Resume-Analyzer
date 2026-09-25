import axios from 'axios'

// The built app is served by the backend itself, so it calls its own address.
// Only the development server (npm run dev, port 5173) needs the backend's URL.
export const API_BASE_URL = import.meta.env.DEV ? import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000' : ''

// The server stops waiting for AI after AI_TIMEOUT_SECONDS (at most 240), so 5 minutes
// leaves room; the first run with semantic matching on also downloads its model.
export const api = axios.create({ baseURL: API_BASE_URL, timeout: 300000 })

/** True when the request was stopped with Cancel (an AbortController signal). */
export const isCancelled = (err) => axios.isCancel(err) || err?.code === 'ERR_CANCELED'


export async function getHealth() {
  const { data } = await api.get('/health', { timeout: 10000 })
  return data
}

export async function createAnalysis({ resumeFile, jdFile, jdText }, { signal, onSent } = {}) {
  const form = new FormData()
  form.append('resume', resumeFile)
  if (jdFile) form.append('jd_file', jdFile)
  else form.append('jd_text', jdText)
  const { data } = await api.post('/api/analyses', form, {
    signal,
    onUploadProgress: (e) => onSent && e.total && e.loaded >= e.total && onSent(),
  })
  return data
}

export async function getSamples() {
  const { data } = await api.get('/api/samples')
  return data
}

// Same limit as the server (parsing.py MAX_TEXT_CHARS).
export const MAX_TEXT_CHARS = 100000

/** Turn an axios error into one readable sentence. */
export function errorMessage(err) {
  const detail = err?.response?.data?.detail
  // The server's form reader rejects very large pasted text with a technical message.
  if (typeof detail === 'string' && detail.startsWith('Part exceeded maximum size')) {
    return `The pasted text is too long. Please shorten it to under ${MAX_TEXT_CHARS.toLocaleString('en-US')} characters.`
  }
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  if (err?.request && !err?.response) return 'Could not reach the app server. Make sure it is still running (start.ps1), then try again.'
  return err?.message || 'Something went wrong.'
}

export async function getRoadmap(analysisId, refresh = false) {
  const { data } = await api.post(`/api/analyses/${analysisId}/roadmap`, null, { params: { refresh } })
  return data
}

export async function getInterview(analysisId, refresh = false) {
  const { data } = await api.post(`/api/analyses/${analysisId}/interview`, null, { params: { refresh } })
  return data
}

export async function submitAnswer(questionId, answer) {
  const { data } = await api.post(`/api/interview/questions/${questionId}/answers`, { answer })
  return data
}

export async function getQuality(analysisId) {
  const { data } = await api.get(`/api/analyses/${analysisId}/quality`)
  return data
}

export async function rewriteBullet(analysisId, bullet) {
  const { data } = await api.post(`/api/analyses/${analysisId}/rewrites`, { bullet })
  return data
}

export async function listRewrites(analysisId) {
  const { data } = await api.get(`/api/analyses/${analysisId}/rewrites`)
  return data
}

export async function getAts(analysisId) {
  const { data } = await api.get(`/api/analyses/${analysisId}/ats`)
  return data
}

export async function getCareer(analysisId) {
  const { data } = await api.get(`/api/analyses/${analysisId}/career`)
  return data
}

export async function getEvidence(analysisId) {
  const { data } = await api.get(`/api/analyses/${analysisId}/evidence`)
  return data
}

export async function runGithub(analysisId, username) {
  const { data } = await api.post(`/api/analyses/${analysisId}/github`, { username: username || null })
  return data
}

export async function runLinkedin(analysisId, text) {
  const { data } = await api.post(`/api/analyses/${analysisId}/linkedin`, { text })
  return data
}

export async function getFairness(analysisId) {
  const { data } = await api.get(`/api/analyses/${analysisId}/fairness`)
  return data
}

export async function getAnalysis(analysisId) {
  const { data } = await api.get(`/api/analyses/${analysisId}`)
  return data
}

// ---- Job Provider mode ----

export async function listJobs() {
  const { data } = await api.get('/api/jobs')
  return data
}

export async function createJob({ title, jdFile, jdText }) {
  const form = new FormData()
  if (title) form.append('title', title)
  if (jdFile) form.append('jd_file', jdFile)
  else form.append('jd_text', jdText)
  const { data } = await api.post('/api/jobs', form)
  return data
}

export async function getJob(jobId) {
  const { data } = await api.get(`/api/jobs/${jobId}`)
  return data
}

export async function addCandidates(jobId, files, { signal } = {}) {
  const form = new FormData()
  for (const f of files) form.append('resumes', f)
  const { data } = await api.post(`/api/jobs/${jobId}/candidates`, form, { signal })
  return data
}

export async function deleteJob(jobId) {
  await api.delete(`/api/jobs/${jobId}`)
}

export async function removeCandidate(jobId, analysisId) {
  await api.delete(`/api/jobs/${jobId}/candidates/${analysisId}`)
}

export async function listAnalyses(limit = 20) {
  const { data } = await api.get('/api/analyses', { params: { limit } })
  return data
}

export async function deleteAnalysis(analysisId) {
  await api.delete(`/api/analyses/${analysisId}`)
}
