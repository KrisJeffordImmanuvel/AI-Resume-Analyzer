import { useEffect, useRef, useState } from 'react'
import { Briefcase, ScanSearch, User } from 'lucide-react'
import StatusIndicator from './StatusIndicator.jsx'
import DataFooter from './DataFooter.jsx'
import AnalyzeForm from './AnalyzeForm.jsx'
import AnalysisResults from './AnalysisResults.jsx'
import Provider from './Provider.jsx'
import RecentAnalyses from './RecentAnalyses.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import Announcer, { announce } from './Announcer.jsx'
import { TabList, TabPanel } from './Tabs.jsx'

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
    announce(
      r.score.value === null
        ? 'Analysis ready. No score: the job description has no recognisable skills.'
        : `Analysis ready. Job-fit score ${r.score.value} out of 100.`,
    )
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
    <>
      <header className="topbar">
        <div className="topbar__inner">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true">
              <ScanSearch size={20} />
            </span>
            <h1 className="brand__name">
              AI Resume &amp; Career Intelligence <span className="brand__suffix">Platform</span>
            </h1>
          </div>
          <StatusIndicator />
        </div>
      </header>
      <main className="app">
        <Announcer />
        <div className="hero">
          <TabList
            id="mode"
            label="Mode"
            className="mode-switch"
            tabs={[['seeker', 'Job Seeker', User], ['provider', 'Job Provider', Briefcase]]}
            value={mode}
            onChange={switchMode}
          />
          <p className="subtitle">
            {mode === 'seeker'
              ? 'See how well a resume fits a job, backed by quotes from both documents.'
              : 'Set a job description once, then compare candidate resumes side by side.'}
          </p>
        </div>
        <TabPanel id="mode" value={mode}>
          {mode === 'seeker' ? (
            <>
              <AnalyzeForm onResult={onNewResult} />
              <RecentAnalyses
                refreshKey={historyKey}
                currentId={result?.id}
                onOpen={(r) => {
                  announce(`Opened the analysis of ${r.resume_filename}.`)
                  showResult(r)
                }}
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
        </TabPanel>
        <DataFooter />
      </main>
    </>
  )
}
