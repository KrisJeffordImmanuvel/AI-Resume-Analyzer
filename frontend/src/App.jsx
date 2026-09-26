import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router'
import { Briefcase, Settings as SettingsIcon, User } from 'lucide-react'
import Logo from './Logo.jsx'
import StatusIndicator from './StatusIndicator.jsx'
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
import Settings from './pages/Settings.jsx'
import Login from './pages/Login.jsx'
import { SIGNED_OUT_EVENT, getAuthStatus, signOut } from './api.js'
import { AuthContext } from './auth.js'

export default function App() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  // null while checking; a published site (APP_PASSWORD set) shows the sign-in page until signed in.
  const [auth, setAuth] = useState(null)

  useEffect(() => {
    let alive = true
    getAuthStatus().then(
      (status) => alive && setAuth(status),
      // Server not reachable yet: show the app (its status light says so); a later "sign in first" reply brings the sign-in page.
      () => alive && setAuth({ required: false, signed_in: true }),
    )
    const signedOut = () => setAuth({ required: true, signed_in: false })
    window.addEventListener(SIGNED_OUT_EVENT, signedOut)
    return () => {
      alive = false
      window.removeEventListener(SIGNED_OUT_EVENT, signedOut)
    }
  }, [])

  const logOut = useCallback(async () => {
    await signOut()
    setAuth({ required: true, signed_in: false })
    navigate('/', { replace: true })
  }, [navigate])
  const authValue = useMemo(() => ({ required: !!auth?.required, signOut: logOut }), [auth, logOut])
  const locked = !auth || !auth.signed_in

  // A display error stays on its page: moving to another page clears it (switching report tabs does not).
  const pageKey = pathname.split('/').slice(0, 4).join('/')
  return (
    <>
      <header className="topbar">
        <div className="topbar__inner">
          <Link to="/" className="brand" aria-label="Truescope, start page">
            <Logo />
            <span className="brand__name">
              Truescope <span className="brand__suffix">Resume &amp; career intelligence</span>
            </span>
          </Link>
          {/* The start page offers the same two choices as big cards, so the links are hidden there. */}
          {pathname !== '/' && !locked && (
            <nav className="topnav" aria-label="Main">
              <NavLink to="/seeker" className="topnav__link">
                <User size={16} aria-hidden="true" /> <span>Job Seeker</span>
              </NavLink>
              <NavLink to="/provider" className="topnav__link">
                <Briefcase size={16} aria-hidden="true" /> <span>Job Provider</span>
              </NavLink>
            </nav>
          )}
          <div className="topbar__end">
            <StatusIndicator />
            {!locked && (
              <NavLink to="/settings" className="settings-link" aria-label="Settings" title="Settings">
                <SettingsIcon size={18} aria-hidden="true" />
              </NavLink>
            )}
          </div>
        </div>
      </header>
      <main className="app">
        <Announcer />
        {auth && !auth.signed_in && <Login onSignedIn={() => setAuth({ required: true, signed_in: true })} />}
        {auth?.signed_in && (
          <AuthContext.Provider value={authValue}>
            <ErrorBoundary key={pageKey}>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/seeker" element={<SeekerUpload />} />
                <Route path="/seeker/analysis/:id/:tab?" element={<AnalysisPage />} />
                <Route path="/provider" element={<ProviderJobs />} />
                <Route path="/provider/new" element={<ProviderNewJob />} />
                <Route path="/provider/jobs/:jobId" element={<ProviderJob />} />
                <Route path="/provider/jobs/:jobId/report/:analysisId/:tab?" element={<ProviderReport />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </ErrorBoundary>
          </AuthContext.Provider>
        )}
      </main>
    </>
  )
}
