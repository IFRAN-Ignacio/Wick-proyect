import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api, unwrap } from '@/api/client'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { es } from '@/i18n/es'
import { bytes, dateUtc } from '@/lib/format'
import { useJob } from '@/lib/useJob'

export const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d'] as const

export function DataPage() {
  const qc = useQueryClient()
  const [q, setQ] = useState('BTC')
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [tf, setTf] = useState<string>('1h')
  const [from, setFrom] = useState('2023-01-01')
  const [to, setTo] = useState('2025-12-31')
  const [jobId, setJobId] = useState<string | null>(null)
  const [startError, setStartError] = useState<string | null>(null)
  const job = useJob(jobId)

  const catalog = useQuery({
    queryKey: ['catalog', q],
    queryFn: async () => unwrap(await api.GET('/api/v1/data/catalog', { params: { query: { q } } })),
  })
  const datasets = useQuery({
    queryKey: ['datasets'],
    queryFn: async () => unwrap(await api.GET('/api/v1/data/datasets')),
  })

  useEffect(() => {
    if (job && job.status !== 'running') void qc.invalidateQueries({ queryKey: ['datasets'] })
  }, [job, qc])

  async function download() {
    setStartError(null)
    try {
      const r = unwrap(
        await api.POST('/api/v1/data/download', { body: { symbol, timeframe: tf, from, to } }),
      )
      setJobId(r.job_id)
    } catch (e) {
      setStartError(String(e instanceof Error ? e.message : e))
    }
  }

  const running = job?.status === 'running'
  const result = job?.result as { skipped_existing?: number; empty?: string[] } | undefined

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-semibold">{es.data.title}</h1>
        <p className="text-sm text-muted-foreground">{es.data.subtitle}</p>
      </div>
      <Card>
        <CardContent className="flex flex-col gap-4 pt-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Input placeholder={es.data.search} value={q} onChange={(e) => setQ(e.target.value)} />
              {catalog.data && (
                <div className="text-xs text-muted-foreground">
                  {es.data.catalogDate(catalog.data.total, dateUtc(catalog.data.fetched_at))}
                </div>
              )}
              {catalog.error && <div className="text-sm text-rose-400">{String(catalog.error.message)}</div>}
              <div className="max-h-64 overflow-auto border border-border rounded">
                {catalog.data?.symbols.map((s) => (
                  <button
                    key={s.symbol}
                    onClick={() => setSymbol(s.symbol)}
                    className={`flex w-full justify-between px-3 py-1.5 text-sm text-left hover:bg-accent ${
                      s.symbol === symbol ? 'bg-accent' : ''
                    }`}
                  >
                    <span>{s.symbol}</span>
                    <span className="text-xs text-muted-foreground">
                      {s.status === 'TRADING' ? es.data.trading : es.data.notTrading}
                    </span>
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <div>
                <Label>{es.data.selected}</Label>
                <div className="text-lg font-semibold">{symbol}</div>
              </div>
              <div>
                <Label>{es.data.timeframe}</Label>
                <div className="flex gap-1 mt-1">
                  {TIMEFRAMES.map((t) => (
                    <Button key={t} size="sm" variant={t === tf ? 'default' : 'outline'} onClick={() => setTf(t)}>
                      {t}
                    </Button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label>{es.data.from}</Label>
                  <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
                </div>
                <div>
                  <Label>{es.data.to}</Label>
                  <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
                </div>
              </div>
              <Button onClick={download} disabled={running || !symbol}>
                {running ? es.data.downloading : es.data.download}
              </Button>
            </div>
          </div>
          {startError && (
            <Alert variant="destructive">
              <AlertDescription>{startError}</AlertDescription>
            </Alert>
          )}
          {job && (
            <div className="flex flex-col gap-2">
              <Progress value={job.total ? (100 * job.done) / job.total : running ? 0 : 100} />
              <div className="text-sm">
                {job.status === 'done' ? es.data.downloadDone : job.status === 'error' ? es.data.downloadError : job.message}
              </div>
              {job.error && <div className="text-sm text-rose-400">{job.error}</div>}
              {result?.skipped_existing ? (
                <div className="text-xs text-muted-foreground">{es.data.alreadyHad(result.skipped_existing)}</div>
              ) : null}
              {result?.empty && result.empty.length > 0 && (
                <div className="text-xs text-amber-400">{es.data.emptyMonths(result.empty.join(', '))}</div>
              )}
              <pre className="text-xs text-muted-foreground max-h-32 overflow-auto">{job.log.join('\n')}</pre>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{es.data.local}</CardTitle>
        </CardHeader>
        <CardContent>
          {datasets.data?.length === 0 && <div className="text-sm text-muted-foreground">{es.data.noLocal}</div>}
          <table className="w-full text-sm">
            <tbody>
              {datasets.data?.map((d) => (
                <tr key={`${d.symbol}-${d.timeframe}`} className="border-b border-border align-top">
                  <td className="py-2 font-medium">
                    {d.symbol} · {d.timeframe}
                  </td>
                  <td className="py-2">
                    {dateUtc(d.first_ts, false)} → {dateUtc(d.last_ts)}
                  </td>
                  <td className="py-2">
                    {d.rows} {es.data.rows.toLowerCase()}
                  </td>
                  <td className="py-2">{bytes(d.bytes)}</td>
                  <td className="py-2">
                    {d.n_gaps === 0 ? (
                      <span className="text-emerald-400">{es.data.noGaps}</span>
                    ) : (
                      <span className="text-amber-400">{es.data.gapsText(d.n_gaps, d.missing_candles)}</span>
                    )}
                    {d.incomplete_months.length > 0 && (
                      <div className="text-xs text-muted-foreground">
                        {es.data.incomplete(d.incomplete_months.join(', '))}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
