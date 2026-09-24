import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({ baseURL: API_BASE_URL, timeout: 10000 })

export async function getHealth() {
  const { data } = await api.get('/health')
  return data
}
