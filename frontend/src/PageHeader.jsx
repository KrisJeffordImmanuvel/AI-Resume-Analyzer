import { useEffect, useRef } from 'react'
import { Link } from 'react-router'
import { ArrowLeft } from 'lucide-react'

const APP_NAME = 'AI Resume & Career Intelligence'

/**
 * The top of every page: an optional back link, the page title (h1) and a short line under it.
 * When a page opens it scrolls to the top and moves keyboard/screen-reader focus to the title,
 * so moving between pages is announced like a normal page load.
 */
export default function PageHeader({ title, subtitle, back, actions }) {
  const heading = useRef(null)

  useEffect(() => {
    window.scrollTo(0, 0)
    heading.current?.focus({ preventScroll: true })
  }, [])

  useEffect(() => {
    document.title = title ? `${title} · ${APP_NAME}` : APP_NAME
  }, [title])

  return (
    <div className="page-header">
      {back && (
        <Link to={back.to} className="back-link">
          <ArrowLeft size={16} aria-hidden="true" /> {back.label}
        </Link>
      )}
      <div className="page-header__row">
        <div className="page-header__text">
          <h1 ref={heading} tabIndex={-1}>{title}</h1>
          {subtitle && <p className="subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="page-header__actions">{actions}</div>}
      </div>
    </div>
  )
}
