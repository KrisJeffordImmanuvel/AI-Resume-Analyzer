import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Generous timeout: an analysis may wait on Gemini and, the first time, on the
// semantic model download.
export const api = axios.create({ baseURL: API_BASE_URL, timeout: 300000 })

export async function getHealth() {
  const { data } = await api.get('/health', { timeout: 10000 })
  return data
}

export async function createAnalysis({ resumeFile, jdFile, jdText }) {
  const form = new FormData()
  form.append('resume', resumeFile)
  if (jdFile) form.append('jd_file', jdFile)
  else form.append('jd_text', jdText)
  const { data } = await api.post('/api/analyses', form)
  return data
}

/** Turn an axios error into one readable sentence. */
export function errorMessage(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  if (err?.request && !err?.response) return `Could not reach the backend at ${API_BASE_URL}. Is uvicorn running?`
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
