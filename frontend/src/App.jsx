import { Link, NavLink, Route, Routes, useLocation } from 'react-router'
import { Briefcase, ScanSearch, User } from 'lucide-react'
import StatusIndicator from './StatusIndicator.jsx'
import DataFooter from './DataFooter.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import Announcer from './Announcer.jsx'
import Home from './pages/Home.jsx'
import SeekerUpload from './pages/SeekerUpload.jsx'
import AnalysisPage from './pages/AnalysisPage.jsx'
import ProviderJobs from './pages/ProviderJobs.jsx'
import ProviderNewJob from './pages/ProviderNewJob.jsx'
import ProviderJob from './pages/ProviderJob.jsx'
import ProviderReport from './pages/ProviderReport.jsx'
import NotFound from './pages/NotFound.jsx'

export default function App() {
  const { pathname } = useLocation()
  // A display error stays on its page: moving to another page clears it (switching report tabs does not).
  const pageKey = pathname.split('/').slice(0, 4).join('/')
  return (
    <>
      <header className="topbar">
        <div className="topbar__inner">
          <Link to="/" className="brand" aria-label="Truescope, start page">
            <span className="brand__mark" aria-hidden="true">
              <ScanSearch size={20} />
            </span>
            <span className="brand__name">
              Truescope <span className="brand__suffix">Resume &amp; career intelligence</span>
            </span>
          </Link>
          <nav className="topnav" aria-label="Main">
            <NavLink to="/seeker" className="topnav__link">
              <User size={16} aria-hidden="true" /> <span>Job Seeker</span>
            </NavLink>
            <NavLink to="/provider" className="topnav__link">
              <Briefcase size={16} aria-hidden="true" /> <span>Job Provider</span>
            </NavLink>
          </nav>
          <StatusIndicator />
        </div>
      </header>
      <main className="app">
        <Announcer />
        <ErrorBoundary key={pageKey}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/seeker" element={<SeekerUpload />} />
            <Route path="/seeker/analysis/:id/:tab?" element={<AnalysisPage />} />
            <Route path="/provider" element={<ProviderJobs />} />
            <Route path="/provider/new" element={<ProviderNewJob />} />
            <Route path="/provider/jobs/:jobId" element={<ProviderJob />} />
            <Route path="/provider/jobs/:jobId/report/:analysisId/:tab?" element={<ProviderReport />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </ErrorBoundary>
        <DataFooter />
      </main>
    </>
  )
}
