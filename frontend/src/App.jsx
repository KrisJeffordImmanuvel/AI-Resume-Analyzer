import { useState } from 'react'
import HealthStatus from './HealthStatus.jsx'
import AnalyzeForm from './AnalyzeForm.jsx'
import AnalysisResults from './AnalysisResults.jsx'

export default function App() {
  const [result, setResult] = useState(null)

  return (
    <main className="app">
      <h1>AI Resume &amp; Career Intelligence Platform</h1>
      <p className="subtitle">Upload a resume and a job description to see an evidence-backed fit report.</p>
      <HealthStatus />
      <AnalyzeForm onResult={setResult} />
      {result && <AnalysisResults result={result} />}
    </main>
  )
}
