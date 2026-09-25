import { useState } from 'react'
import { Briefcase, User } from 'lucide-react'
import HealthStatus from './HealthStatus.jsx'
import AnalyzeForm from './AnalyzeForm.jsx'
import AnalysisResults from './AnalysisResults.jsx'
import Provider from './Provider.jsx'
import RecentAnalyses from './RecentAnalyses.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'

const MODE_KEY = 'app-mode'

function savedMode() {
  try {
    return localStorage.getItem(MODE_KEY) === 'provider' ? 'provider' : 'seeker'
  } catch {
    return 'seeker'
  }
}

export default function App() {
  const [mode, setMode] = useState(savedMode)
  const [result, setResult] = useState(null)
  const [historyKey, setHistoryKey] = useState(0)

  function onNewResult(r) {
    setResult(r)
    setHistoryKey((k) => k + 1)
  }

  function switchMode(next) {
    setMode(next)
    try {
      localStorage.setItem(MODE_KEY, next)
    } catch {
      /* storage may be unavailable; the mode just won't be remembered */
    }
  }

  return (
    <main className="app">
      <h1>AI Resume &amp; Career Intelligence Platform</h1>
      <div className="mode-switch" role="tablist" aria-label="Mode">
        <button type="button" role="tab" aria-selected={mode === 'seeker'}
          className={mode === 'seeker' ? 'tab tab--active' : 'tab'} onClick={() => switchMode('seeker')}>
          <User size={16} aria-hidden="true" /> Job Seeker
        </button>
        <button type="button" role="tab" aria-selected={mode === 'provider'}
          className={mode === 'provider' ? 'tab tab--active' : 'tab'} onClick={() => switchMode('provider')}>
          <Briefcase size={16} aria-hidden="true" /> Job Provider
        </button>
      </div>
      <p className="subtitle">
        {mode === 'seeker'
          ? 'Upload a resume and a job description to see an evidence-backed fit report.'
          : 'Set a job description once, then upload candidate resumes and compare them side by side.'}
      </p>
      <HealthStatus />
      {mode === 'seeker' ? (
        <>
          <AnalyzeForm onResult={onNewResult} />
          <RecentAnalyses
            refreshKey={historyKey}
            currentId={result?.id}
            onOpen={setResult}
            onDeleted={(id) => result?.id === id && setResult(null)}
          />
          {result && (
            <ErrorBoundary key={result.id}>
              <AnalysisResults result={result} />
            </ErrorBoundary>
          )}
        </>
      ) : (
        <ErrorBoundary>
          <Provider />
        </ErrorBoundary>
      )}
    </main>
  )
}
