import { useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router'
import { Button } from '@/components/ui/button'
import { BotPanel } from '@/features/bot/BotPanel'
import { es } from '@/i18n/es'
import { DataPage } from '@/pages/DataPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { ResultPage } from '@/pages/ResultPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { StrategyPage } from '@/pages/StrategyPage'

const links = [
  { to: '/datos', label: es.nav.data },
  { to: '/estrategia', label: es.nav.strategy },
  { to: '/historial', label: es.nav.history },
  { to: '/configuracion', label: es.nav.settings },
]

export default function App() {
  const [botOpen, setBotOpen] = useState(false)
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="w-48 shrink-0 border-r border-border p-4 flex flex-col gap-1">
        <div className="mb-4">
          <div className="text-xl font-bold tracking-wide">{es.app.name}</div>
          <div className="text-xs text-muted-foreground">{es.app.tagline}</div>
        </div>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) =>
              `rounded px-3 py-2 text-sm ${isActive ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/50'}`
            }
          >
            {l.label}
          </NavLink>
        ))}
        <Button variant="outline" className="mt-4" onClick={() => setBotOpen((v) => !v)}>
          {es.nav.bot}
        </Button>
        <div className="mt-auto text-xs text-muted-foreground">{es.app.utc}</div>
      </aside>
      <main className="flex-1 min-w-0 p-6">
        <Routes>
          <Route path="/" element={<Navigate to="/estrategia" replace />} />
          <Route path="/datos" element={<DataPage />} />
          <Route path="/estrategia" element={<StrategyPage />} />
          <Route path="/historial" element={<HistoryPage />} />
          <Route path="/resultado/:id" element={<ResultPage />} />
          <Route path="/configuracion" element={<SettingsPage />} />
        </Routes>
      </main>
      {botOpen && <BotPanel onClose={() => setBotOpen(false)} />}
    </div>
  )
}
