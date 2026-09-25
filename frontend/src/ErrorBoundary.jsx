import { Component } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

/** Keeps a display bug in one section from blanking the whole page. */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Section failed to render:', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <section className="card" role="alert">
        <h2 className="section-title section-title--bad">
          <AlertTriangle size={18} aria-hidden="true" /> This section could not be displayed
        </h2>
        <p className="muted">
          The rest of the page still works. Try again; if it keeps happening, reload the page. Technical details are in
          the browser console (F12).
        </p>
        <button type="button" className="icon-button" onClick={() => this.setState({ error: null })}>
          <RotateCcw size={15} aria-hidden="true" /> Try again
        </button>
      </section>
    )
  }
}
