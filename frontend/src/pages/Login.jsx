import { useState } from 'react'
import { LogIn } from 'lucide-react'
import { errorMessage, signIn } from '../api.js'
import PageHeader from '../PageHeader.jsx'

/** Shown instead of the app when it is published with a password and this browser is not signed in. */
export default function Login({ onSignedIn }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    if (!password) {
      setError('Please type the password.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await signIn(password)
      onSignedIn()
    } catch (e) {
      setError(errorMessage(e))
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <PageHeader title="Sign in" subtitle="This Truescope site is private. Type its password to continue." />
      <section className="card">
        <form className="form" onSubmit={submit} noValidate>
          <label className="field">
            <span className="field__label">Password</span>
            <input
              className="text-input"
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? 'login-error' : undefined}
            />
          </label>
          {error && (
            <p id="login-error" className="form__error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="primary" disabled={busy}>
            <LogIn size={16} aria-hidden="true" /> {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </div>
  )
}
