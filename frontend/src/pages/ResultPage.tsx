import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { api, unwrap, type Schemas } from '@/api/client'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CandleChart, EquityChart } from '@/features/results/Charts'
import { es } from '@/i18n/es'
import { dateUtc, num, pct, price, qty, signClass } from '@/lib/format'

type Metrics = Schemas['Metrics']
type SortKey = 'total_return' | 'max_dd' | 'sharpe' | 'profit_factor' | 'win_rate' | 'n_trades' | 'n_ambiguous'

function pf(m: Metrics): string {
  if (m.profit_factor_infinite) return es.result.infinite
  return num(m.profit_factor)
}

function MetricsGrid({ m }: { m: Metrics }) {
  const items: [string, string, string?][] = [
    [es.result.totalReturn, pct(m.total_return), signClass(m.total_return)],
    [es.result.finalEquity, num(m.final_equity)],
    [es.result.maxDd, pct(-m.max_dd), 'text-rose-400'],
    [es.result.winRate, pct(m.win_rate)],
    [es.result.profitFactor, pf(m)],
    [es.result.trades, String(m.n_trades)],
    [es.result.sharpe, num(m.sharpe)],
    [es.result.fees, num(m.fees_paid)],
    [es.result.ambiguous, String(m.n_ambiguous)],
    [es.result.buyHold, pct(m.buy_hold_return), signClass(m.buy_hold_return)],
    [es.result.exposure, pct(m.exposure, 1)],
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
      {items.map(([label, value, cls]) => (
        <div key={label} className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">{label}</div>
          <div className={`text-lg font-semibold ${cls ?? ''}`}>{value}</div>
        </div>
      ))}
    </div>
  )
}

const VARIANT_COLS: { key: SortKey; label: string; fmt: (m: Metrics) => string }[] = [
  { key: 'total_return', label: es.result.totalReturn, fmt: (m) => pct(m.total_return) },
  { key: 'max_dd', label: es.result.maxDd, fmt: (m) => pct(-m.max_dd) },
  { key: 'sharpe', label: 'Sharpe', fmt: (m) => num(m.sharpe) },
  { key: 'profit_factor', label: es.result.profitFactor, fmt: pf },
  { key: 'win_rate', label: es.result.winRate, fmt: (m) => pct(m.win_rate) },
  { key: 'n_trades', label: es.result.trades, fmt: (m) => String(m.n_trades) },
  { key: 'n_ambiguous', label: es.result.ambiguous, fmt: (m) => String(m.n_ambiguous) },
]

