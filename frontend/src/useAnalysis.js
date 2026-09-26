import { useEffect, useState } from 'react'
import { useLocation } from 'react-router'
import { errorMessage, getAnalysis } from './api.js'

/**
 * Loads one saved analysis for a page. A result handed over by the previous page
 * (navigation state) is shown at once; the saved copy is then loaded to be sure it is current.
 */
export default function useAnalysis(id) {
  const location = useLocation()
  const handedOver = location.state?.result
  const [state, setState] = useState(() => ({
    result: handedOver && String(handedOver.id) === String(id) ? handedOver : null,
    error: null,
  }))

  useEffect(() => {
    let alive = true
    getAnalysis(id).then(
      (result) => alive && setState({ result, error: null }),
      (err) => alive && setState({ result: null, error: errorMessage(err) }),
    )
    return () => {
      alive = false
    }
  }, [id])

  return state
}
