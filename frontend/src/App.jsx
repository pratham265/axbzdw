import { useEffect, useState } from 'react'
import Overview from './pages/Overview'
import DayAhead from './pages/DayAhead'
import Accuracy from './pages/Accuracy'
import Methodology from './pages/Methodology'

const TABS = [
  ['overview', 'Overview'],
  ['day', 'Day-ahead view'],
  ['accuracy', 'Accuracy analysis'],
  ['method', 'Methodology'],
]

// Tab and day live in the URL hash (#day/2026-01-11) so views can be linked.
function readHash() {
  const [tab, day] = window.location.hash.slice(1).split('/')
  return {
    tab: TABS.some(([id]) => id === tab) ? tab : 'overview',
    day: /^\d{4}-\d{2}-\d{2}$/.test(day || '') ? day : '2026-01-11',
  }
}

export default function App() {
  const [{ tab, day }, setView] = useState(readHash)

  useEffect(() => {
    const onHash = () => setView(readHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const go = (nextTab, nextDay = day) => {
    window.location.hash = nextTab === 'day' ? `day/${nextDay}` : nextTab
  }
  const setTab = (t) => go(t)
  const setDay = (d) => go('day', d)
  const openDay = (d) => go('day', d)

  return (
    <div className="app">
      <header>
        <div>
          <h1>Wind Forecast Monitor</h1>
          <p className="muted">GB national wind: day-ahead forecast vs actual, January 2026 purchase decisions</p>
        </div>
        <nav>
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>
      </header>
      <main>
        {tab === 'overview' && <Overview onOpenDay={openDay} />}
        {tab === 'day' && <DayAhead day={day} setDay={setDay} />}
        {tab === 'accuracy' && <Accuracy />}
        {tab === 'method' && <Methodology />}
      </main>
      <footer className="muted">Data: Elexon BMRS (FUELHH, WINDFOR). All times UTC (= UK time in January).</footer>
    </div>
  )
}
