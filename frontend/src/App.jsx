import { useEffect, useRef, useState } from 'react'
import { Briefcase, User } from 'lucide-react'
import StatusIndicator from './StatusIndicator.jsx'
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
  const resultsRef = useRef(null)
  const scrollPending = useRef(false)

  // Bring new results into view: they appear below the form, often off-screen.
  useEffect(() => {
    if (!result || !scrollPending.current || !resultsRef.current) return
    scrollPending.current = false
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    resultsRef.current.focus({ preventScroll: true })
    resultsRef.current.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
  }, [result])

  function showResult(r) {
    scrollPending.current = true
    setResult(r)
  }

  function onNewResult(r) {
    showResult(r)
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
      <header className="app-header">
        <h1>AI Resume &amp; Career Intelligence Platform</h1>
        <StatusIndicator />
      </header>
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
      {mode === 'seeker' ? (
        <>
          <AnalyzeForm onResult={onNewResult} />
          <RecentAnalyses
            refreshKey={historyKey}
            currentId={result?.id}
            onOpen={showResult}
            onDeleted={(id) => result?.id === id && setResult(null)}
          />
          {result && (
            <section ref={resultsRef} tabIndex={-1} className="results-anchor" aria-label="Analysis results">
              <ErrorBoundary key={result.id}>
                <AnalysisResults result={result} />
              </ErrorBoundary>
            </section>
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
