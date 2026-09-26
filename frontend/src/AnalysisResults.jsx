import Roadmap from './Roadmap.jsx'
import Interview from './Interview.jsx'
import ResumeQuality from './ResumeQuality.jsx'
import AtsView from './AtsView.jsx'
import Career from './Career.jsx'
import Evidence from './Evidence.jsx'
import FitReport from './FitReport.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import { TabList, TabPanel } from './Tabs.jsx'

const TABS = [
  ['report', 'Fit report'],
  ['roadmap', 'Learning roadmap'],
  ['interview', 'Mock interview'],
  ['quality', 'Resume quality'],
  ['ats', 'ATS view'],
  ['career', 'Career'],
  ['evidence', 'Evidence'],
]

export const TAB_IDS = TABS.map(([id]) => id)

/** The seven report tabs. The page owns the selected tab (it is part of the web address). */
export default function AnalysisResults({ result, tab, onTabChange }) {
  return (
    <div className="results">
      <TabList id="report" label="Report sections" className="tabs tabs--results" tabs={TABS} value={tab} onChange={onTabChange} />
      <TabPanel id="report" value={tab}>
        {/* key={tab}: switching tabs clears an error shown by the previous tab */}
        <ErrorBoundary key={tab}>
          {tab === 'report' && <FitReport result={result} />}
          {tab === 'roadmap' && <Roadmap analysisId={result.id} />}
          {tab === 'interview' && <Interview analysisId={result.id} />}
          {tab === 'quality' && <ResumeQuality analysisId={result.id} />}
          {tab === 'ats' && <AtsView analysisId={result.id} />}
          {tab === 'career' && <Career analysisId={result.id} />}
          {tab === 'evidence' && <Evidence analysisId={result.id} />}
        </ErrorBoundary>
      </TabPanel>
    </div>
  )
}
