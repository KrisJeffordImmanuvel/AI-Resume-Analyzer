/**
 * The Truescope logo: a "T" inside a scope's crosshair ring ("true" + "scope").
 * Drawn inline so it follows the light/dark colours; public/favicon.svg is the same design.
 */
export default function Logo({ size = 34 }) {
  return (
    <svg className="logo" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="8" className="logo__bg" />
      <g className="logo__fg" fill="none" strokeLinecap="round">
        <circle cx="16" cy="16" r="9.25" strokeWidth="2.5" />
        <path d="M16 3.5v3M16 25.5v3M3.5 16h3M25.5 16h3" strokeWidth="2.5" />
        <path d="M11.5 12.5h9M16 12.5v8" strokeWidth="2.75" />
      </g>
    </svg>
  )
}
