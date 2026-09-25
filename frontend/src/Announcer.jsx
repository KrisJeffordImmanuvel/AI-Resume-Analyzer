import { useEffect, useState } from 'react'

// One polite live region for the whole app, so screen readers hear when slow work finishes.
let setMessage = () => {}

/** Say `text` to screen reader users (e.g. "Analysis ready"). Visible UI is unchanged. */
export function announce(text) {
  // Clear first so the same message twice in a row is still read out.
  setMessage('')
  setTimeout(() => setMessage(text), 50)
}

export default function Announcer() {
  const [message, setState] = useState('')
  useEffect(() => {
    setMessage = setState
    return () => {
      setMessage = () => {}
    }
  }, [])
  return (
    <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
      {message}
    </div>
  )
}
