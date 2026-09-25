/**
 * Accessible tabs (WAI-ARIA tabs pattern): each tab controls a panel, only the selected tab is in the
 * Tab order, and Left/Right/Home/End move between tabs (selecting as they go).
 *
 *   <TabList id="results" label="Report sections" tabs={[['report', 'Fit report'], ...]} value={tab} onChange={setTab} />
 *   <TabPanel id="results" value={tab}>...</TabPanel>
 *
 * `tabs` entries are [value, label] or [value, label, Icon].
 */
export const tabId = (id, value) => `${id}-tab-${value}`
export const panelId = (id) => `${id}-panel`

export function TabList({ id, label, tabs, value, onChange, className = 'tabs' }) {
  function onKeyDown(event) {
    const i = tabs.findIndex(([v]) => v === value)
    const next = {
      ArrowRight: (i + 1) % tabs.length,
      ArrowLeft: (i - 1 + tabs.length) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    }[event.key]
    if (next === undefined) return
    event.preventDefault()
    const nextValue = tabs[next][0]
    onChange(nextValue)
    document.getElementById(tabId(id, nextValue))?.focus()
  }

  return (
    <div className={className} role="tablist" aria-label={label} onKeyDown={onKeyDown}>
      {tabs.map(([v, text, Icon]) => {
        const selected = v === value
        return (
          <button
            key={v}
            id={tabId(id, v)}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={panelId(id)}
            tabIndex={selected ? 0 : -1}
            className={selected ? 'tab tab--active' : 'tab'}
            onClick={() => onChange(v)}
          >
            {Icon && <Icon size={16} aria-hidden="true" />} {text}
          </button>
        )
      })}
    </div>
  )
}

/** One panel for the selected tab (the content changes with the tab). */
export function TabPanel({ id, value, className, children }) {
  return (
    <div id={panelId(id)} role="tabpanel" aria-labelledby={tabId(id, value)} className={className}>
      {children}
    </div>
  )
}