export function ResultPage() {
  const { id = '' } = useParams()
  const [variantId, setVariantId] = useState<string | null>(null)
  const [sort, setSort] = useState<SortKey>('total_return')
  const [desc, setDesc] = useState(true)

  const bt = useQuery({
    queryKey: ['backtest', id],
    queryFn: async () => unwrap(await api.GET('/api/v1/backtests/{bt_id}', { params: { path: { bt_id: id } } })),
  })
  const variants = useQuery({
    queryKey: ['variants', id, sort, desc],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/backtests/{bt_id}/variants', {
          params: { path: { bt_id: id }, query: { sort, desc } },
        }),
      ),
  })
  useEffect(() => {
    if (!variantId && bt.data?.best_variant_id) setVariantId(bt.data.best_variant_id)
  }, [bt.data, variantId])
  const detail = useQuery({
    queryKey: ['variant', id, variantId],
    enabled: variantId !== null,
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/backtests/{bt_id}/variants/{variant_id}', {
          params: { path: { bt_id: id, variant_id: variantId! } },
        }),
      ),
  })

  if (bt.isLoading) return <div>{es.app.loading}</div>
  if (bt.error) return <div className="text-rose-400">{bt.error.message}</div>
  const b = bt.data!
  const d = detail.data
  const paramLabels = Object.keys(variants.data?.[0]?.params ?? {})

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded border border-amber-500/50 bg-amber-500/10 px-4 py-2 text-sm text-amber-300">
        {es.app.pastBanner}
      </div>
      <div>
        <h1 className="text-2xl font-semibold">{b.name}</h1>
        <div className="text-sm text-muted-foreground">
          {b.symbol} · {b.timeframe} · {b.range_from} → {b.range_to} · {es.strategy.variants(b.n_variants)} · {b.created_at}
        </div>
      </div>
      {b.status === 'running' && <div>{es.result.statusRunning}</div>}
      {b.status === 'error' && (
        <div className="text-rose-400">
          {es.result.statusError} {b.error}
        </div>
      )}

      {variants.data && variants.data.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle>{es.result.variants}</CardTitle>
            <p className="text-xs text-muted-foreground">{es.result.variantsHelp}</p>
          </CardHeader>
          <CardContent className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b border-border text-left">
                  {paramLabels.map((p) => (
                    <th key={p} className="py-1 pr-3 font-medium">
                      {p}
                    </th>
                  ))}
                  {VARIANT_COLS.map((c) => (
                    <th
                      key={c.key}
                      className="py-1 pr-3 font-medium cursor-pointer select-none"
                      onClick={() => {
                        if (sort === c.key) setDesc(!desc)
                        else {
                          setSort(c.key)
                          setDesc(true)
                        }
                      }}
                    >
                      {c.label} {sort === c.key ? (desc ? '▼' : '▲') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {variants.data.map((v) => (
                  <tr
                    key={v.id}
                    onClick={() => setVariantId(v.id)}
                    className={`cursor-pointer border-b border-border hover:bg-accent ${v.id === variantId ? 'bg-accent' : ''}`}
                  >
                    {paramLabels.map((p) => (
                      <td key={p} className="py-1 pr-3">
                        {num(v.params[p], Number.isInteger(v.params[p]) ? 0 : 2)}
                      </td>
                    ))}
                    {VARIANT_COLS.map((c) => (
                      <td key={c.key} className={`py-1 pr-3 ${c.key === 'total_return' ? signClass(v.metrics.total_return) : ''}`}>
                        {c.fmt(v.metrics)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {detail.isLoading && <div>{es.result.loadingDetail}</div>}
      {detail.error && <div className="text-rose-400">{detail.error.message}</div>}
      {d && (
        <>
          {Object.keys(d.params).length > 0 && (
            <div className="text-sm">
              {es.result.variant}:{' '}
              {Object.entries(d.params)
                .map(([k, v]) => `${k} = ${v}`)
                .join(' · ')}
            </div>
          )}
          {d.warnings.length > 0 && (
            <Alert>
              <AlertDescription>
                <ul className="list-disc pl-4 text-amber-300">
                  {d.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}
          <MetricsGrid m={d.metrics} />
          <Tabs defaultValue="chart">
            <TabsList>
              <TabsTrigger value="chart">{es.result.chart}</TabsTrigger>
              <TabsTrigger value="trades">{es.result.tradesTable}</TabsTrigger>
              <TabsTrigger value="monthly">{es.result.monthly}</TabsTrigger>
            </TabsList>
            <TabsContent value="chart" className="flex flex-col gap-4">
              {d.candles.truncated && (
                <div className="text-xs text-muted-foreground">{es.result.chartTruncated(d.candles.ts.length)}</div>
              )}
              <CandleChart detail={d} />
              <h3 className="font-medium">{es.result.equity}</h3>
              <EquityChart detail={d} />
              <div className="text-xs text-muted-foreground">{es.result.attribution}</div>
            </TabsContent>
            <TabsContent value="trades">
              <div className="max-h-[600px] overflow-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-background">
                    <tr className="border-b border-border text-left">
                      {['#', es.result.signal, es.result.entry, es.result.entryPrice, es.result.exit, es.result.exitPrice,
                        es.result.qty, es.result.fees, es.result.pnl, es.result.ret, es.result.reason].map((h) => (
                        <th key={h} className="py-1 pr-3 font-medium">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.trades.map((tr, i) => (
                      <tr key={i} className="border-b border-border">
                        <td className="py-1 pr-3">{i + 1}</td>
                        <td className="py-1 pr-3">{dateUtc(tr.signal_ts)}</td>
                        <td className="py-1 pr-3">{dateUtc(tr.entry_ts)}</td>
                        <td className="py-1 pr-3">{price(tr.entry_price)}</td>
                        <td className="py-1 pr-3">{dateUtc(tr.exit_ts)}</td>
                        <td className="py-1 pr-3">{price(tr.exit_price)}</td>
                        <td className="py-1 pr-3">{qty(tr.qty)}</td>
                        <td className="py-1 pr-3">{num(tr.fees)}</td>
                        <td className={`py-1 pr-3 ${signClass(tr.pnl_net)}`}>{num(tr.pnl_net)}</td>
                        <td className={`py-1 pr-3 ${signClass(tr.return_pct)}`}>{pct(tr.return_pct)}</td>
                        <td className="py-1 pr-3">
                          {es.result.reasons[tr.reason] ?? tr.reason}
                          {tr.ambiguous && <span className="ml-1 text-amber-400">({es.result.ambiguousMark})</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </TabsContent>
            <TabsContent value="monthly">
              <table className="w-full text-sm max-w-2xl">
                <thead>
                  <tr className="border-b border-border text-left">
                    {[es.result.month, es.result.monthReturn, es.result.monthTrades, es.result.monthPnl].map((h) => (
                      <th key={h} className="py-1 pr-3 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {d.monthly.map((m) => (
                    <tr key={m.month} className="border-b border-border">
                      <td className="py-1 pr-3">{m.month}</td>
                      <td className={`py-1 pr-3 ${signClass(m.return)}`}>{pct(m.return)}</td>
                      <td className="py-1 pr-3">{m.n_trades}</td>
                      <td className={`py-1 pr-3 ${signClass(m.net_pnl)}`}>{num(m.net_pnl)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  )
}
