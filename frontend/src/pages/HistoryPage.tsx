import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { api, unwrap } from '@/api/client'
import { es } from '@/i18n/es'
import { pct, signClass } from '@/lib/format'

export function HistoryPage() {
  const q = useQuery({
    queryKey: ['backtests'],
    queryFn: async () => unwrap(await api.GET('/api/v1/backtests')),
    refetchInterval: 5000,
  })
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{es.history.title}</h1>
      {q.error && <div className="text-rose-400">{q.error.message}</div>}
      {q.data?.length === 0 && <div className="text-muted-foreground">{es.history.empty}</div>}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            {[es.history.date, es.history.name, es.history.market, es.history.range, es.history.variants,
              es.history.best, es.history.status, ''].map((h, i) => (
              <th key={i} className="py-2 pr-3 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {q.data?.map((b) => (
            <tr key={b.id} className="border-b border-border">
              <td className="py-2 pr-3">{b.created_at.slice(0, 16).replace('T', ' ')}</td>
              <td className="py-2 pr-3">{b.name}</td>
              <td className="py-2 pr-3">
                {b.symbol} · {b.timeframe}
              </td>
              <td className="py-2 pr-3">
                {b.range_from} → {b.range_to}
              </td>
              <td className="py-2 pr-3">{b.n_variants}</td>
              <td className={`py-2 pr-3 ${signClass(b.best_return)}`}>{pct(b.best_return)}</td>
              <td className="py-2 pr-3">{es.history.statuses[b.status] ?? b.status}</td>
              <td className="py-2 pr-3">
                <Link className="underline" to={`/resultado/${b.id}`}>
                  {es.history.open}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
